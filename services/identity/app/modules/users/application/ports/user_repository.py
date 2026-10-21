"""
Port: what the user use cases need from storage.

An abstract base class, so every implementation says so explicitly (`class X(UserRepository)`) and
Python refuses to create one that forgets a method. Implementations:
`SqlAlchemyUserRepository` (infrastructure) and `FakeUserRepository` (tests).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.users.domain.entities import UserAccount


class UserRepository(ABC):
    @abstractmethod
    async def get_account_by_id(self, user_id: UUID) -> UserAccount: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> UserAccount | None: ...

    @abstractmethod
    async def list_accounts(self, filters: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def create_account(self, values: dict[str, Any]) -> UserAccount: ...

    @abstractmethod
    async def update_account(self, user_id: UUID, values: dict[str, Any]) -> UserAccount: ...

    @abstractmethod
    async def delete_account(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def register_failed_login(self, user_id: UUID, max_attempts: int, lock_until: datetime) -> None:
        """Atomically counts a failed sign-in and locks the account when it reaches `max_attempts`."""

    @abstractmethod
    async def increment_token_version(self, user_id: UUID) -> int:
        """Atomically bumps the token version (revokes every access token) and returns the new value."""
