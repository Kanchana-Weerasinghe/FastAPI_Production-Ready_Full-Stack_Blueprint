import uuid
from datetime import UTC, datetime
from typing import Any

from app.modules.users.application.ports.user_repository import UserRepository
from app.modules.users.domain.entities import UserAccount
from app.modules.users.domain.value_objects import EmailAddress, PasswordHash, Role, Username
from app.modules.users.infrastructure.persistence.models import Users


class FakeUserRepository(UserRepository):
    """In-memory implementation of the `UserRepository` port, for use-case tests without a database."""

    def __init__(self) -> None:
        self.users_db: list[Users] = []

    @staticmethod
    def _to_entity(user: Users) -> UserAccount:
        return UserAccount(
            id=user.id,
            email=EmailAddress(user.email),
            username=Username(user.username),
            password_hash=PasswordHash(user._password),
            role=Role.parse(user.role or "user"),
            token_version=user.token_version or 0,
            email_verified_at=user.email_verified_at,
            failed_login_attempts=user.failed_login_attempts or 0,
            locked_until=user.locked_until,
            mfa_secret_encrypted=user.mfa_secret_encrypted,
            mfa_enabled_at=user.mfa_enabled_at,
            created_at=user.created_at or datetime.now(UTC),
            is_active=user.is_active if user.is_active is not None else True,
            is_deleted=user.is_deleted if user.is_deleted is not None else False,
        )

    def _row(self, user_id: uuid.UUID) -> Users:
        user = next((item for item in self.users_db if item.id == user_id), None)
        if user is None:
            raise ValueError("User not found")
        return user

    async def get_account_by_id(self, user_id: uuid.UUID) -> UserAccount:
        return self._to_entity(self._row(user_id))

    async def find_by_email(self, email: str) -> UserAccount | None:
        user = next((item for item in self.users_db if item.email == email), None)
        return self._to_entity(user) if user is not None else None

    async def list_accounts(self, filters: dict[str, Any]) -> dict[str, Any]:
        email = filters.get("email__eq") or filters.get("email")
        founds = [user for user in self.users_db if email is None or user.email == email]
        return {"founds": [self._to_entity(user) for user in founds], "total": len(founds)}

    async def create_account(self, values: dict[str, Any]) -> UserAccount:
        user = Users(
            id=uuid.uuid4(),
            email=values["email"],
            username=values["username"],
            _password=values["password"],
            created_by=values.get("created_by", values["username"]),
            updated_by=values.get("updated_by", values["username"]),
        )
        self.users_db.append(user)
        return self._to_entity(user)

    async def update_account(self, user_id: uuid.UUID, values: dict[str, Any]) -> UserAccount:
        user = self._row(user_id)
        for key, value in values.items():
            if key == "password":
                user._password = value
            elif hasattr(user, key):
                setattr(user, key, value)
        return self._to_entity(user)

    async def delete_account(self, user_id: uuid.UUID) -> None:
        self.users_db[:] = [user for user in self.users_db if user.id != user_id]

    async def register_failed_login(self, user_id: uuid.UUID, max_attempts: int, lock_until: datetime) -> None:
        user = next((item for item in self.users_db if item.id == user_id), None)
        if user is None:
            return
        attempts = (user.failed_login_attempts or 0) + 1
        user.failed_login_attempts = 0 if attempts >= max_attempts else attempts
        if attempts >= max_attempts:
            user.locked_until = lock_until

    async def increment_token_version(self, user_id: uuid.UUID) -> int:
        user = self._row(user_id)
        user.token_version = (user.token_version or 0) + 1
        return user.token_version
