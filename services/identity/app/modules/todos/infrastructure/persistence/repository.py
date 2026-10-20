from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.todos.domain.entities import TodoRecord
from app.modules.todos.infrastructure.persistence.models import Todos
from app.shared.repository import BaseRepository


class TodoRepository(BaseRepository[Todos, BaseModel]):
    """
    Repository layer for managing Todo (Task) data.

    Handles standard CRUD operations and custom query logic for tasks.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(model=Todos, session=session)

    @staticmethod
    def _to_entity(model: Todos) -> TodoRecord:
        return TodoRecord(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            description=model.description,
            is_completed=model.is_completed,
            is_active=model.is_active,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    async def list_todos(self, filters: dict[str, Any], eager: bool | list[str] = False) -> dict[str, Any]:
        result = await self.read_by_options(filters, eager=eager)
        return {
            **result,
            "founds": [self._to_entity(item) for item in result["founds"]],
        }

    async def get_todo(self, todo_id: UUID, eager: bool | list[str] = False) -> TodoRecord:
        return self._to_entity(await self.read_by_id(todo_id, eager=eager))

    async def create_todo(self, values: dict[str, Any]) -> TodoRecord:
        return self._to_entity(await super().create(values))

    async def update_todo(self, todo_id: UUID, values: dict[str, Any]) -> TodoRecord:
        model = await self.read_by_id(todo_id)
        return self._to_entity(await super().update(model, values))

    async def update_todo_attribute(self, todo_id: UUID, attribute: str, value: int | str | bool | UUID) -> TodoRecord:
        model = await self.read_by_id(todo_id)
        return self._to_entity(await self.update_attribute(model, attribute, value))

    async def delete_todo(self, todo_id: UUID) -> None:
        await super().delete(await self.read_by_id(todo_id))
