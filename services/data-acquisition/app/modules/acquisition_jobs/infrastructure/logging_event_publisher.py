"""
`EventPublisher` adapter that writes events to the structured log after commit.

It keeps the service self-contained until a message broker exists. To let other domains consume the
events, replace it with an outbox adapter (store events in the same transaction, relay them to the
broker) and wire it in `container.py`; the use cases do not change.
"""

from collections.abc import Sequence
from dataclasses import asdict

from platform_kit.database import UnitOfWork
from platform_kit.logging import logger

from app.modules.acquisition_jobs.application.ports import EventPublisher
from app.modules.acquisition_jobs.domain.events import DomainEvent


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
