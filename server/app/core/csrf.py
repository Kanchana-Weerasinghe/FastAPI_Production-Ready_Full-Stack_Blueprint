from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .config import config
from .error_handlers import problem_response
from .logging import logger
from .security import tokens_match

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Endpoints that establish or recover a session and therefore cannot have a CSRF token yet.
# They are protected by SameSite=Lax cookies, rate limits and (for sign-in) credentials.
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/v1/auth/signup",
        "/v1/auth/signin",
        "/v1/auth/mfa/verify",
        "/v1/auth/verify-email",
        "/v1/auth/password/forgot",
        "/v1/auth/password/reset",
    }
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit-cookie CSRF protection for cookie-authenticated requests.

    For unsafe methods, when the request carries a session cookie, the `X-CSRF-Token` header must
    equal the `csrf_token` cookie. A cross-site attacker can make the browser send cookies but cannot
    read the CSRF cookie to copy it into a header. Requests without session cookies (e.g. API clients
    using other auth) are not affected.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in SAFE_METHODS or request.url.path in CSRF_EXEMPT_PATHS:
            return await call_next(request)
        has_session = config.AUTH_COOKIE_NAME in request.cookies or config.REFRESH_COOKIE_NAME in request.cookies
        if has_session:
            cookie_token = request.cookies.get(config.CSRF_COOKIE_NAME, "")
            header_token = request.headers.get(config.CSRF_HEADER_NAME, "")
            if not cookie_token or not header_token or not tokens_match(cookie_token, header_token):
                logger.warning("csrf_validation_failed", path=request.url.path)
                return problem_response(
                    request,
                    status=403,
                    code="csrf_failed",
                    title="Forbidden",
                    detail=f"Missing or invalid {config.CSRF_HEADER_NAME} header",
                )
        return await call_next(request)
