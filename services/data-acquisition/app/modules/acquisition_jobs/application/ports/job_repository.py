"""What the use cases need from storage. The SQLAlchemy adapter implements it; tests use a fake."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.value_objects import JobStatus


@dataclass(frozen=True, slots=True)
class JobQuery:
    owner_id: UUID | None  # None = all owners (admins only)
    status: JobStatus | None
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class JobPage:
    items: list[AcquisitionJob]
    total: int


class JobRepository(Protocol):
    async def add(self, job: AcquisitionJob) -> None: ...

    async def get(self, job_id: UUID) -> AcquisitionJob:
        """Raises `JobNotFound` when the job does not exist."""
        ...

    async def save(self, job: AcquisitionJob) -> None:
        """Persists a changed job; raises `ConcurrentModification` if it changed since it was loaded."""
        ...

    async def find(self, query: JobQuery) -> JobPage: ...

    async def count_active(self, owner_id: UUID) -> int: ...
