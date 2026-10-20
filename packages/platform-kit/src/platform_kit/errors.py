"""
Framework-agnostic application errors.

Domain and application code raise these (or subclasses) and never import HTTP types. The handlers
in `platform_kit.http.problems` map them to RFC 9457 Problem Details responses. Each error carries:

- `status`: the HTTP status code it maps to,
- `code`: a stable, machine-readable identifier clients can branch on (never change it once published),
- `title`: a short, human-readable summary of the error type,
- `detail`: a human-readable explanation of this specific occurrence (safe to show to users).
"""

from typing import Any


class AppError(Exception):
    """Base class for every expected application error."""

    status: int = 500
    code: str = "internal_error"
    title: str = "Internal Server Error"

    def __init__(self, detail: str | None = None, *, code: str | None = None, extra: dict[str, Any] | None = None):
        self.detail = detail or self.title
        if code:
            self.code = code
        # Additional problem members (RFC 9457 extension members), e.g. {"retry_after": 30}.
        self.extra = extra or {}
        super().__init__(self.detail)


class BadRequestError(AppError):
    """The request is syntactically valid but cannot be processed as sent."""

    status = 400
    code = "bad_request"
    title = "Bad Request"


class AuthenticationError(AppError):
    """The caller is not authenticated or the token is invalid."""

    status = 401
    code = "unauthenticated"
    title = "Unauthenticated"


class PermissionDeniedError(AppError):
    """The caller is authenticated but not allowed to perform this action on this resource."""

    status = 403
    code = "forbidden"
    title = "Forbidden"


class NotFoundError(AppError):
    """The requested resource does not exist (or is not visible to the caller)."""

    status = 404
    code = "not_found"
    title = "Not Found"


class ConflictError(AppError):
    """The request conflicts with the current state, e.g. an invalid state transition."""

    status = 409
    code = "conflict"
    title = "Conflict"


class PreconditionFailedError(AppError):
    """A conditional request failed, e.g. `If-Match` does not match the current version (ETag)."""

    status = 412
    code = "precondition_failed"
    title = "Precondition Failed"


class UnprocessableError(AppError):
    """The request is well-formed but violates a business rule."""

    status = 422
    code = "business_rule_violation"
    title = "Business Rule Violation"


class ServiceUnavailableError(AppError):
    """A required dependency (database, another service, ...) is unavailable."""

    status = 503
    code = "service_unavailable"
    title = "Service Unavailable"
