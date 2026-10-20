"""Pure domain representation for account access-state decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass(slots=True)
class UserAccount:
    """User account data required by application workflows, without ORM behavior."""

    id: UUID
    email: str
    username: str
    password_hash: str
    role: str
    token_version: int
    email_verified_at: datetime | None
    failed_login_attempts: int
    locked_until: datetime | None
    mfa_secret_encrypted: str | None
    mfa_enabled_at: datetime | None
    created_at: datetime
    is_active: bool
    is_deleted: bool

    def apply(self, other: UserAccount) -> None:
        """Refresh mutable account state after a persistence operation."""
        self.email = other.email
        self.username = other.username
        self.password_hash = other.password_hash
        self.role = other.role
        self.token_version = other.token_version
        self.email_verified_at = other.email_verified_at
        self.failed_login_attempts = other.failed_login_attempts
        self.locked_until = other.locked_until
        self.mfa_secret_encrypted = other.mfa_secret_encrypted
        self.mfa_enabled_at = other.mfa_enabled_at
        self.created_at = other.created_at
        self.is_active = other.is_active
        self.is_deleted = other.is_deleted


@dataclass(frozen=True, slots=True)
class AccountAccess:
    """The lockout state relevant to deciding whether an account may sign in."""

    locked_until: datetime | None

    def is_locked(self, now: datetime | None = None) -> bool:
        """Treat only a future, timezone-aware lock expiry as an active lock."""
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None:
            raise ValueError("Account lock checks require a timezone-aware datetime")
        return self.locked_until is not None and self.locked_until > current_time
