"""In-memory implementations of the application ports, for fast use-case tests without a database."""

import copy
from collections.abc import Sequence
from uuid import UUID

from app.modules.acquisition_jobs.application.ports import EventPublisher, JobPage, JobQuery, JobRepository
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.events import DomainEvent
from app.modules.acquisition_jobs.domain.exceptions import ConcurrentModification, JobNotFound


def _stored(job: AcquisitionJob) -> AcquisitionJob:
    """Like a database row: a detached copy without unpublished domain events."""
    stored = copy.deepcopy(job)
    stored.pull_events()
    return stored


class FakeJobRepository(JobRepository):
    def __init__(self) -> None:
        self.jobs: dict[UUID, AcquisitionJob] = {}

    async def add(self, job: AcquisitionJob) -> None:
        job.version = 1
        self.jobs[job.id] = _stored(job)

    async def get(self, job_id: UUID) -> AcquisitionJob:
        if job_id not in self.jobs:
            raise JobNotFound()
        return copy.deepcopy(self.jobs[job_id])

    async def save(self, job: AcquisitionJob) -> None:
        if self.jobs[job.id].version != job.version:
            raise ConcurrentModification()
        job.version += 1
        self.jobs[job.id] = _stored(job)

    async def find(self, query: JobQuery) -> JobPage:
        items = [
            job
            for job in self.jobs.values()
            if (query.owner_id is None or job.owner_id == query.owner_id)
            and (query.status is None or job.status is query.status)
        ]
        return JobPage(items=items[query.offset : query.offset + query.limit], total=len(items))

    async def count_active(self, owner_id: UUID) -> int:
        return sum(1 for job in self.jobs.values() if job.owner_id == owner_id and job.is_active)


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)

    @property
    def names(self) -> list[str]:
        return [event.name for event in self.published]
