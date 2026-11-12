"""
DOMAIN EVENTS: facts that happened, which other modules or services may react to.

The ENTITY records them when something happens (`Item.create` records `ItemCreated`,
`archive` records `ItemArchived`). The USE CASE hands them to the `EventPublisher` port, which
publishes them only AFTER the database transaction commits, so nothing is announced for a change that
was rolled back. Today the publisher just logs them (infrastructure/logging_event_publisher.py).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    item_id: UUID
    occurred_at: datetime

    @property
    def name(self) -> str:
        return type(self).__name__


@dataclass(frozen=True, slots=True)
class ItemCreated(DomainEvent):
    code: str


@dataclass(frozen=True, slots=True)
class ItemArchived(DomainEvent):
    pass
