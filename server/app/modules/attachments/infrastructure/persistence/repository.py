from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attachments.domain.entities import AttachmentRecord
from app.modules.attachments.infrastructure.persistence.models import Attachments
from app.shared.repository import BaseRepository


class AttachmentRepository(BaseRepository[Attachments, BaseModel]):
    """
    Repository layer for managing Attachment data.

    Handles persistence logic for files and their associations with other entities.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(model=Attachments, session=session)

    @staticmethod
    def _to_entity(model: Attachments) -> AttachmentRecord:
        return AttachmentRecord(
            id=model.id,
            user_id=model.user_id,
            todo_id=model.todo_id,
            file_name=model.file_name,
            storage_key=model.storage_key,
            file_size=model.file_size,
            file_type=model.file_type,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
        )

    async def list_attachments(self, filters: dict[str, Any]) -> dict[str, Any]:
        result = await self.read_by_options(filters)
        return {**result, "founds": [self._to_entity(item) for item in result["founds"]]}

    async def get_attachment(self, attachment_id: UUID) -> AttachmentRecord:
        return self._to_entity(await self.read_by_id(attachment_id))

    async def create_attachment(self, values: dict[str, Any]) -> AttachmentRecord:
        return self._to_entity(await super().create(values))

    async def update_attachment(self, attachment_id: UUID, values: dict[str, Any]) -> AttachmentRecord:
        model = await self.read_by_id(attachment_id)
        return self._to_entity(await super().update(model, values))

    async def delete_attachment(self, attachment_id: UUID) -> None:
        await super().delete(await self.read_by_id(attachment_id))

    async def link_to_todo(self, attachment_id: UUID, todo_id: UUID) -> AttachmentRecord:
        model = await self.read_by_id(attachment_id)
        return self._to_entity(await self.update_attribute(model, "todo_id", todo_id))
