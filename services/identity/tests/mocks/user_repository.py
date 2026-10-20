import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from app.modules.users.domain.entities import UserAccount
from app.modules.users.domain.value_objects import EmailAddress, Username
from app.modules.users.infrastructure.persistence.models import Users
from app.modules.users.schemas import FindUser


class MockUserRepository:
    """Mock repository for UserRepository to test AuthService in isolation."""

    def __init__(self) -> None:
        self.users_db: list[Users] = []
        self.read_by_options = AsyncMock(side_effect=self._mock_read_by_options)
        self.create = AsyncMock(side_effect=self._mock_create)
        self.get_account_by_id = AsyncMock(side_effect=self._port_get_by_id)
        self.find_by_email = AsyncMock(side_effect=self._port_get_by_email)
        self.list_accounts = AsyncMock(side_effect=self._port_list)
        self.create_account = AsyncMock(side_effect=self._port_create)
        self.update_account = AsyncMock(side_effect=self._port_update)
        self.delete_account = AsyncMock(side_effect=self._port_delete)
        self.register_failed_login = AsyncMock(side_effect=self._port_register_failed_login)
        self.increment_token_version = AsyncMock(side_effect=self._port_increment_token_version)

    @staticmethod
    def _to_entity(user: Users) -> UserAccount:
        created_at = user.created_at or datetime.now(UTC)
        return UserAccount(
            id=user.id,
            email=EmailAddress(user.email),
            username=Username(user.username),
            password_hash=user._password,
            role=user.role or "user",
            token_version=user.token_version or 0,
            email_verified_at=user.email_verified_at,
            failed_login_attempts=user.failed_login_attempts or 0,
            locked_until=user.locked_until,
            mfa_secret_encrypted=user.mfa_secret_encrypted,
            mfa_enabled_at=user.mfa_enabled_at,
            created_at=created_at,
            is_active=user.is_active if user.is_active is not None else True,
            is_deleted=user.is_deleted if user.is_deleted is not None else False,
        )

    async def _port_get_by_id(self, user_id: uuid.UUID) -> UserAccount:
        user = next((item for item in self.users_db if item.id == user_id), None)
        if user is None:
            raise ValueError("User not found")
        return self._to_entity(user)

    async def _port_get_by_email(self, email: str) -> UserAccount | None:
        user = next((item for item in self.users_db if item.email == email), None)
        return self._to_entity(user) if user is not None else None

    async def _port_list(self, filters: dict[str, Any]) -> dict[str, Any]:
        result = await self.read_by_options(filters)
        return {**result, "founds": [self._to_entity(user) for user in result["founds"]]}

    async def _port_create(self, values: dict[str, Any]) -> UserAccount:
        return self._to_entity(await self.create(values))

    async def _port_update(self, user_id: uuid.UUID, values: dict[str, Any]) -> UserAccount:
        user = next((item for item in self.users_db if item.id == user_id), None)
        if user is None:
            raise ValueError("User not found")
        for key, value in values.items():
            if key == "password":
                user._password = value
            elif hasattr(user, key):
                setattr(user, key, value)
        return self._to_entity(user)

    async def _port_delete(self, user_id: uuid.UUID) -> None:
        self.users_db[:] = [user for user in self.users_db if user.id != user_id]

    async def _port_register_failed_login(self, user_id: uuid.UUID, max_attempts: int, lock_until: datetime) -> None:
        user = next((item for item in self.users_db if item.id == user_id), None)
        if user is None:
            return
        attempts = (user.failed_login_attempts or 0) + 1
        user.failed_login_attempts = 0 if attempts >= max_attempts else attempts
        if attempts >= max_attempts:
            user.locked_until = lock_until

    async def _port_increment_token_version(self, user_id: uuid.UUID) -> int:
        user = next((item for item in self.users_db if item.id == user_id), None)
        if user is None:
            raise ValueError("User not found")
        user.token_version = (user.token_version or 0) + 1
        return user.token_version

    def _mock_read_by_options(self, schema: FindUser | dict[str, Any], _eager: bool = False) -> dict[str, Any]:
        if isinstance(schema, FindUser):
            email = schema.email__eq
        else:
            email = schema.get("email")
        founds = [u for u in self.users_db if u.email == email]
        return {"founds": founds, "total": len(founds)}

    def _mock_create(self, schema: dict[str, Any]) -> Users:
        user = Users(
            id=uuid.uuid4(),
            email=schema["email"],
            username=schema["username"],
            _password=schema["password"],
            created_by=schema.get("created_by", schema["username"]),
            updated_by=schema.get("updated_by", schema["username"]),
        )
        self.users_db.append(user)
        return user
