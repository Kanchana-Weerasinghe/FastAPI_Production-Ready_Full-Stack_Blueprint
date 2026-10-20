"""Persistence-independent audit record."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class AuditEntry:
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
