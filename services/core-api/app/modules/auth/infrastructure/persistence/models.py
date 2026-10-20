from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class RefreshTokens(BaseModel):
    """
    A refresh token issued to one device/session. Only the SHA-256 hash is stored.

    Tokens rotate on every use: the used token is revoked and points to its replacement. All tokens
    descending from one sign-in share a `family_id`; presenting an already-rotated token means it was
    stolen, so the whole family is revoked.
    """

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, unique=True, index=True)
    family_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)


class OneTimeTokens(BaseModel):
    """
    Single-use, expiring tokens for email verification and password reset. Only the hash is stored;
    `used_at` makes them single-use.
    """

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
