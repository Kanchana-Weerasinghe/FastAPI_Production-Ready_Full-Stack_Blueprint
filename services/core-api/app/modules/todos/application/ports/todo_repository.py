"""Persistence contract for todo use cases."""

from typing import Any, Protocol
from uuid import UUID

from app.modules.todos.domain.entities import TodoRecord


class TodoRepositoryPort(Protocol):
    async def list_todos(self, filters: dict[str, Any], eager: bool | list[str] = False) -> dict[str, Any]: ...

    async def get_todo(self, todo_id: UUID, eager: bool | list[str] = False) -> TodoRecord: ...

    async def create_todo(self, values: dict[str, Any]) -> TodoRecord: ...

    async def update_todo(self, todo_id: UUID, values: dict[str, Any]) -> TodoRecord: ...

    async def update_todo_attribute(
        self, todo_id: UUID, attribute: str, value: int | str | bool | UUID
    ) -> TodoRecord: ...

    async def delete_todo(self, todo_id: UUID) -> None: ...
