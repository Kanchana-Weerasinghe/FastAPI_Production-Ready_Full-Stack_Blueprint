import uuid

import pytest

from app.core.errors import NotFoundError
from app.modules.todos.schemas import TodoCreate, TodoUpdate
from app.modules.todos.service import TodoService
from tests.mocks.attachment_repository import MockAttachmentRepository
from tests.mocks.todo_repository import MockTodoRepository


async def test_add_todo_without_attachments(
    todo_service: TodoService,
    mock_todo_repository: MockTodoRepository,
) -> None:
    """Test that creating a Todo task without specifying attachment IDs persists the Todo correctly."""
    todo_data = TodoCreate(
        title="Buy groceries",
        description="Milk and bread",
        is_completed=False,
        attachment_ids=None,
    )
    todo = await todo_service.add(todo_data.model_dump())
    assert len(mock_todo_repository.todos_db) == 1
    assert mock_todo_repository.todos_db[0].title == "Buy groceries"
    assert mock_todo_repository.todos_db[0].id == todo.id


async def test_add_todo_with_attachments(
    todo_service: TodoService,
    mock_todo_repository: MockTodoRepository,
    mock_attachment_repository: MockAttachmentRepository,
) -> None:
    """Test that creating a Todo task with attachment IDs links those orphaned attachment records to the new Todo ID."""
    user_id = uuid.uuid4()
    attachment = mock_attachment_repository._mock_create(
        {
            "user_id": user_id,
            "todo_id": None,
            "file_name": "receipt.pdf",
            "storage_key": f"{user_id}/receipt.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
        }
    )
    todo_data = {
        "title": "Submit expense report",
        "user_id": user_id,
        "attachment_ids": [attachment.id],
    }
    todo = await todo_service.add(todo_data)
    assert len(mock_todo_repository.todos_db) == 1
    assert todo.id is not None
    updated_attachment = mock_attachment_repository.attachments_db[0]
    assert updated_attachment.todo_id == todo.id


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
        attachment_ids=None,
    )
    updated_todo = await todo_service.patch(todo_record, update_data.model_dump(exclude_none=True))
    assert updated_todo.title == "Buy fresh groceries"
    assert updated_todo.description == "Milk, bread, and fruits"


async def test_patch_todo_with_new_attachments(
    todo_service: TodoService,
    mock_todo_repository: MockTodoRepository,
    mock_attachment_repository: MockAttachmentRepository,
) -> None:
    """Test that patching a Todo with new attachment IDs updates the todo properties and associates the attachments."""
    user_id = uuid.uuid4()
    todo = mock_todo_repository._mock_create(
        {
            "user_id": user_id,
            "title": "Buy groceries",
        }
    )
    todo_record = await todo_service.get_by_id(todo.id)
    attachment = mock_attachment_repository._mock_create(
        {
            "user_id": user_id,
            "todo_id": None,
            "file_name": "list.txt",
            "storage_key": f"{user_id}/list.txt",
            "file_size": 256,
            "file_type": "text/plain",
        }
    )
    update_data = TodoUpdate(
        title=None,
        description=None,
        is_completed=None,
        attachment_ids=[attachment.id],
    )
    await todo_service.patch(todo_record, update_data.model_dump(exclude_none=True))
    updated_attachment = mock_attachment_repository.attachments_db[0]
    assert updated_attachment.todo_id == todo.id


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


async def test_add_todo_rejects_attachment_of_another_user(
    todo_service: TodoService,
    mock_attachment_repository: MockAttachmentRepository,
) -> None:
    """Test that linking an attachment owned by a different user raises NotFoundError and leaves the attachment unlinked."""
    attachment = mock_attachment_repository._mock_create(
        {
            "user_id": uuid.uuid4(),
            "todo_id": None,
            "file_name": "secret.pdf",
            "storage_key": "other/secret.pdf",
            "file_size": 10,
            "file_type": "application/pdf",
        }
    )
    with pytest.raises(NotFoundError, match="Attachment not found"):
        await todo_service.add({"title": "Steal file", "user_id": uuid.uuid4(), "attachment_ids": [attachment.id]})
    assert attachment.todo_id is None
