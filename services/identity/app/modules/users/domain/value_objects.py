"""
Value objects of the users domain: small values that validate themselves when created.

They subclass `str`, so a validated `EmailAddress` can go anywhere a string is expected (auth,
email sending, response schemas) while still being impossible to construct with an invalid value.
Like any value object they are immutable and compared by value: `EmailAddress("a@b.io") == "a@b.io"`.
"""

import re

from app.modules.users.domain.exceptions import InvalidEmailAddress, InvalidUsername

EMAIL_MAX_LENGTH = 320  # RFC 5321 limit for a full address
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50

_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_CHARACTERS = re.compile(r"^[A-Za-z0-9._-]+$")


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
