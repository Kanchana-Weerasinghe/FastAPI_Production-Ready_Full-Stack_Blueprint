from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.shared.schemas import CursorPage, CursorParams


class AuditLog(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID
    created_at: datetime
    actor_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    outcome: str
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    details: dict[str, Any]


class FindAuditLog(CursorParams):
    """Filters for the audit trail (newest first, cursor-paginated)."""

    action__eq: str | None = Field(None, alias="action", description="Exact action, e.g. auth.signin.failed")
    actor_id__eq: UUID | None = Field(None, alias="actorId", description="Filter by acting user")
    outcome__eq: str | None = Field(None, alias="outcome", description="success or failure")


class AuditLogPage(CursorPage[AuditLog]):
    pass
