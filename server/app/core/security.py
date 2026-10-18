"""
Security primitives: rate limiting, password hashing, tokens, auth cookies and field encryption.

Session model (see docs/adr/0008-session-tokens.md):
- Access token: short-lived JWT (`ACCESS_TOKEN_EXPIRE_MINUTES`) in an HttpOnly cookie, carrying the
  user id (`sub`), role and the user's `token_version` (`ver`). Bumping `token_version` revokes
  every outstanding access token of that user.
- Refresh token: opaque random string in an HttpOnly cookie scoped to the auth endpoints, stored
  only as a SHA-256 hash and rotated on every use (reuse of a rotated token revokes the family).
- CSRF token: random value in a JS-readable cookie that must be echoed in the `X-CSRF-Token` header
  on unsafe requests (double-submit), enforced by `CSRFMiddleware`.
"""

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any, Literal

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, Request, Response
from slowapi import Limiter
from starlette.concurrency import run_in_threadpool

from app.core.client_ip import get_real_ip_address

from .config import config
from .errors import AuthenticationError
from .logging import logger

ALGORITHM = "HS256"
TokenType = Literal["access", "mfa_challenge"]

limiter = Limiter(key_func=get_real_ip_address, storage_uri=config.RATE_LIMIT_STORAGE_URI)


def rate_limit(limit_value: str) -> Any:
    """FastAPI dependency factory for rate limiting."""

    async def dependency(request: Request) -> None:
        pass

    if not config.RATE_LIMIT_ENABLED:
        return Depends(dependency)

    func_name = f"dependency_{id(dependency)}"
    dependency.__name__ = func_name
    dependency.__qualname__ = f"rate_limit.<locals>.{func_name}"
    decorated_dependency = limiter.limit(limit_value)(dependency)
    return Depends(decorated_dependency)


# --- JWTs ----------------------------------------------------------------------------------


def _encode(claims: dict[str, Any], token_type: TokenType, expires_in: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {**claims, "type": token_type, "iat": now, "exp": now + expires_in, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, config.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)


def create_access_token(*, user_id: uuid.UUID, role: str, token_version: int) -> str:
    """Creates a short-lived access token for an authenticated session."""
    logger.info("access_token_issued", user_id=user_id)
    return _encode(
        {"sub": str(user_id), "role": role, "ver": token_version},
        "access",
        timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_mfa_challenge_token(user_id: uuid.UUID) -> str:
    """Creates a short-lived token proving the password step succeeded; exchanged for a session with a TOTP code."""
    return _encode({"sub": str(user_id)}, "mfa_challenge", timedelta(minutes=config.MFA_CHALLENGE_EXPIRE_MINUTES))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Validates signature, expiry and token type; raises AuthenticationError otherwise."""
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            config.SECRET_KEY.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired", code="token_expired") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token", code="invalid_token") from None
    if claims.get("type") != expected_type:
        raise AuthenticationError("Invalid token", code="invalid_token")
    return claims


class JWTCookieAuth:
    """FastAPI dependency returning the validated claims of the access token cookie."""

    async def __call__(self, request: Request) -> dict[str, Any]:
        token = request.cookies.get(config.AUTH_COOKIE_NAME)
        if not token:
            raise AuthenticationError("Not authenticated", code="not_authenticated")
        return decode_token(token, "access")


# --- Opaque tokens (refresh, email verification, password reset, CSRF) ---------------------


def generate_opaque_token() -> str:
    """256-bit random URL-safe token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens are stored only as SHA-256 hashes, so a database leak does not expose usable tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# --- Passwords -----------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


@cache
def _dummy_password_hash() -> str:
    return hash_password("dummy-password-used-for-constant-time-checks")


async def hash_password_async(password: str) -> str:
    """Hashes a password in a worker thread so bcrypt's CPU cost doesn't block the event loop."""
    return await run_in_threadpool(hash_password, password)


async def verify_password_async(plain_password: str, hashed_password: str | None) -> bool:
    """
    Verifies a password in a worker thread so bcrypt doesn't block the event loop.

    When no user matched (`hashed_password` is None) a dummy hash is still checked, so the
    response time doesn't reveal whether an account exists for the given email.
    """
    if hashed_password is None:
        await run_in_threadpool(verify_password, plain_password, _dummy_password_hash())
        return False
    return await run_in_threadpool(verify_password, plain_password, hashed_password)


# --- Field-level encryption ----------------------------------------------------------------


@cache
def _fernet(key: str) -> Fernet:
    # Derive a valid 32-byte Fernet key from the configured secret of any length.
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest()))


def encrypt_field(value: str) -> str:
    """Encrypts a sensitive value (e.g. an MFA seed) for storage at rest."""
    return _fernet(config.FIELD_ENCRYPTION_KEY.get_secret_value()).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_field(value: str) -> str:
    try:
        return _fernet(config.FIELD_ENCRYPTION_KEY.get_secret_value()).decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Encrypted field cannot be decrypted with the current FIELD_ENCRYPTION_KEY") from e


# --- Cookies -------------------------------------------------------------------------------


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str, csrf_token: str) -> None:
    """Sets the session cookies. Access/refresh are HttpOnly; the CSRF cookie is readable by the web app."""
    refresh_max_age = config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    common: dict[str, Any] = {"samesite": "lax", "secure": config.AUTH_COOKIE_SECURE, "domain": config.APP_DOMAIN}
    response.set_cookie(
        config.AUTH_COOKIE_NAME,
        access_token,
        httponly=True,
        path="/",
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        config.REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        path=config.REFRESH_COOKIE_PATH,
        max_age=refresh_max_age,
        **common,
    )
    response.set_cookie(
        config.CSRF_COOKIE_NAME, csrf_token, httponly=False, path="/", max_age=refresh_max_age, **common
    )


def clear_auth_cookies(response: Response) -> None:
    """Expires every session cookie using the attributes they were set with, so browsers drop them."""
    common: dict[str, Any] = {"samesite": "lax", "secure": config.AUTH_COOKIE_SECURE, "domain": config.APP_DOMAIN}
    response.delete_cookie(config.AUTH_COOKIE_NAME, httponly=True, path="/", **common)
    response.delete_cookie(config.REFRESH_COOKIE_NAME, httponly=True, path=config.REFRESH_COOKIE_PATH, **common)
    response.delete_cookie(config.CSRF_COOKIE_NAME, httponly=False, path="/", **common)
