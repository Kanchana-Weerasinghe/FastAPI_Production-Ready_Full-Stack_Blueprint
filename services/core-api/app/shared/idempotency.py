"""
Idempotency keys for unsafe requests (IETF draft "The Idempotency-Key HTTP Header Field").

Clients that may retry a POST/PATCH (network timeouts, mobile apps, payment-like operations) send a
unique `Idempotency-Key` header. The first request is executed and its response stored; retries with
the same key replay that response (`Idempotent-Replayed: true`) instead of executing again.

- Keys are scoped per user (or per client IP when unauthenticated) and expire after
  `IDEMPOTENCY_TTL_HOURS`.
- Reusing a key with a different request body → 422 `idempotency_key_reused`.
- A retry while the first request is still running → 409 `idempotency_request_in_progress`.
- 5xx responses are not stored, so the client can retry.

The middleware wraps the per-request transaction, so a response is only recorded after the business
transaction committed.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import TIMESTAMP, Integer, LargeBinary, UniqueConstraint, delete, select
from sqlalchemy.dialects.postgresql import JSONB, VARCHAR
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.client_ip import get_real_ip_address
from app.core.config import config
from app.core.database import Database
from app.core.error_handlers import problem_response
from app.core.errors import AuthenticationError
from app.core.logging import logger
from app.core.security import decode_token
from app.shared.models import BaseModel

HEADER = "Idempotency-Key"
REPLAYED_HEADER = "Idempotent-Replayed"
IDEMPOTENT_METHODS = frozenset({"POST", "PATCH"})
STORED_HEADERS = ("content-type", "location", "etag")
MAX_STORED_BODY_BYTES = 1024 * 1024
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


class IdempotencyKeys(BaseModel):
    """A recorded idempotent request and (once finished) its response."""

    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_keys_scope_key"),)

    scope: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    key: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, index=True)


def _scope(request: Request) -> str:
    token = request.cookies.get(config.AUTH_COOKIE_NAME)
    if token:
        try:
            return f"user:{decode_token(token, 'access')['sub']}"
        except AuthenticationError:
            pass
    return f"ip:{get_real_ip_address(request)}"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, db: Database) -> None:
        super().__init__(app)
        self.db = db

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = request.headers.get(HEADER)
        if request.method not in IDEMPOTENT_METHODS or not key:
            return await call_next(request)
        if len(key) > 255:
            return problem_response(
                request, status=400, code="invalid_idempotency_key", title="Bad Request", detail=f"{HEADER} too long"
            )
        body = await request.body()
        request_hash = hashlib.sha256(b"|".join([request.method.encode(), request.url.path.encode(), body])).hexdigest()
        scope = _scope(request)

        early = await self._claim(request, scope, key, request_hash)
        if early is not None:
            return early

        response = await call_next(request)
        if response.status_code >= 500:
            await self._release(scope, key)
            return response
        content = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[attr-defined]
        await self._complete(scope, key, response, content)
        return Response(
            content=content,
            status_code=response.status_code,
            headers=dict(response.headers),
            background=response.background,
        )

    async def _claim(self, request: Request, scope: str, key: str, request_hash: str) -> Response | None:
        """Records the key as in progress, or returns the response to send instead (replay / conflict)."""
        now = datetime.now(UTC)
        async with self.db.session_scope() as session:
            existing = (
                await session.execute(
                    select(IdempotencyKeys).where(IdempotencyKeys.scope == scope, IdempotencyKeys.key == key)
                )
            ).scalar_one_or_none()
            if existing is not None and existing.expires_at <= now:
                await session.delete(existing)
                await session.flush()
                existing = None
            if existing is not None:
                if existing.request_hash != request_hash:
                    return problem_response(
                        request,
                        status=422,
                        code="idempotency_key_reused",
                        title="Unprocessable Content",
                        detail=f"This {HEADER} was already used with a different request",
                    )
                if existing.status == STATUS_COMPLETED:
                    logger.info("idempotent_replay", key=key)
                    headers = {**(existing.response_headers or {}), REPLAYED_HEADER: "true"}
                    return Response(
                        content=existing.response_body or b"",
                        status_code=existing.response_status or 200,
                        headers=headers,
                    )
                return self._in_progress(request)
            session.add(
                IdempotencyKeys(
                    scope=scope,
                    key=key,
                    request_hash=request_hash,
                    status=STATUS_IN_PROGRESS,
                    expires_at=now + timedelta(hours=config.IDEMPOTENCY_TTL_HOURS),
                    created_by=scope,
                    updated_by=scope,
                )
            )
            try:
                await session.flush()
            except IntegrityError:
                # A concurrent request with the same key won the race.
                return self._in_progress(request)
        return None

    @staticmethod
    def _in_progress(request: Request) -> Response:
        return problem_response(
            request,
            status=409,
            code="idempotency_request_in_progress",
            title="Conflict",
            detail="A request with this Idempotency-Key is still being processed",
        )

    async def _complete(self, scope: str, key: str, response: Response, content: bytes) -> None:
        async with self.db.session_scope() as session:
            record = (
                await session.execute(
                    select(IdempotencyKeys).where(IdempotencyKeys.scope == scope, IdempotencyKeys.key == key)
                )
            ).scalar_one_or_none()
            if record is None:
                return
            record.status = STATUS_COMPLETED
            record.response_status = response.status_code
            record.response_headers = {h: response.headers[h] for h in STORED_HEADERS if h in response.headers}
            record.response_body = content if len(content) <= MAX_STORED_BODY_BYTES else b""

    async def _release(self, scope: str, key: str) -> None:
        async with self.db.session_scope() as session:
            await session.execute(
                delete(IdempotencyKeys).where(IdempotencyKeys.scope == scope, IdempotencyKeys.key == key)
            )
