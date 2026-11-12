"""
ADAPTER for the `EventPublisher` port: writes each event to the structured log after commit.

`uow.after_commit(...)` makes sure nothing is published when the request fails and is rolled back.
To let other services react, replace this class with an outbox adapter in container.py.
"""

from collections.abc import Sequence
from dataclasses import asdict

from platform_kit.database import UnitOfWork

from app.core.logging import logger
from app.modules.items.application.ports import EventPublisher
from app.modules.items.domain.events import DomainEvent


class LoggingEventPublisher(EventPublisher):
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        if events:
            self.uow.after_commit(self._log, list(events))

    @staticmethod
    async def _log(events: list[DomainEvent]) -> None:
        for event in events:
            payload = {k: str(v) for k, v in asdict(event).items()}
            logger.info("domain_event_published", event_name=event.name, **payload)
