"""How domain events leave the service. Today a logging adapter; later an outbox + message broker."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.modules.acquisition_jobs.domain.events import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        """Publishes the events only if the current transaction commits."""
