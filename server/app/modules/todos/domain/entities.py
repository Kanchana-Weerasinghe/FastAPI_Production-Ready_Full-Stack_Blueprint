"""Persistence-independent todo data used by application workflows."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class AttachmentSnapshot:
    """Attachment data required when presenting a todo aggregate."""

    id: UUID
    file_name: str
    file_size: int
    file_type: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class TodoRecord:
    """Todo state exposed outside the SQLAlchemy adapter."""

    id: UUID
    user_id: UUID
    title: str
    description: str | None
    is_completed: bool
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    version: int
    attachments: list[AttachmentSnapshot] = field(default_factory=list)
