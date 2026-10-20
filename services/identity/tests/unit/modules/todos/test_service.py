import uuid

from app.modules.todos.schemas import TodoCreate, TodoUpdate
from app.modules.todos.service import TodoService
from tests.mocks.todo_repository import MockTodoRepository


async def test_add_todo_persists_record(
    todo_service: TodoService,
    mock_todo_repository: MockTodoRepository,
) -> None:
    """Test that creating a Todo task persists the Todo correctly."""
    todo_data = TodoCreate(
        title="Buy groceries",
        description="Milk and bread",
        is_completed=False,
    )
    todo = await todo_service.add(todo_data.model_dump())
    assert len(mock_todo_repository.todos_db) == 1
    assert mock_todo_repository.todos_db[0].title == "Buy groceries"
    assert mock_todo_repository.todos_db[0].id == todo.id


async def test_patch_todo_update_fields(
    todo_service: TodoService,
    mock_todo_repository: MockTodoRepository,
) -> None:
    """Test that applying a partial update to a Todo correctly updates the fields in the persisted Todo record."""
    user_id = uuid.uuid4()
    todo = mock_todo_repository._mock_create(
        {
            "user_id": user_id,
            "title": "Buy groceries",
            "description": "Old description",
        }
    )
    todo_record = await todo_service.get_by_id(todo.id)
    update_data = TodoUpdate(
        title="Buy fresh groceries",
        description="Milk, bread, and fruits",
        is_completed=None,
    )
    updated_todo = await todo_service.patch(todo_record, update_data.model_dump(exclude_none=True))
    assert updated_todo.title == "Buy fresh groceries"
    assert updated_todo.description == "Milk, bread, and fruits"


async def test_todo_service_add_and_patch_use_mappings(
    todo_service: TodoService,
) -> None:
    """Test that use cases receive transport-neutral mappings and do not mutate input data."""
    values = {"title": "Generic Find Task"}
    todo = await todo_service.add(values)
    assert todo.title == "Generic Find Task"
    updated_todo = await todo_service.patch(todo, {"title": "Updated Task"})
    assert updated_todo.title == "Updated Task"
    assert values == {"title": "Generic Find Task"}
