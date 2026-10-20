import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from platform_kit.auth import Principal, TokenVerifier, bearer_token
from platform_kit.errors import AuthenticationError, PermissionDeniedError

SECRET = "test-secret-key-with-at-least-32-characters"


def _token(**overrides: object) -> str:
    now = datetime.now(UTC)
    claims = {"sub": str(uuid.uuid4()), "role": "user", "type": "access", "iat": now, "exp": now + timedelta(minutes=5)}
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_verify_returns_principal_for_valid_access_token() -> None:
    user_id = uuid.uuid4()
    principal = TokenVerifier(secret_key=SECRET).verify(_token(sub=str(user_id), role="admin"))
    assert principal.user_id == user_id
    assert principal.is_admin


def test_verify_rejects_expired_token() -> None:
    expired = _token(exp=datetime.now(UTC) - timedelta(seconds=1))
    with pytest.raises(AuthenticationError) as excinfo:
        TokenVerifier(secret_key=SECRET).verify(expired)
    assert excinfo.value.code == "token_expired"


@pytest.mark.parametrize(
    "token",
    [
        _token(type="refresh"),
        _token(sub="not-a-uuid"),
        jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, SECRET, algorithm="HS256"),
        _token().replace(".", "x", 1),
    ],
)
def test_verify_rejects_invalid_tokens(token: str) -> None:
    with pytest.raises(AuthenticationError):
        TokenVerifier(secret_key=SECRET).verify(token)


def test_verify_rejects_token_signed_with_another_key() -> None:
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "another-secret-key-with-at-least-32-characters",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        TokenVerifier(secret_key=SECRET).verify(forged)


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer "])
def test_bearer_token_requires_bearer_scheme(header: str | None) -> None:
    with pytest.raises(AuthenticationError):
        bearer_token(header)


def test_bearer_token_extracts_token() -> None:
    assert bearer_token("Bearer abc.def") == "abc.def"


def test_require_role_allows_role_or_admin() -> None:
    Principal(user_id=uuid.uuid4(), role="operator", token="t").require_role("operator")
    Principal(user_id=uuid.uuid4(), role="admin", token="t").require_role("operator")
    with pytest.raises(PermissionDeniedError):
        Principal(user_id=uuid.uuid4(), role="user", token="t").require_role("operator")
