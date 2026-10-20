---
name: python-testing
description: Guidelines for Python testing using pytest and pytest-asyncio. Use when writing or debugging backend tests.
---
# Python Testing Skill

## Testing Framework & Configuration

* Use `pytest` combined with `pytest-asyncio` for all testing.
* **Auto Mode**: The project is configured with `asyncio_mode = "auto"` in `services/core-api/pyproject.toml`. Because of this, any test function declared with `async def` is automatically run inside an asyncio event loop.
* **No Decorators Needed**: Do **not** use the `@pytest.mark.anyio` or `@pytest.mark.asyncio` decorators on async test functions, as `asyncio_mode = "auto"` handles this automatically.

## Directory Structure

All test files are located under `services/core-api/tests/` and are organized as follows:

* `tests/unit/`: Unit tests mirroring the app: `core/`, `shared/` and `modules/<name>/` (`test_service.py`, `test_repository.py`, ...).
* `tests/architecture/`: Module boundary and layering rules (see `docs/adr/0001-modular-monolith.md`).
* `tests/integrations/`: Contains end-to-end integration tests that call API endpoints using a test client.
* `tests/mocks/`: Contains mock classes for repositories and external integrations (e.g. `MockTodoRepository`) and `FakeUnitOfWork` (call `await fake_uow.commit()` to run after-commit side effects).
* `tests/factories.py`: Contains factory methods (like `create_user`, `create_todo`) to generate mock data.
* `tests/conftest.py`: Contains common fixtures and configuration for all tests.

## Conventions & Best Practices

* **Docstrings**: Every test function MUST have a descriptive docstring explaining exactly what it verifies.
* **Mocking**: Mock external dependencies (like database repositories or third-party HTTP clients) when writing unit tests for services. Use the classes in `tests/mocks/`.
* **Fixture Scopes**: Ensure all fixtures are explicitly scoped (e.g. `scope="session"`).
* **Code Coverage**: **Coverage must stay at or above 90%** (`fail_under` in `services/core-api/pyproject.toml`; run `uv run task cov`).
* **Test Database**: Tests run against a throwaway Postgres container (testcontainers, Docker required) started in `tests/conftest.py` before the app is imported. Never point tests at a shared database; the DB name must contain `test`.
* **Isolation**: Every integration test runs inside a transaction that is rolled back afterwards (`tests/integrations/conftest.py`). Assert against the seeded baseline from `tests/factories.py`; never rely on data created by another test.
* **Async loops**: Use the default loop scopes defined in `pyproject.toml` (`asyncio_default_fixture_loop_scope = "session"` and `asyncio_default_test_loop_scope = "session"`).
* **No need to add comments inside any of the test code. Docstrings are enough.**

## Example: Unit Test

```python
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
```

## Example: Integration Test

```python
async def test_get_todos_list_success(client: Any) -> None:
    """Integration test verifying that an authenticated user can list their seeded Todo items successfully."""
    api_client = await client("user@email.com", "SecurePass123!")
    response = await api_client.get("/v2/todos/")
    assert response.status_code == 200
    data = response.json()
    assert "founds" in data
```
