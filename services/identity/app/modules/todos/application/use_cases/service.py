from typing import Any
from uuid import UUID

from app.modules.todos.application.ports.todo_repository import TodoRepositoryPort
from app.modules.todos.domain.entities import TodoRecord


class TodoService:
    """Todo use cases, with persistence behind the repository port."""

    def __init__(self, todo_repository: TodoRepositoryPort) -> None:
        self.todo_repository = todo_repository

    async def get_list(self, filters: dict[str, Any], eager: bool | list[str] = False) -> dict[str, Any]:
        return await self.todo_repository.list_todos(filters, eager)

    async def get_by_id(self, todo_id: UUID, eager: bool | list[str] = False) -> TodoRecord:
        return await self.todo_repository.get_todo(todo_id, eager)

    async def add(self, schema: dict[str, Any]) -> TodoRecord:
        return await self.todo_repository.create_todo(dict(schema))

    async def patch(self, todo: TodoRecord, schema: dict[str, Any]) -> TodoRecord:
        return await self.todo_repository.update_todo(todo.id, dict(schema))

    async def patch_attr(self, todo: TodoRecord, attribute: str, value: int | str | bool | UUID) -> TodoRecord:
        return await self.todo_repository.update_todo_attribute(todo.id, attribute, value)

    async def remove(self, todo: TodoRecord) -> None:
        await self.todo_repository.delete_todo(todo.id)
