"""Application-facing transaction-boundary contract."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol


class UnitOfWork(Protocol):
    """Operations application workflows may use without depending on database infrastructure."""

    async def flush(self) -> None: ...

    def persist_on_failure(self) -> None: ...

    def after_commit(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None: ...
