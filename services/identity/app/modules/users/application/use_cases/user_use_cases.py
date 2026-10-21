"""
Use cases of the users module, grouped in `UserUseCases` (auth and the router call them).

Every method follows the same steps: build or receive the `UserAccount`, let the entity apply its
rule, then persist only the fields that changed. Business decisions live in the domain layer
(`entities.py`, `value_objects.py`, `policies.py`); this file coordinates them with the ports.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.config import config
from app.core.errors import BadRequestError
from app.core.logging import logger
from app.modules.audit.public import AuditService
from app.modules.users.application.ports.user_repository import UserRepository
from app.modules.users.domain.entities import UserAccount
from app.modules.users.domain.exceptions import UserRuleViolation
from app.modules.users.domain.policies import lockout_expiry
from app.modules.users.domain.value_objects import EmailAddress, Username
from app.shared.storage import FileStorage
from app.shared.unit_of_work import UnitOfWork


@contextmanager
def business_rules() -> Iterator[None]:
    """Translates a domain rule violation into an error the HTTP layer renders as 400."""
    try:
        yield
    except UserRuleViolation as e:
        raise BadRequestError(e.message, code=e.code) from e


def _now() -> datetime:
    return datetime.now(UTC)


class UserUseCases:
    """The operations on user accounts: load the account, apply an entity behaviour, save the changes."""

    def __init__(
        self,
        user_repository: UserRepository,
        uow: UnitOfWork,
        storage: FileStorage,
        audit: AuditService,
    ) -> None:
        self.audit = audit
        self._users = user_repository
        self.uow = uow
        self.storage = storage

    # --- Queries --------------------------------------------------------------------------------

    async def get_list(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await self._users.list_accounts(filters)

    async def get_by_id(self, user_id: UUID) -> UserAccount:
        return await self._users.get_account_by_id(user_id)

    async def get_by_email(self, email: str) -> UserAccount | None:
        return await self._users.find_by_email(email)

    @staticmethod
    def is_locked(user: UserAccount) -> bool:
        return user.is_locked(_now())

    # --- Registration and deletion --------------------------------------------------------------

    async def create_user(self, *, email: str, password_hash: str, username: str) -> UserAccount:
        logger.info("user_creation_started")
        with business_rules():
            address, handle = EmailAddress(email), Username(username)
        return await self._users.create_account(
            {
                "email": address,
                "password": password_hash,
                "username": handle,
                "created_by": handle,
                "updated_by": handle,
            }
        )

    async def delete_account(self, user: UserAccount) -> None:
        """Deletes the account and schedules file cleanup only after the transaction commits."""
        await self._users.delete_account(user.id)
        await self.audit.record("user.deleted", actor_id=user.id, resource_type="user", resource_id=user.id)
        self.uow.after_commit(self.storage.delete_owner, user.id)

    # --- Sign-in protection ---------------------------------------------------------------------

    async def record_failed_login(self, user: UserAccount) -> None:
        """Atomically counts a failure and preserves it when the authentication response fails."""
        lock_until = lockout_expiry(now=_now(), lockout_minutes=config.LOGIN_LOCKOUT_MINUTES)
        await self._users.register_failed_login(user.id, config.LOGIN_MAX_FAILED_ATTEMPTS, lock_until)
        self.uow.persist_on_failure()
        logger.warning("login_failed_recorded", user_id=user.id)

    async def reset_failed_logins(self, user: UserAccount) -> None:
        if user.clear_failed_logins():
            await self._save(user, failed_login_attempts=user.failed_login_attempts, locked_until=user.locked_until)

    # --- Credentials ----------------------------------------------------------------------------

    async def set_password(self, user: UserAccount, password_hash: str) -> None:
        """Changes credentials and revokes every outstanding access token."""
        with business_rules():
            user.change_password(password_hash)
        await self._save(user, password=user.password_hash, updated_by=user.username)
        await self.revoke_access_tokens(user)

    async def revoke_access_tokens(self, user: UserAccount) -> None:
        # Atomic increment in the database, so concurrent revocations are never lost.
        user.token_version = await self._users.increment_token_version(user.id)

    async def mark_email_verified(self, user: UserAccount) -> None:
        if user.verify_email(at=_now()):
            await self._save(user, email_verified_at=user.email_verified_at)

    async def set_mfa_secret(self, user: UserAccount, encrypted_secret: str | None, *, enabled: bool) -> None:
        """Start (`enabled=False`), activate (`enabled=True`) or remove (`encrypted_secret=None`) MFA."""
        with business_rules():
            if encrypted_secret is None:
                user.disable_mfa()
            elif enabled:
                user.enable_mfa(at=_now())
            else:
                user.start_mfa_setup(encrypted_secret)
        await self._save(user, mfa_secret_encrypted=user.mfa_secret_encrypted, mfa_enabled_at=user.mfa_enabled_at)

    # --- Persistence ----------------------------------------------------------------------------

    async def _save(self, user: UserAccount, **changed: Any) -> None:
        """Persists only the changed columns, then refreshes the entity from the stored row."""
        user.apply(await self._users.update_account(user.id, changed))
