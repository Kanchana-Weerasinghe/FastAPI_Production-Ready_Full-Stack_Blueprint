"""Persistence-independent authentication token records."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class RefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_id: UUID | None
    user_agent: str | None
    ip_address: str | None
    created_by: str
    updated_by: str


@dataclass(slots=True)
class OneTimeToken:
    id: UUID
    user_id: UUID
    purpose: str
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_by: str
    updated_by: str
