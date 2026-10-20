from typing import Any

import pytest
from sqlalchemy import select

from app.core.config import config
from app.main import db
from app.shared.outbox import STATUS_DEAD, STATUS_DONE, STATUS_PENDING, OutboxEvents, OutboxRelay


async def _add_event(event_type: str) -> Any:
    async with db.session_scope() as session:
        event = OutboxEvents(event_type=event_type, payload={"n": 1}, created_by="test", updated_by="test")
        session.add(event)
        await session.flush()
        return event.id


async def _get(event_id: Any) -> OutboxEvents:
    async with db.session_scope() as session:
        return (await session.execute(select(OutboxEvents).where(OutboxEvents.id == event_id))).scalar_one()


async def test_relay_delivers_and_marks_done() -> None:
    """Test that the relay hands due events to their handler and marks them done."""
    received: list[dict[str, Any]] = []

    async def handler(payload: dict[str, Any]) -> None:
        received.append(payload)

    event_id = await _add_event("test.ok")
    await OutboxRelay(db, {"test.ok": handler}).dispatch(event_id)
    assert received == [{"n": 1}]
    assert (await _get(event_id)).status == STATUS_DONE


async def test_relay_retries_with_backoff_then_dead_letters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that failing events are rescheduled with backoff and parked as dead after OUTBOX_MAX_ATTEMPTS."""
    monkeypatch.setattr(config, "OUTBOX_MAX_ATTEMPTS", 2)

    async def failing(_payload: dict[str, Any]) -> None:
        raise RuntimeError("provider down")

    relay = OutboxRelay(db, {"test.fail": failing})
    event_id = await _add_event("test.fail")

    await relay.dispatch(event_id)
    event = await _get(event_id)
    assert event.status == STATUS_PENDING
    assert event.attempts == 1
    assert event.available_at > event.created_at
    assert "provider down" in (event.last_error or "")

    await relay.dispatch(event_id)
    assert (await _get(event_id)).status == STATUS_DEAD
