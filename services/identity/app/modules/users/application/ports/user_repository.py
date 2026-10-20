"""Persistence contract for user account use cases."""

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.modules.users.domain.entities import UserAccount


class UserRepositoryPort(Protocol):
    """Application-facing operations implemented by the users persistence adapter."""

    async def get_account_by_id(self, user_id: UUID) -> UserAccount: ...

    async def find_by_email(self, email: str) -> UserAccount | None: ...

    async def list_accounts(self, filters: dict[str, Any]) -> dict[str, Any]: ...

    async def create_account(self, values: dict[str, Any]) -> UserAccount: ...

    async def update_account(self, user_id: UUID, values: dict[str, Any]) -> UserAccount: ...

    async def delete_account(self, user_id: UUID) -> None: ...

    async def register_failed_login(self, user_id: UUID, max_attempts: int, lock_until: datetime) -> None: ...

    async def increment_token_version(self, user_id: UUID) -> int: ...
