import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import config
from app.core.logging import logger

AfterCommitCallback = tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]

_session_context: ContextVar[str] = ContextVar("session_context")
_after_commit: ContextVar[list[AfterCommitCallback] | None] = ContextVar("after_commit", default=None)
# Mutable one-element flag shared with child tasks: [True] = commit even if the request fails.
_persist_on_failure: ContextVar[list[bool] | None] = ContextVar("persist_on_failure", default=None)


def _install_slow_query_logging(engine: AsyncEngine) -> None:
    """Logs statements exceeding DB_SLOW_QUERY_MS (the query performance budget) without parameters."""
    if not config.DB_SLOW_QUERY_MS:
        return

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _start(conn: Any, _cursor: Any, _statement: str, _params: Any, _context: Any, _many: bool) -> None:
        conn.info.setdefault("query_start", []).append(time.perf_counter())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _end(conn: Any, _cursor: Any, statement: str, _params: Any, _context: Any, _many: bool) -> None:
        elapsed_ms = (time.perf_counter() - conn.info["query_start"].pop()) * 1000
        if elapsed_ms >= config.DB_SLOW_QUERY_MS:
            logger.warning("slow_query", duration_ms=round(elapsed_ms, 1), statement=statement[:1000])


def _get_session_context() -> str:
    session_id = _session_context.get(None)
    if not session_id:
        session_id = str(uuid.uuid4())
        _session_context.set(session_id)
    return session_id


class Database:
    """
    Asynchronous database manager using SQLAlchemy and asyncpg.

    Handles engine creation, session management, and transaction scopes.
    """

    def __init__(
        self, *, url: str, echo: bool = False, search_path: str, pool_size: int = 5, max_overflow: int = 10
    ) -> None:
        server_settings = {"search_path": search_path, "timezone": "UTC"}
        if config.DB_STATEMENT_TIMEOUT_MS:
            server_settings["statement_timeout"] = str(config.DB_STATEMENT_TIMEOUT_MS)
        connect_args: dict[str, Any] = {"server_settings": server_settings}
        if config.DB_PGBOUNCER:
            # PgBouncer (transaction mode) cannot keep prepared statements across transactions.
            connect_args |= {"statement_cache_size": 0, "prepared_statement_cache_size": 0}
        self._engine = create_async_engine(
            url=url,
            echo=echo,
            connect_args=connect_args,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=config.DB_POOL_TIMEOUT_SECONDS,
            pool_pre_ping=True,
            future=True,
        )
        _install_slow_query_logging(self._engine)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        self.scoped_session = async_scoped_session(
            self._session_factory,
            scopefunc=_get_session_context,
        )

    @asynccontextmanager
    async def session_scope(self, *, run_after_commit: bool = True) -> AsyncGenerator[AsyncSession, None]:
        """
        Provides a transactional scope (the unit of work) for a database session.

        Commits on success and rolls back on exception. Callbacks registered through
        `UnitOfWork.after_commit` run only after a successful commit; with
        `run_after_commit=False` they are left for the caller (`pending_after_commit`)
        so the HTTP middleware can run them after the response is sent.
        """
        session_id = str(uuid.uuid4())
        token = _session_context.set(session_id)
        callbacks: list[AfterCommitCallback] = []
        callbacks_token = _after_commit.set(callbacks)
        persist_token = _persist_on_failure.set([False])
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
            _persist_on_failure.reset(persist_token)
        if run_after_commit:
            await run_callbacks(callbacks)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def close(self) -> None:
        if self._engine:
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


class UnitOfWork:
    """
    The request/use-case transaction boundary, injected into services.

    Services and repositories never commit: the scope that opened the unit of work
    (the HTTP middleware per request, or a worker/script via `Database.session_scope`)
    commits once at the end. Side effects that must only happen if the transaction
    commits (deleting files, sending emails, publishing events) are registered with
    `after_commit` instead of being executed inline.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db.scoped_session()

    async def flush(self) -> None:
        await self.session.flush()

    def persist_on_failure(self) -> None:
        """
        Commits this unit of work even though the request ends with an error response.

        For security bookkeeping on paths that write nothing else and then fail on purpose:
        counting a failed login (which returns 401) or revoking a stolen refresh-token family.
        After-commit callbacks are still discarded on failure. Use sparingly.
        """
        flag = _persist_on_failure.get()
        if flag is None:
            raise RuntimeError("persist_on_failure() called outside of a Database.session_scope()")
        flag[0] = True

    def after_commit(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        """Schedules `func(*args, **kwargs)` to run once the current transaction has committed."""
        callbacks = _after_commit.get()
        if callbacks is None:
            raise RuntimeError("after_commit() called outside of a Database.session_scope()")
        callbacks.append((func, args, kwargs))


def persist_on_failure_requested() -> bool:
    """True when the current scope asked to be committed despite an error response."""
    flag = _persist_on_failure.get()
    return bool(flag and flag[0])


def pending_after_commit() -> list[AfterCommitCallback]:
    """Returns the callbacks registered in the current scope (for scopes opened with run_after_commit=False)."""
    callbacks = _after_commit.get()
    # Not `or []`: the shared list starts empty and must be returned by identity.
    return callbacks if callbacks is not None else []
