"""
Maps every error to an RFC 9457 Problem Details response (`application/problem+json`).

    {
      "type": "<PROBLEM_TYPE_BASE_URI>/not_found",
      "title": "Not Found",
      "status": 404,
      "detail": "Acquisition job not found",
      "instance": "/v1/acquisition-jobs/1f0e...",
      "code": "not_found",
      "request_id": "8c1b...",
      "errors": [{"field": "...", "message": "...", "type": "..."}]   # validation errors only
    }
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from platform_kit.errors import AppError
from platform_kit.logging import logger

PROBLEM_JSON = "application/problem+json"

_HTTP_STATUS_CODES = {
    400: ("bad_request", "Bad Request"),
    401: ("unauthenticated", "Unauthenticated"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not Found"),
    405: ("method_not_allowed", "Method Not Allowed"),
    413: ("payload_too_large", "Content Too Large"),
    429: ("rate_limited", "Too Many Requests"),
}

Handler = Callable[[Request, Any], Awaitable[JSONResponse]]


def problem_response(
    request: Request,
    *,
    base_uri: str,
    status: int,
    code: str,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{base_uri.rstrip('/')}/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
        **extra,
    }
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_JSON, headers=headers)


def exception_handlers(base_uri: str) -> dict[Any, Handler]:
    """Exception handlers to register on the FastAPI app."""

    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        log = logger.error if exc.status >= 500 else logger.warning
        log("app_error", code=exc.code, status=exc.status, detail=exc.detail)
        return problem_response(
            request,
            base_uri=base_uri,
            status=exc.status,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            **exc.extra,
        )

    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, title = _HTTP_STATUS_CODES.get(exc.status_code, ("http_error", "HTTP Error"))
        detail = exc.detail if isinstance(exc.detail, str) else title
        return problem_response(
            request,
            base_uri=base_uri,
            status=exc.status_code,
            code=code,
            title=title,
            detail=detail,
            headers=getattr(exc, "headers", None),
        )

    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for error in exc.errors():
            loc = error.get("loc", [])
            field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else (str(loc[0]) if loc else "unknown")
            errors.append(
                {
                    "field": field,
                    "message": str(error.get("msg", "Unknown error")).capitalize(),
                    "type": error.get("type", "unknown"),
                }
            )
        return problem_response(
            request,
            base_uri=base_uri,
            status=422,
            code="validation_failed",
            title="Validation Failed",
            detail="Input validation failed.",
            errors=errors,
        )

    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc), method=request.method, path=request.url.path)
        return problem_response(
            request,
            base_uri=base_uri,
            status=500,
            code="internal_error",
            title="Internal Server Error",
            detail="Please try again later.",
        )

    return {
        AppError: app_error,
        StarletteHTTPException: http_error,
        RequestValidationError: validation_error,
        Exception: unexpected_error,
    }
