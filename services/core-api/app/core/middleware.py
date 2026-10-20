import re
import time
import uuid

import structlog
from fastapi import Request
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp

from app.core.client_ip import get_real_ip_address

from .config import config
from .database import Database, pending_after_commit, persist_on_failure_requested, run_callbacks
from .error_handlers import problem_response
from .logging import logger
from .metrics import record_request

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class CoreMiddleware(BaseHTTPMiddleware):
    """
    Main application middleware: request context, body size limit and the per-request unit of work.

    - Binds request context (request ID, method, path, client IP) to structured logs. An incoming
      `X-Request-ID` (e.g. set by the load balancer or a calling service) is reused so a request
      can be correlated across services; otherwise a new one is generated.
    - Opens one database transaction per request and commits it once. Any 4xx/5xx response rolls
      the transaction back, so a failed request never persists partial writes.
    - Runs `UnitOfWork.after_commit` callbacks only after a successful commit, as background tasks
      of the response so they don't delay it.
    """

    def __init__(self, app: ASGIApp, db: Database) -> None:
        super().__init__(app)
        self.db = db

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Intercepts the request to manage context, logs, and database sessions."""
        incoming_id = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming_id if _VALID_REQUEST_ID.match(incoming_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=get_real_ip_address(request),
            user_agent=request.headers.get("user-agent"),
        )
        start_time = time.perf_counter()
        if self._exceeds_body_limit(request):
            logger.warning("request_body_too_large", content_length=request.headers.get("content-length"))
            response: Response = problem_response(
                request,
                status=413,
                code="payload_too_large",
                title="Content Too Large",
                detail="Request body too large",
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        async with self.db.session_scope(run_after_commit=False) as session:
            callbacks = pending_after_commit()
            response = await call_next(request)
            # Exception handlers turn errors into ordinary responses, so the scope never sees an
            # exception: roll back explicitly so a failed request never commits partial writes.
            # (Unless the service explicitly asked to keep security bookkeeping, see UnitOfWork.persist_on_failure.)
            if response.status_code >= 400:
                callbacks.clear()
                if not persist_on_failure_requested():
                    await session.rollback()
        if callbacks:
            # The response returned by call_next ignores `.background`, so re-wrap it in a
            # StreamingResponse that runs the callbacks once the body has been sent.
            response = StreamingResponse(
                response.body_iterator,  # type: ignore[attr-defined]
                status_code=response.status_code,
                headers=dict(response.headers),
                background=BackgroundTask(run_callbacks, list(callbacks)),
            )
        process_time = time.perf_counter() - start_time
        response.headers[REQUEST_ID_HEADER] = request_id
        route = request.scope.get("route")
        record_request(request.method, getattr(route, "path", "unmatched"), response.status_code, process_time)
        logger.info("request_completed", status_code=response.status_code, duration=f"{process_time:.4f}s")
        return response

    @staticmethod
    def _exceeds_body_limit(request: Request) -> bool:
        """
        Rejects oversized bodies up front using Content-Length, before multipart parsing spools them
        to disk. Chunked requests without a length are capped by the reverse proxy and by the
        streaming size check in file storage.
        """
        content_length = request.headers.get("content-length")
        if not content_length:
            return False
        try:
            return int(content_length) > config.MAX_REQUEST_BODY_BYTES
        except ValueError:
            return True
