from typing import Any
from uuid import UUID

from app.modules.attachments.service import AttachmentService
from app.modules.todos.application.ports.todo_repository import TodoRepositoryPort
from app.modules.todos.domain.entities import TodoRecord


class TodoService:
    """Todo use cases, with persistence and attachment linking behind module contracts."""

    def __init__(self, todo_repository: TodoRepositoryPort, attachment_service: AttachmentService) -> None:
        self.todo_repository = todo_repository
        self.attachment_service = attachment_service

    async def get_list(self, filters: dict[str, Any], eager: bool | list[str] = False) -> dict[str, Any]:
        return await self.todo_repository.list_todos(filters, eager)

    async def get_by_id(self, todo_id: UUID, eager: bool | list[str] = False) -> TodoRecord:
        return await self.todo_repository.get_todo(todo_id, eager)

    async def add(self, schema: dict[str, Any]) -> TodoRecord:
        """Creates the todo first, then associates previously uploaded attachments."""
        values = dict(schema)
        attachment_ids = values.pop("attachment_ids", None)
        todo = await self.todo_repository.create_todo(values)
        if attachment_ids:
            await self._link_attachments(todo, attachment_ids)
        return todo

    async def patch(self, todo: TodoRecord, schema: dict[str, Any]) -> TodoRecord:
        """Updates a todo and optionally links additional attachments."""
        values = dict(schema)
        attachment_ids = values.pop("attachment_ids", None)
        updated = await self.todo_repository.update_todo(todo.id, values)
        if attachment_ids:
            await self._link_attachments(updated, attachment_ids)
        return updated

    async def patch_attr(self, todo: TodoRecord, attribute: str, value: int | str | bool | UUID) -> TodoRecord:
        return await self.todo_repository.update_todo_attribute(todo.id, attribute, value)

    async def remove(self, todo: TodoRecord) -> None:
        await self.todo_repository.delete_todo(todo.id)

    async def _link_attachments(self, todo: TodoRecord, attachment_ids: list[UUID]) -> None:
        await self.attachment_service.link_to_todo(attachment_ids, todo.id, todo.user_id)
