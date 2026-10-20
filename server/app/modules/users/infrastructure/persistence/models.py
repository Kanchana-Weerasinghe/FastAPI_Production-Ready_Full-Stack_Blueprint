from datetime import datetime

from sqlalchemy import TIMESTAMP, Integer, text
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import BaseModel


class Users(BaseModel):
    """Database model representing a user account with authentication details."""

    email: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False, index=True)
    _password: Mapped[str] = mapped_column("password", TEXT, nullable=False)
    # Authorization role; permissions per role live in app/modules/auth/permissions.py.
    role: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, server_default=text("'user'"))
    # Incremented on password change/reset and "sign out everywhere": invalidates all access tokens.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    email_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    # TOTP seed, encrypted at rest with FIELD_ENCRYPTION_KEY. Set during enrolment, active once mfa_enabled_at is set.
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    mfa_enabled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    @property
    def password(self) -> str:
        raise ValueError("Password cannot be accessed directly.")

    @password.setter
    def password(self, password: str) -> None:
        self._password = password

    todos: Mapped[list["Todos"]] = relationship("Todos", back_populates="user", cascade="all, delete-orphan")

    eagers = ["todos"]
