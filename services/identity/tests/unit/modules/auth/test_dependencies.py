import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import jwt
import pytest
from fastapi import Request

from app.core.config import config
from app.core.errors import AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError
from app.core.security import ALGORITHM
from app.modules.auth.dependencies import check_ownership, get_access_subject, get_current_user, resolve_session
from app.modules.users.domain.value_objects import EmailAddress, PasswordHash, Role, Username
from app.modules.users.public import UserAccount


def _user(token_version: int = 0, user_id: UUID | None = None) -> UserAccount:
    return UserAccount(
        id=user_id or uuid.uuid4(),
        email=EmailAddress("test@example.com"),
        username=Username("test_user"),
        password_hash=PasswordHash("$2b$12$C6UzMDM.H6dfI/f/IKcEeO5EHpKChSJlLpm1AaM6cX9i5n2H2hB7m"),
        role=Role.USER,
        token_version=token_version,
        email_verified_at=None,
        failed_login_attempts=0,
        locked_until=None,
        mfa_secret_encrypted=None,
        mfa_enabled_at=None,
        created_at=datetime.now(UTC),
        is_active=True,
        is_deleted=False,
    )


def _cookie_request(claims: dict[str, Any] | None = None, *, token: str | None = None) -> MagicMock:
    """A request carrying an access token cookie signed with the app's key (or no cookie)."""
    if claims is not None:
        now = datetime.now(UTC)
        token = jwt.encode(
            {"type": "access", "iat": now, "exp": now + timedelta(minutes=5), **claims},
            config.SECRET_KEY.get_secret_value(),
            algorithm=ALGORITHM,
        )
    request = MagicMock(spec=Request)
    request.cookies = {config.AUTH_COOKIE_NAME: token} if token else {}
    return request


async def test_get_current_user_success() -> None:
    """Test the session resolves the user when the token's version matches the user's token_version."""
    user = _user(token_version=2)
    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = user
    session = await resolve_session(_cookie_request({"sub": str(user.id), "ver": 2}), users=mock_service)
    result = await get_current_user(session)
    assert result.id == user.id
    mock_service.get_by_id.assert_called_once_with(user.id)


async def test_get_current_user_revoked_token_version() -> None:
    """Test tokens issued before the user's token_version was bumped are rejected."""
    user = _user(token_version=3)
    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = user
    session = await resolve_session(_cookie_request({"sub": str(user.id), "ver": 2}), users=mock_service)
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(session)
    assert exc_info.value.code == "token_revoked"


async def test_get_current_user_invalid_subject() -> None:
    """Test a missing or malformed subject claim is rejected as an invalid token."""
    for claims in ({}, {"sub": "not-a-uuid"}):
        session = await resolve_session(_cookie_request(claims), users=AsyncMock())
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await get_current_user(session)


async def test_get_current_user_not_found() -> None:
    """Test a token for a user that no longer exists is rejected."""
    mock_service = AsyncMock()
    mock_service.get_by_id.side_effect = NotFoundError("Record not found")
    session = await resolve_session(_cookie_request({"sub": str(uuid.uuid4()), "ver": 0}), users=mock_service)
    with pytest.raises(AuthenticationError, match="User not found"):
        await get_current_user(session)


async def test_get_current_user_without_cookie() -> None:
    """Test a request without the access token cookie is not authenticated."""
    session = await resolve_session(_cookie_request(), users=AsyncMock())
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(session)
    assert exc_info.value.code == "not_authenticated"


async def test_access_subject_is_anonymous_with_the_reason_or_signed_in_with_the_role() -> None:
    """Test the access check sees anonymous callers (keeping the 401 reason) and signed-in callers' roles."""
    anonymous = await get_access_subject(await resolve_session(_cookie_request(), users=AsyncMock()))
    assert not anonymous.authenticated
    assert isinstance(anonymous.authentication_error, AuthenticationError)

    user = _user()
    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = user
    session = await resolve_session(_cookie_request({"sub": str(user.id), "ver": 0}), users=mock_service)
    signed_in = await get_access_subject(session)
    assert signed_in.authenticated
    assert signed_in.roles == frozenset({"user"})


async def test_check_ownership_success() -> None:
    """Test check_ownership successfully validates resource ownership."""
    validation_fn = check_ownership("projects.use_cases", param_name="id", is_active=True)

    resource_id = uuid.uuid4()
    mock_request = MagicMock(spec=Request)
    mock_request.path_params = {"id": str(resource_id)}

    mock_user = _user(user_id=uuid.uuid4())
    mock_user.username = Username("owner_user")

    mock_resource = MagicMock()
    mock_resource.user_id = mock_user.id

    mock_service = AsyncMock()
    mock_service.get_list.return_value = {"founds": [mock_resource]}

    result = await validation_fn(
        request=mock_request,
        current_user=mock_user,
        service=mock_service,
    )
    assert result == mock_resource
    mock_service.get_list.assert_called_once_with({"id__eq": resource_id, "is_active": True})


async def test_check_ownership_param_not_found() -> None:
    """Test check_ownership raises NotFoundError if parameter name is not in request path."""
    validation_fn = check_ownership("projects.use_cases", param_name="id")

    mock_request = MagicMock(spec=Request)
    mock_request.path_params = {}

    mock_user = _user()
    mock_service = AsyncMock()

    with pytest.raises(NotFoundError, match="id not found in path"):
        await validation_fn(
            request=mock_request,
            current_user=mock_user,
            service=mock_service,
        )


async def test_check_ownership_invalid_uuid() -> None:
    """Test check_ownership raises BadRequestError if ID string is not a valid UUID."""
    validation_fn = check_ownership("projects.use_cases", param_name="id")

    mock_request = MagicMock(spec=Request)
    mock_request.path_params = {"id": "not-a-valid-uuid"}

    mock_user = _user()
    mock_service = AsyncMock()

    with pytest.raises(BadRequestError, match="Invalid resource ID format"):
        await validation_fn(
            request=mock_request,
            current_user=mock_user,
            service=mock_service,
        )


async def test_check_ownership_resource_not_found() -> None:
    """Test check_ownership raises NotFoundError if resource does not exist in DB."""
    validation_fn = check_ownership("projects.use_cases", param_name="id")

    resource_id = uuid.uuid4()
    mock_request = MagicMock(spec=Request)
    mock_request.path_params = {"id": str(resource_id)}

    mock_user = _user()
    mock_service = AsyncMock()
    mock_service.get_list.return_value = {"founds": []}

    with pytest.raises(NotFoundError, match="Resource not found"):
        await validation_fn(
            request=mock_request,
            current_user=mock_user,
            service=mock_service,
        )


async def test_check_ownership_not_authorized() -> None:
    """Test check_ownership raises PermissionDeniedError if current user is not the owner of the resource."""
    validation_fn = check_ownership("projects.use_cases", param_name="id")

    resource_id = uuid.uuid4()
    mock_request = MagicMock(spec=Request)
    mock_request.path_params = {"id": str(resource_id)}

    mock_user = _user()
    mock_user.username = Username("other_user")

    mock_resource = MagicMock()
    mock_resource.user_id = uuid.uuid4()

    mock_service = AsyncMock()
    mock_service.get_list.return_value = {"founds": [mock_resource]}

    with pytest.raises(PermissionDeniedError, match="Not authorized to access this resource"):
        await validation_fn(
            request=mock_request,
            current_user=mock_user,
            service=mock_service,
        )
