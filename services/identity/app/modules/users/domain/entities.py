"""
The UserAccount entity: one person's account and the rules for changing it.

It has an identity (`id`) that stays the same while its state changes, is built from value
objects (`EmailAddress`, `Username`), and changes only through its behaviour methods. Plain
Python: no FastAPI, Pydantic or SQLAlchemy, and the clock is passed in so rules are testable.

MFA lifecycle:

    no MFA --start_mfa_setup--> secret pending --enable_mfa--> MFA enabled
       ^                                                           |
       +------------------------- disable_mfa ---------------------+
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.users.domain.exceptions import InvalidPasswordHash, MfaAlreadyEnabled, MfaNotStarted


@dataclass(slots=True)
class UserAccount:
    # --- Properties -------------------------------------------------------------------------
    id: UUID
    email: str  # an EmailAddress when created through UserService
    username: str  # a Username when created through UserService
    password_hash: str  # never the plain password
    role: str
    token_version: int  # bumped to revoke every access token issued so far
    email_verified_at: datetime | None
    failed_login_attempts: int
    locked_until: datetime | None
    mfa_secret_encrypted: str | None
    mfa_enabled_at: datetime | None
    created_at: datetime
    is_active: bool
    is_deleted: bool

    # --- Business questions -----------------------------------------------------------------
    def is_locked(self, now: datetime) -> bool:
        """Only a lock expiry in the future blocks sign-in."""
        if now.tzinfo is None:
            raise ValueError("Account lock checks require a timezone-aware datetime")
        return self.locked_until is not None and self.locked_until > now

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_mfa_enabled(self) -> bool:
        return self.mfa_enabled_at is not None

    @property
    def has_failed_logins(self) -> bool:
        return bool(self.failed_login_attempts or self.locked_until)

    # --- Behaviours (each returns whether anything changed, so callers save only real changes) ---
    def verify_email(self, *, at: datetime) -> bool:
        if self.is_email_verified:
            return False  # verifying twice keeps the original timestamp
        self.email_verified_at = at
        return True

    def clear_failed_logins(self) -> bool:
        if not self.has_failed_logins:
            return False
        self.failed_login_attempts = 0
        self.locked_until = None
        return True

    def change_password(self, password_hash: str) -> None:
        """Stores a new hash. Revoking existing sessions is the use case's job (atomic counter)."""
        if not password_hash:
            raise InvalidPasswordHash("A password hash is required")
        self.password_hash = password_hash

    def start_mfa_setup(self, encrypted_secret: str) -> None:
        """Stores a new, not yet active TOTP secret."""
        if self.is_mfa_enabled:
            raise MfaAlreadyEnabled("MFA is already enabled")
        self.mfa_secret_encrypted = encrypted_secret
        self.mfa_enabled_at = None

    def enable_mfa(self, *, at: datetime) -> None:
        """Activates the pending secret after the user proved they can generate codes."""
        if self.mfa_secret_encrypted is None:
            raise MfaNotStarted("Start MFA setup first")
        self.mfa_enabled_at = at

    def disable_mfa(self) -> None:
        self.mfa_secret_encrypted = None
        self.mfa_enabled_at = None

    # --- Persistence support ----------------------------------------------------------------
    def apply(self, other: UserAccount) -> None:
        """Refresh this object with the state the repository returned after saving."""
        for name in self.__slots__:
            setattr(self, name, getattr(other, name))
