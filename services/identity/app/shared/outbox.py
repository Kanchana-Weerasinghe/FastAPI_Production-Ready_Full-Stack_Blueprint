"""
Transactional outbox: reliable side effects and integration events.

Services publish events with `OutboxPublisher.publish(...)` inside the request's transaction, so an
event exists if and only if the business change committed. `OutboxRelay` delivers pending events to
registered handlers (from the ARQ worker every few seconds, or in-process right after commit when
`OUTBOX_DISPATCH_INLINE` is on). Delivery is at-least-once: failed events are retried with
exponential backoff and, after `OUTBOX_MAX_ATTEMPTS`, parked as `dead` (the dead-letter queue) for
inspection and replay. Handlers must therefore be idempotent.
"""

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import TIMESTAMP, Index, Integer, select, text
from sqlalchemy.dialects.postgresql import JSONB, TEXT, VARCHAR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import config
from app.core.database import Database, UnitOfWork
from app.core.logging import logger
from app.shared.models import BaseModel

STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_DEAD = "dead"

OutboxHandler = Callable[[dict[str, Any]], Awaitable[None]]


class OutboxEvents(BaseModel):
    """An event/side effect waiting to be delivered (or already delivered / dead-lettered)."""

    __table_args__ = (Index("ix_outbox_events_pending", "available_at", postgresql_where=text("status = 'pending'")),)

    event_type: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    available_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True)


def retry_delay(attempts: int) -> timedelta:
    """Exponential backoff for redelivery: 30s, 1m, 2m, 4m ... capped at 1h."""
    return timedelta(seconds=min(3600, 30 * 2 ** (attempts - 1)))


class OutboxRelay:
    """Delivers pending outbox events to their handlers, one transaction per batch."""

    def __init__(self, db: Database, handlers: Mapping[str, OutboxHandler]) -> None:
        self.db = db
        self.handlers = handlers

    async def run_once(self, batch_size: int | None = None) -> int:
        """Processes up to `batch_size` due events; returns how many were attempted."""
        async with self.db.session_scope() as session:
            query = (
                select(OutboxEvents)
                .where(OutboxEvents.status == STATUS_PENDING, OutboxEvents.available_at <= datetime.now(UTC))
                .order_by(OutboxEvents.created_at)
                .limit(batch_size or config.OUTBOX_BATCH_SIZE)
                # Several workers can relay concurrently without picking the same rows.
                .with_for_update(skip_locked=True)
            )
            events = list((await session.execute(query)).scalars())
            for event in events:
                await self._deliver(event)
            return len(events)

    async def dispatch(self, event_id: UUID) -> None:
        """Delivers one event right away (used for inline dispatch after commit)."""
        async with self.db.session_scope() as session:
            query = (
                select(OutboxEvents)
                .where(OutboxEvents.id == event_id, OutboxEvents.status == STATUS_PENDING)
                .with_for_update(skip_locked=True)
            )
            event = (await session.execute(query)).scalar_one_or_none()
            if event is not None:
                await self._deliver(event)

    async def _deliver(self, event: OutboxEvents) -> None:
        now = datetime.now(UTC)
        handler = self.handlers.get(event.event_type)
        try:
            if handler is None:
                raise LookupError(f"No outbox handler registered for '{event.event_type}'")
            await handler(event.payload)
        except Exception as e:
            event.attempts += 1
            event.last_error = f"{type(e).__name__}: {e}"[:2000]
            if event.attempts >= config.OUTBOX_MAX_ATTEMPTS:
                event.status = STATUS_DEAD
                logger.error(
                    "outbox_event_dead_lettered", event_id=event.id, event_type=event.event_type, error=event.last_error
                )
            else:
                event.available_at = now + retry_delay(event.attempts)
                logger.warning(
                    "outbox_event_failed", event_id=event.id, event_type=event.event_type, attempts=event.attempts
                )
            return
        event.status = STATUS_DONE
        event.processed_at = now
        logger.info("outbox_event_delivered", event_id=event.id, event_type=event.event_type)


class OutboxPublisher:
    """Writes events into the current unit of work (same transaction as the business change)."""

    def __init__(self, session: AsyncSession, uow: UnitOfWork, relay: OutboxRelay) -> None:
        self.session = session
        self.uow = uow
        self.relay = relay

    async def publish(self, event_type: str, payload: dict[str, Any], actor: str = "system") -> UUID:
        event = OutboxEvents(event_type=event_type, payload=payload, created_by=actor, updated_by=actor)
        self.session.add(event)
        await self.session.flush()
        if config.OUTBOX_DISPATCH_INLINE:
            self.uow.after_commit(self.relay.dispatch, event.id)
        return event.id
