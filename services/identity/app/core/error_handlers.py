"""
Maps every error to an RFC 9457 Problem Details response (`application/problem+json`).

Response shape:

    {
      "type": "https://errors.example.com/not_found",   # PROBLEM_TYPE_BASE_URI + code
      "title": "Not Found",
      "status": 404,
      "detail": "Project not found",
      "instance": "/v2/projects/1f0e...",                  # the request path
      "code": "not_found",                              # stable machine-readable code
      "request_id": "8c1b...",                          # correlates with server logs
      "errors": [{"field": "...", "message": "...", "type": "..."}]   # validation errors only
    }
"""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import config
from app.core.errors import AppError
from app.core.logging import logger

PROBLEM_JSON = "application/problem+json"

# Codes for framework-raised HTTP errors (e.g. 404 for an unknown route, 405 wrong method).
_HTTP_STATUS_CODES = {
    400: ("bad_request", "Bad Request"),
    401: ("unauthenticated", "Unauthenticated"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not Found"),
    405: ("method_not_allowed", "Method Not Allowed"),
    413: ("payload_too_large", "Content Too Large"),
    429: ("rate_limited", "Too Many Requests"),
}


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    """Builds an RFC 9457 Problem Details response."""
    body: dict[str, Any] = {
        "type": f"{config.PROBLEM_TYPE_BASE_URI.rstrip('/')}/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
        **extra,
    }
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_JSON, headers=headers)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Domain errors: expected failures, logged at warning level (5xx at error level)."""
    log = logger.error if exc.status >= 500 else logger.warning
    log("app_error", code=exc.code, status=exc.status, detail=exc.detail)
    return problem_response(request, status=exc.status, code=exc.code, title=exc.title, detail=exc.detail, **exc.extra)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Framework-raised HTTP errors (unknown routes, wrong methods, ...)."""
    code, title = _HTTP_STATUS_CODES.get(exc.status_code, ("http_error", "HTTP Error"))
    detail = exc.detail if isinstance(exc.detail, str) else title
    headers = getattr(exc, "headers", None)
    return problem_response(request, status=exc.status_code, code=code, title=title, detail=detail, headers=headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Request validation errors, with one entry per invalid field."""
    errors = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else (str(loc[0]) if loc else "unknown")
        errors.append(
            {
                "field": field,
                "message": error.get("msg", "Unknown error").capitalize(),
                "type": error.get("type", "unknown"),
            }
        )
    return problem_response(
        request,
        status=422,
        code="validation_failed",
        title="Validation Failed",
        detail="Input validation failed.",
        errors=errors,
    )


async def rate_limit_exception_handler(request: Request, _exc: RateLimitExceeded) -> JSONResponse:
    """Rate limit exceeded (slowapi)."""
    return problem_response(
        request,
        status=429,
        code="rate_limited",
        title="Too Many Requests",
        detail="Too many requests. Please try again later.",
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Unexpected errors: logged with traceback, returned without internal details."""
    logger.exception("unhandled_exception", error=str(exc), method=request.method, path=request.url.path)
    return problem_response(
        request,
        status=500,
        code="internal_error",
        title="Internal Server Error",
        detail="Please try again later.",
    )


EXCEPTION_HANDLERS: dict[Any, Any] = {
    AppError: app_error_handler,
    HTTPException: http_exception_handler,
    StarletteHTTPException: http_exception_handler,
    RequestValidationError: validation_exception_handler,
    RateLimitExceeded: rate_limit_exception_handler,
    Exception: generic_exception_handler,
}
