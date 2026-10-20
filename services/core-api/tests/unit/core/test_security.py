import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import Request

from app.core.config import config
from app.core.errors import AuthenticationError
from app.core.security import (
    ALGORITHM,
    JWTCookieAuth,
    create_access_token,
    create_mfa_challenge_token,
    decode_token,
    decrypt_field,
    encrypt_field,
    hash_password,
    hash_password_async,
    hash_token,
    verify_password,
    verify_password_async,
)


def _request_with_cookie(token: str | None) -> MagicMock:
    request = MagicMock(spec=Request)
    request.cookies = {config.AUTH_COOKIE_NAME: token} if token else {}
    return request


def test_access_token_claims() -> None:
    """Test that access tokens carry subject, role, token version and a short expiry."""
    user_id = uuid.uuid4()
    claims = decode_token(create_access_token(user_id=user_id, role="admin", token_version=4), "access")
    assert claims["sub"] == str(user_id)
    assert claims["role"] == "admin"
    assert claims["ver"] == 4
    assert claims["exp"] - claims["iat"] == config.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_decode_token_rejects_wrong_type() -> None:
    """Test that an MFA challenge token cannot be used as an access token."""
    with pytest.raises(AuthenticationError) as exc_info:
        decode_token(create_mfa_challenge_token(uuid.uuid4()), "access")
    assert exc_info.value.code == "invalid_token"


def test_decode_token_expired() -> None:
    """Test that expired tokens are rejected with the token_expired code."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "x", "type": "access", "iat": now - timedelta(hours=1), "exp": now - timedelta(minutes=1)},
        config.SECRET_KEY.get_secret_value(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(AuthenticationError) as exc_info:
        decode_token(token, "access")
    assert exc_info.value.code == "token_expired"


def test_decode_token_invalid_signature() -> None:
    """Test that tokens signed with another key are rejected."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "x", "type": "access", "iat": now, "exp": now + timedelta(minutes=5)}, "wrong-key", algorithm=ALGORITHM
    )
    with pytest.raises(AuthenticationError):
        decode_token(token, "access")


async def test_jwt_cookie_auth() -> None:
    """Test that JWTCookieAuth returns claims from a valid cookie and rejects a missing one."""
    token = create_access_token(user_id=uuid.uuid4(), role="user", token_version=0)
    assert (await JWTCookieAuth()(_request_with_cookie(token)))["type"] == "access"
    with pytest.raises(AuthenticationError) as exc_info:
        await JWTCookieAuth()(_request_with_cookie(None))
    assert exc_info.value.code == "not_authenticated"


def test_hash_token_is_deterministic_and_opaque() -> None:
    """Test that stored token hashes are stable SHA-256 digests that don't contain the token."""
    assert hash_token("abc") == hash_token("abc")
    assert "abc" not in hash_token("abc")
    assert len(hash_token("abc")) == 64


def test_field_encryption_round_trip() -> None:
    """Test that encrypted fields decrypt to the original value and the ciphertext differs from it."""
    ciphertext = encrypt_field("JBSWY3DPEHPK3PXP")
    assert ciphertext != "JBSWY3DPEHPK3PXP"
    assert decrypt_field(ciphertext) == "JBSWY3DPEHPK3PXP"


def test_hash_and_verify_password() -> None:
    """Test that password hashing and verification round-trip correctly."""
    hashed = hash_password("my-secure-password")
    assert verify_password("my-secure-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


async def test_async_password_helpers() -> None:
    """Test that the threadpool-backed hash/verify helpers round-trip a password."""
    hashed = await hash_password_async("Async-Pass-123")
    assert await verify_password_async("Async-Pass-123", hashed) is True
    assert await verify_password_async("wrong", hashed) is False


async def test_verify_password_async_without_user() -> None:
    """Test that verifying against a missing user still runs bcrypt (constant time) and returns False."""
    assert await verify_password_async("anything", None) is False
