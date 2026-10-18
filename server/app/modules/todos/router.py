from typing import Annotated, Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.conditional import check_if_match, set_etag
from app.core.security import rate_limit
from app.modules.auth.dependencies import CurrentUserDep, check_ownership
from app.modules.todos.domain.entities import TodoRecord
from app.modules.todos.schemas import FindTodo, Todo, TodoCreate, TodoListResponse, TodoUpdate
from app.modules.todos.service import TodoService

router = APIRouter(tags=["todos"])

TodoServiceDep = Annotated[TodoService, Depends(Provide["todos.service"])]


@router.get("/todos/", response_model=TodoListResponse, summary="List Todos", dependencies=[rate_limit("100/minute")])
@inject
async def get_todo_list(
    find_query: Annotated[FindTodo, Query()],
    service: TodoServiceDep,
    current_user: CurrentUserDep,
) -> Any:
    """Retrieves a paginated list of todos for the current user."""
    find_query_dict = find_query.model_dump(exclude_none=True)
    find_query_dict["user_id__eq"] = current_user.id
    return await service.get_list(find_query_dict)


@router.post(
    "/todos/",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    summary="Create Todo",
    dependencies=[rate_limit("30/minute")],
)
@inject
async def create_todo(
    todo_in: TodoCreate,
    service: TodoServiceDep,
    current_user: CurrentUserDep,
) -> None:
    """Creates a new todo item and links it to the authenticated user."""
    todo_data = todo_in.model_dump()
    todo_data["user_id"] = current_user.id
    todo_data["created_by"] = current_user.username
    todo_data["updated_by"] = current_user.username
    await service.add(todo_data)


@router.post(
    "/todos/{_todo_id}:archive",
    response_model=None,
    summary="Toggle Archive Status",
    dependencies=[rate_limit("40/minute")],
)
@inject
async def toggle_archive_todo(
    _todo_id: UUID,
    service: TodoServiceDep,
    todo: Annotated[TodoRecord, Depends(check_ownership("todos.service", "_todo_id", is_active=None))],
) -> None:
    """Toggles the 'is_active' status of a specific todo."""
    await service.patch_attr(todo, "is_active", not todo.is_active)


@router.get("/todos/{todo_id}", response_model=Todo, summary="Get Todo", dependencies=[rate_limit("120/minute")])
@inject
async def get_todo(
    todo_id: UUID,
    response: Response,
    service: TodoServiceDep,
    _todo: Annotated[TodoRecord, Depends(check_ownership("todos.service", "todo_id"))],
) -> TodoRecord:
    """Retrieves a todo with its attachments. The `ETag` header carries its version for `If-Match`."""
    todo = await service.get_by_id(todo_id, eager=["attachments"])
    set_etag(response, todo.version)
    return todo


@router.patch("/todos/{_todo_id}", response_model=None, summary="Update Todo", dependencies=[rate_limit("40/minute")])
@inject
async def update_todo(
    _todo_id: UUID,
    todo_in: TodoUpdate,
    service: TodoServiceDep,
    todo: Annotated[TodoRecord, Depends(check_ownership("todos.service", "_todo_id"))],
    current_user: CurrentUserDep,
    response: Response,
    if_match: Annotated[str | None, Header(description='ETag from GET (e.g. W/"3"); 412 if the todo changed')] = None,
) -> None:
    """Updates a todo. Send `If-Match` with the ETag from GET to avoid overwriting concurrent changes."""
    check_if_match(if_match, todo.version)
    todo_data = todo_in.model_dump(exclude_none=True)
    todo_data["updated_by"] = current_user.username
    updated = await service.patch(todo, todo_data)
    set_etag(response, updated.version)


@router.delete(
    "/todos/{_todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Todo",
    dependencies=[rate_limit("20/minute")],
)
@inject
async def delete_todo(
    _todo_id: UUID,
    service: TodoServiceDep,
    todo: Annotated[TodoRecord, Depends(check_ownership("todos.service", "_todo_id", is_active=False))],
) -> None:
    """Permanently removes a todo item from the system."""
    await service.remove(todo)
