from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.entities import UserAccount
from app.modules.users.domain.value_objects import EmailAddress, Username
from app.modules.users.infrastructure.persistence.models import Users
from app.shared.repository import BaseRepository


class UserRepository(BaseRepository[Users, BaseModel]):
    """
    Repository layer for managing User accounts.

    Handles user profile persistence and authentication-related lookups.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(model=Users, session=session)

    @staticmethod
    def _to_entity(user: Users) -> UserAccount:
        """Maps a row to the entity, rebuilding the value objects from the stored strings."""
        return UserAccount(
            id=user.id,
            email=EmailAddress(user.email),
            username=Username(user.username),
            password_hash=user._password,
            role=user.role,
            token_version=user.token_version,
            email_verified_at=user.email_verified_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            mfa_secret_encrypted=user.mfa_secret_encrypted,
            mfa_enabled_at=user.mfa_enabled_at,
            created_at=user.created_at,
            is_active=user.is_active,
            is_deleted=user.is_deleted,
        )

    async def get_account_by_id(self, user_id: UUID) -> UserAccount:
        return self._to_entity(await self.read_by_id(user_id))

    async def find_by_email(self, email: str) -> UserAccount | None:
        result = await self.read_by_options({"email__eq": email, "page_size": 1})
        users: list[Users] = result["founds"]
        return self._to_entity(users[0]) if users else None

    async def list_accounts(self, filters: dict[str, Any]) -> dict[str, Any]:
        result = await self.read_by_options(filters)
        return {
            **result,
            "founds": [self._to_entity(user) for user in result["founds"]],
        }

    async def create_account(self, values: dict[str, Any]) -> UserAccount:
        return self._to_entity(await super().create(values))

    async def update_account(self, user_id: UUID, values: dict[str, Any]) -> UserAccount:
        user = await self.read_by_id(user_id)
        return self._to_entity(await super().update(user, values))

    async def delete_account(self, user_id: UUID) -> None:
        await super().delete(await self.read_by_id(user_id))

    async def register_failed_login(self, user_id: UUID, max_attempts: int, lock_until: datetime) -> None:
        """Atomically increments the failure counter and locks the account when it reaches `max_attempts`."""
        attempts = Users.failed_login_attempts + 1
        await self.session.execute(
            update(Users)
            .where(Users.id == user_id)
            .values(
                failed_login_attempts=case((attempts >= max_attempts, 0), else_=attempts),
                locked_until=case((attempts >= max_attempts, lock_until), else_=Users.locked_until),
                # Core UPDATEs bypass the ORM's optimistic locking, so bump the version explicitly.
                version=Users.version + 1,
            )
        )

    async def increment_token_version(self, user_id: UUID) -> int:
        result = await self.session.execute(
            update(Users)
            .where(Users.id == user_id)
            .values(token_version=Users.token_version + 1, version=Users.version + 1)
            .returning(Users.token_version)
        )
        return result.scalar_one()
