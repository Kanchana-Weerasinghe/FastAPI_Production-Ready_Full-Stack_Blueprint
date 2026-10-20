---
name: python
description: Enforces FastAPI, Dependency Injection, and general Python coding standards based on the repository structure.
---

# Python & FastAPI Coding & Architecture Guidelines

Use this skill when extending the Python backend, writing routes, services, or repositories, or working with core server logic.

---

## 1. FastAPI & Dependency Injection

We use `dependency-injector` for wiring application components together.

* **Wiring**: The composition root is `services/core-api/app/container.py`; each module declares its own sub-container in `app/modules/<name>/container.py`, and the root wires all of `app.modules`.
* **Dependency injection in Routes**:
  * Decorate endpoints with `@inject` (from `dependency_injector.wiring`).
  * Create clean dependency type aliases using `Annotated` and `Depends(Provide["<module>.service"])` (string paths, so modules never import the composition root).
  * **Example**:

    ```python
    TodoServiceDep = Annotated[TodoService, Depends(Provide["todos.service"])]

    @router.get("/todos/")
    @inject
    async def list_todos(service: TodoServiceDep):
        ...
    ```

* **No Direct Instantiation**: Do not manually instantiate services or repositories; resolve them via the container.

---

## 2. FastAPI Route & Handler Best Practices

### Use `Annotated`

Always prefer the `Annotated` style for parameter and dependency declarations.

```python
from typing import Annotated
from fastapi import Path, Query

@router.get("/items/{item_id}")
async def read_item(
    item_id: Annotated[UUID, Path(description="The item ID")],
    q: Annotated[str | None, Query(max_length=50)] = None,
):
    ...
```

### Return Types & `response_model`

* Specify explicit return type annotations (`-> Model`) for FastAPI validation, filtering, and serialization (running Pydantic's Rust-based serialization).
* If the returned object differs from the API response contract (e.g. returning a database model that needs filtering/serialization to a public schema), use `response_model` on the router decorator instead:

```python
@router.get("/todos/{todo_id}", response_model=Todo)
async def get_todo(todo_id: UUID) -> Any:
    ...
```

### No Ellipsis (`...`) for Required Fields

Do not use `...` as a default value for required fields or query parameters.

```python
# CORRECT
async def create_item(item: Item, project_id: Annotated[int, Query()]): ...

# INCORRECT
async def create_item(item: Item, project_id: Annotated[int, Query(...)]): ...
```

### Declaring APIRouters

Prefer defining path prefixes and tags on the router itself, rather than in `include_router()`:

```python
router = APIRouter(prefix="/todos", tags=["todos"])
```

### Async vs Sync Handlers

* Use `async def` only when calling `await`-compatible non-blocking code.
* If a route calls blocking code (like synchronous DB queries or filesystem operations), use standard `def` instead of `async def` so FastAPI runs it in an external threadpool.

### Do not use Pydantic `RootModel`

Instead, use regular type annotations with `Annotated` and validation utilities:

```python
@router.post("/items/")
async def create_items(items: Annotated[list[int], Field(min_length=1), Body()]):
    return items
```

### One HTTP Method Per Function

Keep handler functions dedicated to a single HTTP operation. Do not use `@router.api_route` for multiple methods in a single function.

---

## 3. Layered Architecture

Always structure backend logic using the established 3-layer architecture:

1. **Routes/Endpoints** (`app/routes`): Parse requests, validate inputs via Pydantic, call services, and handle HTTP routing. Keep business logic out of this layer.
2. **Services** (`app/services`): Implement business logic, orchestration, and validation checks. Inherit from `BaseService` for CRUD operations.
3. **Repositories** (`app/repositories`): Handle raw database persistence and queries using SQLAlchemy. Inherit from `BaseRepository`.

---

## 4. Database Scopes & Transactions

* **Scoped Sessions**: Uses `async_scoped_session` keyed by a unique request-based UUID context variable.
* **Transactions**:
  * Service-level or middleware-level functions run within `async with db.session_scope():` to ensure automatic rollback on failure and commit on success.
  * Always perform queries asynchronously (e.g. `await session.execute(...)`).
* **Timezones**: Use timezone-aware datetime objects (`TIMESTAMP(timezone=True)`) or Pydantic UTC validation.

---

## 5. Code Quality & Type Safety

* **Type Annotations**: Annotate all function signatures and variables. Use `Annotated`, `TypeVar`, and `Generic` for generic classes like repositories.
* **Pydantic Models**: Define explicit request/response schemas in the module's `schemas.py`.
  * Ensure they map accurately to database models.
  * Configure `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)` for camelCase serialization support.
* **Error Handling**: Raise framework-agnostic domain errors from `app/core/errors.py` (e.g. `NotFoundError`, `ConflictError`, `PermissionDeniedError`), optionally with a stable `code="..."`. Never raise `HTTPException` in services/repositories; `app/core/error_handlers.py` maps errors to RFC 9457 responses.
* **Module boundaries**: Domain code is framework/persistence independent; application use cases depend on ports; infrastructure implements ports; other modules use only public application contracts. HTTP and SQLAlchemy stay at the outer layers. Enforced by `tests/architecture/test_module_boundaries.py`.
* **New modules**: Generate a layered module with `uv run python scripts/new_module.py <plural_name>`.
* **Access control**: Protect routes with `CurrentUserDep`, `check_ownership("<module>.service", "<param>")` for resource ownership, and `dependencies=[require_permission(Permission.X)]` for role-based permissions (`app/modules/auth/permissions.py`). Never hand-roll auth checks in services.

## 6. Background Tasks

* Side effects that must only happen if the request's transaction commits (emails, file deletion, events) are registered in the service with `self.uow.after_commit(func, *args)`; never call them inline and never use FastAPI `BackgroundTasks` in services.
* Services and repositories never commit: one transaction per request is committed by `CoreMiddleware` (and rolled back on any 4xx/5xx).
