"""Persistence contract for attachment workflows."""

from typing import Any, Protocol
from uuid import UUID

from app.modules.attachments.domain.entities import AttachmentRecord


class AttachmentRepositoryPort(Protocol):
    async def list_attachments(self, filters: dict[str, Any]) -> dict[str, Any]: ...

    async def get_attachment(self, attachment_id: UUID) -> AttachmentRecord: ...

    async def create_attachment(self, values: dict[str, Any]) -> AttachmentRecord: ...

    async def update_attachment(self, attachment_id: UUID, values: dict[str, Any]) -> AttachmentRecord: ...

    async def delete_attachment(self, attachment_id: UUID) -> None: ...

    async def link_to_todo(self, attachment_id: UUID, todo_id: UUID) -> AttachmentRecord: ...
