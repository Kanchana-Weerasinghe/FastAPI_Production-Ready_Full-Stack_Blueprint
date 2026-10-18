import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from app.modules.todos.domain.entities import TodoRecord
from app.modules.todos.infrastructure.persistence.models import Todos
from app.modules.todos.schemas import FindTodo


class MockTodoRepository:
    """Mock repository for TodoRepository to test TodoService and AttachmentService in isolation."""

    def __init__(self) -> None:
        self.todos_db: list[Todos] = []
        self.read_by_options = AsyncMock(side_effect=self._mock_read_by_options)
        self.read_by_id = AsyncMock(side_effect=self._mock_read_by_id)
        self.create = AsyncMock(side_effect=self._mock_create)
        self.update = AsyncMock(side_effect=self._mock_update)
        self.update_attribute = AsyncMock(side_effect=self._mock_update_attribute)
        self.delete = AsyncMock(side_effect=self._mock_delete)
        self.list_todos = AsyncMock(side_effect=self._port_list)
        self.get_todo = AsyncMock(side_effect=self._port_get)
        self.create_todo = AsyncMock(side_effect=self._port_create)
        self.update_todo = AsyncMock(side_effect=self._port_update)
        self.update_todo_attribute = AsyncMock(side_effect=self._port_update_attribute)
        self.delete_todo = AsyncMock(side_effect=self._port_delete)

    @staticmethod
    def _to_entity(model: Todos) -> TodoRecord:
        created_at = model.created_at or datetime.now(UTC)
        return TodoRecord(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            description=model.description,
            is_completed=model.is_completed,
            is_active=model.is_active if model.is_active is not None else True,
            is_deleted=model.is_deleted if model.is_deleted is not None else False,
            created_at=created_at,
            updated_at=model.updated_at or created_at,
            version=model.version or 1,
        )

    async def _port_list(self, filters: dict[str, Any], _eager: bool = False) -> dict[str, Any]:
        result = await self.read_by_options(filters)
        return {**result, "founds": [self._to_entity(row) for row in result["founds"]]}

    async def _port_get(self, todo_id: uuid.UUID, _eager: bool = False) -> TodoRecord:
        return self._to_entity(await self.read_by_id(todo_id))

    async def _port_create(self, values: dict[str, Any]) -> TodoRecord:
        return self._to_entity(await self.create(values))

    async def _port_update(self, todo_id: uuid.UUID, values: dict[str, Any]) -> TodoRecord:
        return self._to_entity(await self.update(await self.read_by_id(todo_id), values))

    async def _port_update_attribute(self, todo_id: uuid.UUID, attribute: str, value: Any) -> TodoRecord:
        return self._to_entity(await self.update_attribute(await self.read_by_id(todo_id), attribute, value))

    async def _port_delete(self, todo_id: uuid.UUID) -> None:
        await self.delete(await self.read_by_id(todo_id))

    def _mock_read_by_options(self, schema: FindTodo | dict[str, Any], _eager: bool = False) -> dict[str, Any]:
        user_id = schema.user_id if hasattr(schema, "user_id") else schema.get("user_id")
        founds = [t for t in self.todos_db if t.user_id == user_id]
        return {"founds": founds, "total": len(founds)}

    def _mock_read_by_id(self, id: uuid.UUID, _eager: bool = False) -> Todos:
        for t in self.todos_db:
            if t.id == id:
                return t
        raise ValueError("Todo not found")

    def _mock_create(self, schema: dict[str, Any]) -> Todos:
        todo = Todos(
            id=uuid.uuid4(),
            user_id=schema.get("user_id", uuid.uuid4()),
            title=schema["title"],
            description=schema.get("description"),
            is_completed=schema.get("is_completed", False),
            is_active=schema.get("is_active", True),
            created_by=schema.get("created_by", "system"),
            updated_by=schema.get("updated_by", "system"),
        )
        self.todos_db.append(todo)
        return todo

    def _mock_update(self, db_obj: Todos, schema: dict[str, Any]) -> Todos:
        for k, v in schema.items():
            if hasattr(db_obj, k):
                setattr(db_obj, k, v)
        return db_obj

    def _mock_update_attribute(self, db_obj: Todos, column: str, value: Any) -> Todos:
        if hasattr(db_obj, column):
            setattr(db_obj, column, value)
        return db_obj

    def _mock_delete(self, db_obj: Todos) -> None:
        if db_obj in self.todos_db:
            self.todos_db.remove(db_obj)
