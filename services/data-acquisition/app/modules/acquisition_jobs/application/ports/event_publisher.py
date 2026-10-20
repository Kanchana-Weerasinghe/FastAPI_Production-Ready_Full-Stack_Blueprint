"""How domain events leave the service. Today a logging adapter; later an outbox + message broker."""

from collections.abc import Sequence
from typing import Protocol

from app.modules.acquisition_jobs.domain.events import DomainEvent


class EventPublisher(Protocol):
    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        """Publishes the events only if the current transaction commits."""
        ...
