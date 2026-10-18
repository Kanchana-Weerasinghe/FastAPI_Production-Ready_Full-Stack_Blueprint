"""Persistence-independent attachment record."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class AttachmentRecord:
    """Attachment metadata and storage reference exposed to application workflows."""

    id: UUID
    user_id: UUID
    todo_id: UUID | None
    file_name: str
    storage_key: str
    file_size: int
    file_type: str
    created_at: datetime
    updated_at: datetime
    version: int
    is_active: bool
    is_deleted: bool
