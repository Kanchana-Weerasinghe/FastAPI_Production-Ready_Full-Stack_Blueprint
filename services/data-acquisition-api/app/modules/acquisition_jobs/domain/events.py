"""
Domain events: facts other domains may react to.

The entity records them; the use case hands them to the `EventPublisher` port after a successful
commit. Event names and fields are part of this service's public contract, like its API.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    job_id: UUID
    occurred_at: datetime

    @property
    def name(self) -> str:
        return type(self).__name__


@dataclass(frozen=True, slots=True)
class AcquisitionJobQueued(DomainEvent):
    owner_id: UUID
    source_type: str


@dataclass(frozen=True, slots=True)
class AcquisitionJobCompleted(DomainEvent):
    records_collected: int


@dataclass(frozen=True, slots=True)
class AcquisitionJobFailed(DomainEvent):
    attempt: int
    reason: str
    can_retry: bool


@dataclass(frozen=True, slots=True)
class AcquisitionJobCancelled(DomainEvent):
    pass
