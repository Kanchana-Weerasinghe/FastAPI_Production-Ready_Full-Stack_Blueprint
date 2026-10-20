import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.infrastructure.persistence.repository import UserRepository
from tests.factories import create_user


async def test_create_user_success(
    user_repository: UserRepository,
) -> None:
    """Test that UserRepository successfully persists a User model in the database."""
    user_data = {
        "email": "repo_user@example.com",
        "username": "repouser",
        "password": "hashedpassword",
        "created_by": "system",
        "updated_by": "system",
    }
    db_user = await user_repository.create(user_data)
    assert db_user.id is not None
    assert db_user.email == "repo_user@example.com"


async def test_read_user_by_id_success(
    user_repository: UserRepository,
    db_session: AsyncSession,
) -> None:
    """Test that UserRepository successfully retrieves a persisted User by their primary key UUID."""
    user_data = create_user(email="repo_find@example.com")
    db_session.add(user_data)
    await db_session.flush()
    db_user = await user_repository.read_by_id(user_data.id)
    assert db_user.email == "repo_find@example.com"
    with pytest.raises(ValueError, match="Password cannot be accessed directly."):
        _ = db_user.password
