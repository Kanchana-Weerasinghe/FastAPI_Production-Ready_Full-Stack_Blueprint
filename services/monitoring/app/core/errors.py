"""
Application errors of this service: the framework-agnostic platform-kit types, re-exported so every
module imports them from one place (like the identity service's `app.core.errors`).

Each maps to an RFC 9457 problem response with its `status` and a stable `code`. Never raise
`HTTPException` outside a router.

| Status | Class |
| :--- | :--- |
| 400 | BadRequestError |
| 401 | AuthenticationError |
| 403 | PermissionDeniedError (AccessDeniedError is the central access check's) |
| 404 | NotFoundError |
| 409 | ConflictError |
| 412 | PreconditionFailedError |
| 422 | UnprocessableError |
| 503 | ServiceUnavailableError |
"""

from platform_kit.errors import (
    AccessDeniedError,
    AppError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PreconditionFailedError,
    ServiceUnavailableError,
    UnprocessableError,
)

__all__ = [
    "AccessDeniedError",
    "AppError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "NotFoundError",
    "PermissionDeniedError",
    "PreconditionFailedError",
    "ServiceUnavailableError",
    "UnprocessableError",
]
