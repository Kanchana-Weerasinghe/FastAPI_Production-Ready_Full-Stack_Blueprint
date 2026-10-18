import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from app.modules.attachments.domain.entities import AttachmentRecord
from app.modules.attachments.infrastructure.persistence.models import Attachments


class MockAttachmentRepository:
    """Mock repository for AttachmentRepository to test TodoService and AttachmentService in isolation."""

    def __init__(self) -> None:
        self.attachments_db: list[Attachments] = []
        self.read_by_options = AsyncMock(side_effect=self._mock_read_by_options)
        self.read_by_id = AsyncMock(side_effect=self._mock_read_by_id)
        self.create = AsyncMock(side_effect=self._mock_create)
        self.update = AsyncMock(side_effect=self._mock_update)
        self.update_attribute = AsyncMock(side_effect=self._mock_update_attribute)
        self.delete = AsyncMock(side_effect=self._mock_delete)
        self.list_attachments = AsyncMock(side_effect=self._port_list)
        self.get_attachment = AsyncMock(side_effect=self._port_get)
        self.create_attachment = AsyncMock(side_effect=self._port_create)
        self.update_attachment = AsyncMock(side_effect=self._port_update)
        self.delete_attachment = AsyncMock(side_effect=self._port_delete)
        self.link_to_todo = AsyncMock(side_effect=self._port_link)

    @staticmethod
    def _to_entity(model: Attachments) -> AttachmentRecord:
        created_at = model.created_at or datetime.now(UTC)
        return AttachmentRecord(
            id=model.id,
            user_id=model.user_id,
            todo_id=model.todo_id,
            file_name=model.file_name,
            storage_key=model.storage_key,
            file_size=model.file_size,
            file_type=model.file_type,
            created_at=created_at,
            updated_at=model.updated_at or created_at,
            version=model.version or 1,
            is_active=model.is_active if model.is_active is not None else True,
            is_deleted=model.is_deleted if model.is_deleted is not None else False,
        )

    async def _port_list(self, filters: dict[str, Any]) -> dict[str, Any]:
        result = await self.read_by_options(filters)
        return {**result, "founds": [self._to_entity(row) for row in result["founds"]]}

    async def _port_get(self, attachment_id: uuid.UUID) -> AttachmentRecord:
        return self._to_entity(await self.read_by_id(attachment_id))

    async def _port_create(self, values: dict[str, Any]) -> AttachmentRecord:
        return self._to_entity(await self.create(values))

    async def _port_update(self, attachment_id: uuid.UUID, values: dict[str, Any]) -> AttachmentRecord:
        return self._to_entity(await self.update(await self.read_by_id(attachment_id), values))

    async def _port_delete(self, attachment_id: uuid.UUID) -> None:
        await self.delete(await self.read_by_id(attachment_id))

    async def _port_link(self, attachment_id: uuid.UUID, todo_id: uuid.UUID) -> AttachmentRecord:
        return self._to_entity(await self.update_attribute(await self.read_by_id(attachment_id), "todo_id", todo_id))

    def _mock_read_by_options(self, schema: Any, _eager: bool = False) -> dict[str, Any]:
        user_id = schema.user_id if hasattr(schema, "user_id") else schema.get("user_id")
        founds = [a for a in self.attachments_db if a.user_id == user_id]
        return {"founds": founds, "total": len(founds)}

    def _mock_read_by_id(self, id: uuid.UUID, _eager: bool = False) -> Attachments:
        for a in self.attachments_db:
            if a.id == id:
                return a
        raise ValueError("Attachment not found")

    def _mock_create(self, schema: dict[str, Any]) -> Attachments:
        attachment = Attachments(
            id=uuid.uuid4(),
            user_id=schema["user_id"],
            todo_id=schema.get("todo_id"),
            file_name=schema["file_name"],
            storage_key=schema["storage_key"],
            file_size=schema["file_size"],
            file_type=schema["file_type"],
            created_by=schema.get("created_by", "system"),
            updated_by=schema.get("updated_by", "system"),
        )
        self.attachments_db.append(attachment)
        return attachment

    def _mock_update(self, db_obj: Attachments, schema: dict[str, Any]) -> Attachments:
        for k, v in schema.items():
            if hasattr(db_obj, k):
                setattr(db_obj, k, v)
        return db_obj

    def _mock_update_attribute(self, db_obj: Attachments, column: str, value: Any) -> Attachments:
        if hasattr(db_obj, column):
            setattr(db_obj, column, value)
        return db_obj

    def _mock_delete(self, db_obj: Attachments) -> None:
        if db_obj in self.attachments_db:
            self.attachments_db.remove(db_obj)
