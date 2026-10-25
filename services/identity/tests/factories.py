import uuid
from typing import Any

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.users.infrastructure.persistence.models import Users

fake = Faker()


def create_user(*, password: str = "SecurePass123!", email: str | None = None, **kwargs: Any) -> Users:
    """Generate a mock user with standard hashed password and unique email/username."""
    resolved_email = email or fake.unique.email()
    resolved_username = kwargs.pop("username", resolved_email.split("@")[0])
    return Users(
        id=uuid.uuid4(),
        email=resolved_email,
        username=resolved_username,
        created_by="system_seeder",
        updated_by="system_seeder",
        password=hash_password(password),
        **kwargs,
    )


async def load_test_data(session: AsyncSession) -> dict[str, list[Any]]:
    """Seed the database with the standard mock users used by the integration tests."""
    first_user = create_user(email="first_user@email.com")
    second_user = create_user(email="second_user@email.com")
    users = [first_user, second_user]
    session.add_all(users)
    await session.flush()
    return {"users": users}
