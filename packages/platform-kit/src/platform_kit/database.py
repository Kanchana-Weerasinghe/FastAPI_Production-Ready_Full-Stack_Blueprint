"""
Async database access and the unit of work.

One transaction per request (opened by `RequestContextMiddleware`) or per job (`Database.session_scope`).
Repositories and use cases never commit; side effects that must only happen after a successful
commit are registered with `UnitOfWork.after_commit`.
"""

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from platform_kit.logging import logger

AfterCommitCallback = tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]

_session_context: ContextVar[str] = ContextVar("session_context")
_after_commit: ContextVar[list[AfterCommitCallback] | None] = ContextVar("after_commit", default=None)


def _get_session_context() -> str:
    session_id = _session_context.get(None)
    if not session_id:
        session_id = str(uuid.uuid4())
        _session_context.set(session_id)
    return session_id


class Database:
    """Engine and session factory bound to the service's own schema (`search_path`)."""

    def __init__(
        self,
        *,
        url: str,
        schema: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        statement_timeout_ms: int = 0,
        echo: bool = False,
    ) -> None:
        server_settings = {"search_path": schema, "timezone": "UTC"}
        if statement_timeout_ms:
            server_settings["statement_timeout"] = str(statement_timeout_ms)
        self._engine = create_async_engine(
            url,
            echo=echo,
            connect_args={"server_settings": server_settings},
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(bind=self._engine, autoflush=False, expire_on_commit=False)
        self.scoped_session = async_scoped_session(self._session_factory, scopefunc=_get_session_context)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session_scope(self, *, run_after_commit: bool = True) -> AsyncGenerator[AsyncSession, None]:
        """Commits on success, rolls back on exception, then runs after-commit callbacks."""
        token = _session_context.set(str(uuid.uuid4()))
        callbacks: list[AfterCommitCallback] = []
        callbacks_token = _after_commit.set(callbacks)
        session = self.scoped_session()
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            callbacks.clear()
            raise
        finally:
            await self.scoped_session.remove()
            _session_context.reset(token)
            _after_commit.reset(callbacks_token)
        if run_after_commit:
            await run_callbacks(callbacks)

    async def close(self) -> None:
        await self._engine.dispose()


async def run_callbacks(callbacks: list[AfterCommitCallback]) -> None:
    """Runs after-commit callbacks; a failing callback is logged and never undoes the commit."""
    for func, args, kwargs in callbacks:
        try:
            await func(*args, **kwargs)
        except Exception as e:
            logger.exception(
                "after_commit_callback_failed", callback=getattr(func, "__qualname__", repr(func)), error=str(e)
            )


def pending_after_commit() -> list[AfterCommitCallback]:
    """Callbacks registered in the current scope (for scopes opened with `run_after_commit=False`)."""
    callbacks = _after_commit.get()
    return callbacks if callbacks is not None else []


class UnitOfWork:
    """The transaction boundary injected into use cases. It never commits; the scope owner does."""

    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db.scoped_session()

    async def flush(self) -> None:
        await self.session.flush()

    def after_commit(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        """Schedules `func(*args, **kwargs)` to run once the current transaction has committed."""
        callbacks = _after_commit.get()
        if callbacks is None:
            raise RuntimeError("after_commit() called outside of a Database.session_scope()")
        callbacks.append((func, args, kwargs))
