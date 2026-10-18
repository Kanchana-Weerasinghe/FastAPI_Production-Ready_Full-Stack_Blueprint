import mimetypes
import random
import uuid
from pathlib import Path
from typing import Any

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.security import hash_password
from app.modules.attachments.infrastructure.persistence.models import Attachments
from app.modules.todos.infrastructure.persistence.models import Todos
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


def create_todo(user_id: uuid.UUID, count: int = 1, *, is_active: bool = True, **kwargs: Any) -> list[Todos]:
    """Generate a list of mock todos associated with a specific user."""
    created_by = kwargs.pop("created_by", "system_seeder")
    updated_by = kwargs.pop("updated_by", "system_seeder")
    return [
        Todos(
            id=uuid.uuid4(),
            user_id=user_id,
            title=fake.catch_phrase(),
            description=fake.sentence(nb_words=10),
            is_completed=fake.boolean(chance_of_getting_true=25),
            is_active=is_active,
            created_by=created_by,
            updated_by=updated_by,
            **kwargs,
        )
        for _ in range(count)
    ]


def create_attachment(
    user_id: uuid.UUID, todo_id: uuid.UUID | None = None, count: int = 1, **kwargs: Any
) -> list[Attachments]:
    """Generate a list of mock file attachments with configured extensions and MIME types."""
    created_by = kwargs.pop("created_by", "system_seeder")
    updated_by = kwargs.pop("updated_by", "system_seeder")
    return [
        Attachments(
            id=(attachment_id := uuid.uuid4()),
            user_id=user_id,
            todo_id=todo_id,
            file_name=(
                file_name := f"{fake.word()}_{uuid.uuid4().hex[:4]}{random.choice(config.ALLOWED_FILE_EXTENSIONS)}"
            ),
            storage_key=f"{user_id}/{attachment_id}{Path(file_name).suffix}",
            file_size=random.randint(1024, 5242880),
            file_type=mimetypes.guess_type(file_name)[0] or "application/octet-stream",
            created_by=created_by,
            updated_by=updated_by,
            **kwargs,
        )
        for _ in range(count)
    ]


async def load_test_data(session: AsyncSession) -> dict[str, list[Any]]:
    """Seed the database with a standard set of mock users, todos, and attachments for testing."""
    first_user = create_user(email="first_user@email.com")
    second_user = create_user(email="second_user@email.com")
    users = [first_user, second_user]
    session.add_all(users)

    seeded_todos: list[Todos] = []
    seeded_attachments: list[Attachments] = []

    first_user_active_todos = create_todo(
        user_id=first_user.id, count=16, is_active=True, created_by=first_user.username, updated_by=first_user.username
    )
    first_user_archived_todos = create_todo(
        user_id=first_user.id, count=15, is_active=False, created_by=first_user.username, updated_by=first_user.username
    )
    session.add_all(first_user_active_todos + first_user_archived_todos)
    seeded_todos.extend(first_user_active_todos + first_user_archived_todos)

    second_user_active_todos = create_todo(
        user_id=second_user.id,
        count=16,
        is_active=True,
        created_by=second_user.username,
        updated_by=second_user.username,
    )
    second_user_archived_todos = create_todo(
        user_id=second_user.id,
        count=15,
        is_active=False,
        created_by=second_user.username,
        updated_by=second_user.username,
    )
    session.add_all(second_user_active_todos + second_user_archived_todos)
    seeded_todos.extend(second_user_active_todos + second_user_archived_todos)

    selected_todos = random.sample(seeded_todos, min(len(seeded_todos), 15))

    for todo in selected_todos:
        username = first_user.username if todo.user_id == first_user.id else second_user.username
        attachments = create_attachment(
            user_id=todo.user_id, todo_id=todo.id, count=1, created_by=username, updated_by=username
        )
        session.add_all(attachments)
        seeded_attachments.extend(attachments)

    await session.flush()
    return {
        "users": users,
        "todos": seeded_todos,
        "attachments": seeded_attachments,
    }
