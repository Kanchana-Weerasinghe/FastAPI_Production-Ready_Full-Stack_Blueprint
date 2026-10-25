"""Test data builders and recording fakes shared by the users business-rule tests."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.users.application.use_cases.user_use_cases import UserUseCases
from app.modules.users.domain.entities import UserAccount
from app.modules.users.infrastructure.persistence.models import Users
from tests.mocks.audit import FakeAuditService
from tests.mocks.uow import FakeUnitOfWork
from tests.mocks.user_repository import FakeUserRepository

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
# Shape of a real bcrypt hash (what app.core.security.hash_password produces).
HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeO5EHpKChSJlLpm1AaM6cX9i5n2H2hB7m"
OTHER_HASH = "$2b$12$abcdefghijklmnopqrstuuJ0Fh1y9n7cQ4m9Rz8sQnB3dJ6q9wTzK"


def an_account(**overrides: Any) -> UserAccount:
    """A valid UserAccount; override only what the test is about."""
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "email": "ada@example.com",
        "username": "ADA42",
        "password_hash": HASH,
        "role": "user",
        "token_version": 0,
        "email_verified_at": None,
        "failed_login_attempts": 0,
        "locked_until": None,
        "mfa_secret_encrypted": None,
        "mfa_enabled_at": None,
        "created_at": NOW,
        "is_active": True,
        "is_deleted": False,
    }
    values.update(overrides)
    return UserAccount(**values)


class RecordingUserRepository(FakeUserRepository):
    """In-memory repository that also records every update, so tests can assert what was saved."""

    def __init__(self) -> None:
        super().__init__()
        self.updates: list[dict[str, Any]] = []
        self.deleted: list[uuid.UUID] = []

    def add_row(self, **overrides: Any) -> Users:
        row = Users(
            id=uuid.uuid4(),
            email=overrides.pop("email", f"user_{uuid.uuid4().hex[:6]}@example.com"),
            username=overrides.pop("username", f"U{uuid.uuid4().hex[:7].upper()}"),
            _password=overrides.pop("password", HASH),
            created_by="test",
            updated_by="test",
            **overrides,
        )
        self.users_db.append(row)
        return row

    async def update_account(self, user_id: uuid.UUID, values: dict[str, Any]) -> UserAccount:
        self.updates.append(dict(values))
        return await super().update_account(user_id, values)

    async def delete_account(self, user_id: uuid.UUID) -> None:
        self.deleted.append(user_id)
        await super().delete_account(user_id)


class RecordingStorage:
    """File storage stand-in that records which owners' files were removed."""

    def __init__(self) -> None:
        self.deleted_owners: list[uuid.UUID] = []

    async def delete_owner(self, owner_id: uuid.UUID) -> None:
        self.deleted_owners.append(owner_id)


class UseCaseWorld:
    """Everything a use-case test needs: the use cases wired to in-memory fakes."""

    def __init__(self) -> None:
        self.repository = RecordingUserRepository()
        self.uow = FakeUnitOfWork()
        self.storage = RecordingStorage()
        self.audit = FakeAuditService()
        self.use_cases = UserUseCases(
            user_repository=self.repository,
            uow=self.uow,  # type: ignore[arg-type]
            storage=self.storage,  # type: ignore[arg-type]
            audit=self.audit,  # type: ignore[arg-type]
        )
