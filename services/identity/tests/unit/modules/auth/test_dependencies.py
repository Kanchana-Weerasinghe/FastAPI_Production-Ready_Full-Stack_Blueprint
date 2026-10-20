import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import Request

from app.core.errors import AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError
from app.modules.auth.dependencies import check_ownership, get_current_user
from app.modules.users.domain.value_objects import EmailAddress, Username
from app.modules.users.service import UserAccount


def _user(token_version: int = 0, user_id: UUID | None = None) -> UserAccount:
    return UserAccount(
        id=user_id or uuid.uuid4(),
        email=EmailAddress("test@example.com"),
        username=Username("test_user"),
        password_hash="hashed",
        role="user",
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


async def test_get_current_user_success() -> None:
    """Test get_current_user returns the user when the token's version matches the user's token_version."""
    user = _user(token_version=2)
    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = user
    result = await get_current_user(claims={"sub": str(user.id), "ver": 2}, service=mock_service)
    assert result.id == user.id
    mock_service.get_by_id.assert_called_once_with(user.id)


async def test_get_current_user_revoked_token_version() -> None:
    """Test get_current_user rejects tokens issued before the user's token_version was bumped."""
    user = _user(token_version=3)
    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = user
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(claims={"sub": str(user.id), "ver": 2}, service=mock_service)
    assert exc_info.value.code == "token_revoked"


async def test_get_current_user_invalid_subject() -> None:
    """Test get_current_user raises AuthenticationError when the subject claim is missing or malformed."""
    for claims in ({}, {"sub": "not-a-uuid"}):
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await get_current_user(claims=claims, service=AsyncMock())


async def test_get_current_user_not_found() -> None:
    """Test get_current_user raises AuthenticationError when the user no longer exists."""
    mock_service = AsyncMock()
    mock_service.get_by_id.side_effect = NotFoundError("Record not found")
    with pytest.raises(AuthenticationError, match="User not found"):
        await get_current_user(claims={"sub": str(uuid.uuid4()), "ver": 0}, service=mock_service)


async def test_check_ownership_success() -> None:
    """Test check_ownership successfully validates resource ownership."""
    validation_fn = check_ownership("todos.service", param_name="id", is_active=True)

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
    validation_fn = check_ownership("todos.service", param_name="id")

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
    validation_fn = check_ownership("todos.service", param_name="id")

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
    validation_fn = check_ownership("todos.service", param_name="id")

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
    validation_fn = check_ownership("todos.service", param_name="id")

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
