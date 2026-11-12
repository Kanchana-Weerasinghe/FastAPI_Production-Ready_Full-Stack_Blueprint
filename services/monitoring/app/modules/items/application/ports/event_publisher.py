"""
PORT (interface): how domain events leave the module.

Implemented by `LoggingEventPublisher` today; an outbox + message broker adapter can replace it later
(in container.py) without changing any use case.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.modules.items.domain.events import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        """Publishes the events only if the current transaction commits."""
