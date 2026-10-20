from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.config import config
from app.core.logging import logger
from app.modules.audit.service import AuditService
from app.modules.users.application.ports.user_repository import UserRepositoryPort
from app.modules.users.domain.entities import AccountAccess, UserAccount
from app.shared.storage import FileStorage
from app.shared.unit_of_work import UnitOfWork


class UserService:
    """Users application API; orchestrates account use cases through application ports."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        uow: UnitOfWork,
        storage: FileStorage,
        audit: AuditService,
    ) -> None:
        self.audit = audit
        self._users = user_repository
        self.uow = uow
        self.storage = storage

    async def get_list(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await self._users.list_accounts(filters)

    async def get_by_id(self, user_id: UUID) -> UserAccount:
        return await self._users.get_account_by_id(user_id)

    async def get_by_email(self, email: str) -> UserAccount | None:
        return await self._users.find_by_email(email)

    async def create_user(self, *, email: str, password_hash: str, username: str) -> UserAccount:
        logger.info("user_creation_started")
        return await self._users.create_account(
            {
                "email": email,
                "password": password_hash,
                "username": username,
                "created_by": username,
                "updated_by": username,
            }
        )

    async def delete_account(self, user: UserAccount) -> None:
        """Deletes the account and schedules file cleanup only after the transaction commits."""
        await self._users.delete_account(user.id)
        await self.audit.record("user.deleted", actor_id=user.id, resource_type="user", resource_id=user.id)
        self.uow.after_commit(self.storage.delete_owner, user.id)

    @staticmethod
    def is_locked(user: UserAccount) -> bool:
        return AccountAccess(user.locked_until).is_locked()

    async def record_failed_login(self, user: UserAccount) -> None:
        """Atomically counts a failure and preserves it when the authentication response fails."""
        lock_until = datetime.now(UTC) + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)
        await self._users.register_failed_login(user.id, config.LOGIN_MAX_FAILED_ATTEMPTS, lock_until)
        self.uow.persist_on_failure()
        logger.warning("login_failed_recorded", user_id=user.id)

    async def reset_failed_logins(self, user: UserAccount) -> None:
        if user.failed_login_attempts or user.locked_until:
            user.apply(await self._users.update_account(user.id, {"failed_login_attempts": 0, "locked_until": None}))

    async def set_password(self, user: UserAccount, password_hash: str) -> None:
        """Changes credentials and revokes every outstanding access token."""
        updated = await self._users.update_account(
            user.id,
            {"password": password_hash, "updated_by": user.username},
        )
        user.apply(updated)
        await self.revoke_access_tokens(user)

    async def revoke_access_tokens(self, user: UserAccount) -> None:
        user.token_version = await self._users.increment_token_version(user.id)

    async def mark_email_verified(self, user: UserAccount) -> None:
        if user.email_verified_at is None:
            user.apply(await self._users.update_account(user.id, {"email_verified_at": datetime.now(UTC)}))

    async def set_mfa_secret(self, user: UserAccount, encrypted_secret: str | None, *, enabled: bool) -> None:
        user.apply(
            await self._users.update_account(
                user.id,
                {
                    "mfa_secret_encrypted": encrypted_secret,
                    "mfa_enabled_at": datetime.now(UTC) if enabled else None,
                },
            )
        )
