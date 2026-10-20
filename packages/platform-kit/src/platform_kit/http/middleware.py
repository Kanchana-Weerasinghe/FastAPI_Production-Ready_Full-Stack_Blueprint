import re
import time
import uuid

import structlog
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from platform_kit.database import Database, pending_after_commit, run_callbacks
from platform_kit.http.problems import problem_response
from platform_kit.logging import logger

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_NO_TRANSACTION_PATHS = ("/health/",)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Request context, body size limit and the per-request unit of work.

    - Reuses an incoming `X-Request-ID` (from the gateway or a calling service) so one request can be
      followed across services; otherwise generates one. It is bound to every log line and returned.
    - Opens one transaction per request and commits it once; any 4xx/5xx response rolls it back.
    - Runs `UnitOfWork.after_commit` callbacks after the response body is sent.
    """

    def __init__(self, app: ASGIApp, *, db: Database, max_body_bytes: int, problem_base_uri: str) -> None:
        super().__init__(app)
        self.db = db
        self.max_body_bytes = max_body_bytes
        self.problem_base_uri = problem_base_uri

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_id = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming_id if _VALID_REQUEST_ID.match(incoming_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, method=request.method, path=request.url.path)
        start = time.perf_counter()

        if self._exceeds_body_limit(request):
            response: Response = problem_response(
                request,
                base_uri=self.problem_base_uri,
                status=413,
                code="payload_too_large",
                title="Content Too Large",
                detail="Request body too large",
            )
        elif request.url.path.startswith(_NO_TRANSACTION_PATHS):
            response = await call_next(request)
        else:
            async with self.db.session_scope(run_after_commit=False) as session:
                callbacks = pending_after_commit()
                response = await call_next(request)
                if response.status_code >= 400:
                    callbacks.clear()
                    await session.rollback()
            if callbacks:
                response = StreamingResponse(
                    response.body_iterator,  # type: ignore[attr-defined]
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    background=BackgroundTask(run_callbacks, list(callbacks)),
                )

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_completed", status_code=response.status_code, duration=f"{time.perf_counter() - start:.4f}s"
        )
        return response

    def _exceeds_body_limit(self, request: Request) -> bool:
        content_length = request.headers.get("content-length")
        if not content_length:
            return False
        try:
            return int(content_length) > self.max_body_bytes
        except ValueError:
            return True
