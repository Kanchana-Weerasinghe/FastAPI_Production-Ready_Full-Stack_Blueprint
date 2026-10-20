"""
Value objects of the users domain: small values that validate themselves when created.

They subclass `str`, so a validated `EmailAddress` can go anywhere a string is expected (auth,
email sending, response schemas) while still being impossible to construct with an invalid value.
Like any value object they are immutable and compared by value: `EmailAddress("a@b.io") == "a@b.io"`.
"""

import re
from enum import StrEnum

from app.modules.users.domain.exceptions import InvalidEmailAddress, InvalidPasswordHash, InvalidRole, InvalidUsername

EMAIL_MAX_LENGTH = 320  # RFC 5321 limit for a full address
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50

_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_CHARACTERS = re.compile(r"^[A-Za-z0-9._-]+$")
# bcrypt modular-crypt format: $2a$/$2b$/$2y$, two-digit cost, 22-char salt + 31-char digest.
_BCRYPT_HASH = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


class EmailAddress(str):
    """A syntactically valid email address, trimmed. Case is kept: lookups are exact-match."""

    __slots__ = ()

    def __new__(cls, value: str) -> "EmailAddress":
        cleaned = value.strip()
        if len(cleaned) > EMAIL_MAX_LENGTH or not _EMAIL_SHAPE.fullmatch(cleaned):
            raise InvalidEmailAddress("Enter a valid email address")
        return super().__new__(cls, cleaned)


class Username(str):
    """A public handle: 3-50 letters, digits, dots, underscores or hyphens."""

    __slots__ = ()

    def __new__(cls, value: str) -> "Username":
        cleaned = value.strip()
        if not USERNAME_MIN_LENGTH <= len(cleaned) <= USERNAME_MAX_LENGTH:
            raise InvalidUsername(f"Username must contain {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters")
        if not _USERNAME_CHARACTERS.fullmatch(cleaned):
            raise InvalidUsername("Username may only contain letters, digits, dots, underscores and hyphens")
        return super().__new__(cls, cleaned)


class PasswordHash(str):
    """A bcrypt hash. Rejecting anything else stops a plain password from ever being stored."""

    __slots__ = ()

    def __new__(cls, value: str) -> "PasswordHash":
        if not _BCRYPT_HASH.fullmatch(value):
            raise InvalidPasswordHash("Expected a bcrypt password hash, never a plain password")
        return super().__new__(cls, value)


class Role(StrEnum):
    """What kind of account this is. Permissions per role are decided by the auth module."""

    USER = "user"
    ADMIN = "admin"

    @classmethod
    def parse(cls, value: str) -> "Role":
        try:
            return cls(value)
        except ValueError as e:
            raise InvalidRole(f"Unknown role: {value!r}") from e
