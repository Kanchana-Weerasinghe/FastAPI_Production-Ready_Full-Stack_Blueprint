import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.modules.todos.infrastructure.persistence.repository import TodoRepository
from tests.factories import create_todo, create_user


async def test_create_todo_success(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that TodoRepository successfully persists a Todo model linked to a user in the database."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    todo_data = {
        "user_id": user.id,
        "title": "Repo test todo",
        "description": "Repo test desc",
        "created_by": "system",
        "updated_by": "system",
    }
    db_todo = await todo_repository.create(todo_data)
    assert db_todo.id is not None
    assert db_todo.user_id == user.id


async def test_read_todo_by_id_success(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that TodoRepository successfully retrieves a persisted Todo by its primary key UUID."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    todo_data = create_todo(user_id=user.id, count=1)[0]
    db_session.add(todo_data)
    await db_session.flush()
    db_todo = await todo_repository.read_by_id(todo_data.id)
    assert db_todo.title == todo_data.title


async def test_read_todo_by_options(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that TodoRepository.read_by_options successfully retrieves, filters, paginates, and eager loads Todo models."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()

    todos = create_todo(user_id=user.id, count=4)
    todos[0].title = "Specific Laundry Title"
    todos[0].is_active = True
    todos[1].is_active = True
    todos[2].is_active = True
    todos[3].is_active = False
    for t in todos:
        t.created_by = user.username
        db_session.add(t)
    await db_session.flush()

    find_schema = {
        "created_by": user.username,
        "title": "Laundry",
        "page": 1,
        "page_size": 10,
        "ordering": "title",
        "is_active": True,
    }
    result = await todo_repository.read_by_options(dict(find_schema))
    assert len(result["founds"]) == 1
    assert result["founds"][0].title == "Specific Laundry Title"
    assert result["search_options"]["total_count"] == 1

    find_paginated = {
        "created_by": user.username,
        "page": 1,
        "page_size": 2,
        "ordering": "-created_at",
        "is_active": True,
    }
    result_pag = await todo_repository.read_by_options(dict(find_paginated))
    assert len(result_pag["founds"]) == 2
    assert result_pag["search_options"]["total_count"] == 3

    find_eager = {
        "created_by": user.username,
        "page": 1,
        "page_size": 10,
        "ordering": "title",
        "is_active": True,
    }
    result_eager = await todo_repository.read_by_options(dict(find_eager), eager=True)
    assert len(result_eager["founds"]) == 3
    assert result_eager["founds"][0].user is not None

    result_eager_list = await todo_repository.read_by_options(dict(find_eager), eager=["user"])
    assert len(result_eager_list["founds"]) == 3


async def test_create_todo_integrity_error(
    todo_repository: TodoRepository,
) -> None:
    """Test that TodoRepository.create maps IntegrityError to ConflictError without leaking the database error text."""
    orig_err = Exception("duplicate key value violates unique constraint")
    integrity_error = IntegrityError(statement="INSERT ...", params={}, orig=orig_err)

    with patch.object(todo_repository.session, "flush", side_effect=integrity_error):
        with pytest.raises(ConflictError) as exc_info:
            await todo_repository.create(
                {
                    "title": "Duplicate Todo",
                    "created_by": "system",
                    "updated_by": "system",
                }
            )
    assert exc_info.value.detail == "Resource already exists or violates a constraint"


async def test_read_todo_by_id_not_found(
    todo_repository: TodoRepository,
) -> None:
    """Test that TodoRepository.read_by_id raises NotFoundError when record is missing."""
    with pytest.raises(NotFoundError, match="Record not found"):
        await todo_repository.read_by_id(uuid.uuid4())


async def test_update_todo_success(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that TodoRepository.update successfully modifies a record."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    todo_data = create_todo(user_id=user.id, count=1)[0]
    db_session.add(todo_data)
    await db_session.flush()
    updated = await todo_repository.update(todo_data, {"title": "Updated Title"})
    assert updated.title == "Updated Title"


async def test_update_attribute_success(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that TodoRepository.update_attribute successfully modifies a single attribute."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    todo_data = create_todo(user_id=user.id, count=1)[0]
    db_session.add(todo_data)
    await db_session.flush()
    updated = await todo_repository.update_attribute(todo_data, "description", "New Description")
    assert updated.description == "New Description"


async def test_delete_todo_success(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that TodoRepository.delete successfully deletes a record."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    todo_data = create_todo(user_id=user.id, count=1)[0]
    db_session.add(todo_data)
    await db_session.flush()
    await todo_repository.delete(todo_data)

    with pytest.raises(NotFoundError):
        await todo_repository.read_by_id(todo_data.id)


async def test_read_by_options_page_size_all(
    todo_repository: TodoRepository,
    db_session: AsyncSession,
) -> None:
    """Test that passing page_size='all' returns all records without LIMIT/OFFSET."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    todos = create_todo(user_id=user.id, count=5, created_by=user.username, updated_by=user.username)
    for t in todos:
        db_session.add(t)
    await db_session.flush()
    result = await todo_repository.read_by_options(
        {"created_by": user.username, "page": 1, "page_size": "all", "ordering": "title", "is_active": True}
    )
    assert len(result["founds"]) == 5
    assert result["search_options"]["page_size"] == "all"
