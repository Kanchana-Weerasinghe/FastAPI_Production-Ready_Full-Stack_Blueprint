from typing import Any
from uuid import UUID

from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB, TEXT, VARCHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class AuditLogs(BaseModel):
    """
    Append-only record of security-relevant and administrative actions (who did what, when, from where).

    Rows are never updated or deleted by the application. `actor_id` is not a foreign key on purpose:
    the trail must survive deletion of the account it refers to.
    """

    __table_args__ = (
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    actor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(VARCHAR(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True)
    outcome: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    request_id: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
