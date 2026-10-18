from collections.abc import Awaitable, Callable
from typing import Any


class FakeUnitOfWork:
    """In-memory stand-in for UnitOfWork: records after-commit callbacks so tests can assert or run them."""

    def __init__(self) -> None:
        self.callbacks: list[tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]] = []

    def after_commit(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        self.callbacks.append((func, args, kwargs))

    def persist_on_failure(self) -> None:
        self.persisted_on_failure = True

    async def commit(self) -> None:
        """Simulates a successful commit by running and clearing the registered callbacks."""
        callbacks, self.callbacks = self.callbacks, []
        for func, args, kwargs in callbacks:
            await func(*args, **kwargs)
