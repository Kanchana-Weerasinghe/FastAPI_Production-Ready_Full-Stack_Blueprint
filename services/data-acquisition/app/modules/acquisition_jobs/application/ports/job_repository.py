"""
Port: what the use cases need from storage.

An abstract base class, so implementations declare it explicitly (`class X(JobRepository)`) and
Python refuses to create one that forgets a method. Implementations: `SqlAlchemyJobRepository`
(infrastructure) and `FakeJobRepository` (tests).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


class JobRepository(ABC):
    @abstractmethod
    async def add(self, job: AcquisitionJob) -> None: ...

    @abstractmethod
    async def get(self, job_id: UUID) -> AcquisitionJob:
        """Raises `JobNotFound` when the job does not exist."""

    @abstractmethod
    async def save(self, job: AcquisitionJob) -> None:
        """Persists a changed job; raises `ConcurrentModification` if it changed since it was loaded."""

    @abstractmethod
    async def find(self, query: JobQuery) -> JobPage: ...

    @abstractmethod
    async def count_active(self, owner_id: UUID) -> int: ...
