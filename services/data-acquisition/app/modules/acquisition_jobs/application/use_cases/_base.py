"""Shared steps of the job use cases: load with access control, then save and publish events."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from platform_kit.auth import Principal
from platform_kit.errors import PermissionDeniedError, PreconditionFailedError

from app.modules.acquisition_jobs.application.ports import EventPublisher, JobRepository
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.exceptions import JobNotFound

Clock = Callable[[], datetime]

# Acquisition workers (crawlers, importers) report lifecycle changes with this role.
WORKER_ROLE = "acquisition_worker"


def utc_now() -> datetime:
    return datetime.now(UTC)


class JobUseCase:
    def __init__(self, repository: JobRepository, events: EventPublisher, clock: Clock = utc_now) -> None:
        self.repository = repository
        self.events = events
        self.clock = clock

    async def _load_for_owner(
        self, job_id: UUID, actor: Principal, *, expected_version: int | None = None
    ) -> AcquisitionJob:
        """Owners and admins see a job; for everyone else it does not exist (no ID probing)."""
        job = await self.repository.get(job_id)
        if not (job.is_owned_by(actor.user_id) or actor.is_admin):
            raise JobNotFound()
        if expected_version is not None and job.version != expected_version:
            raise PreconditionFailedError(
                "The job was modified by someone else; reload it and retry",
                extra={"current_etag": f'W/"{job.version}"'},
            )
        return job

    async def _load_for_worker(self, job_id: UUID, actor: Principal) -> AcquisitionJob:
        if not (actor.role == WORKER_ROLE or actor.is_admin):
            raise PermissionDeniedError("Only acquisition workers may report job progress")
        return await self.repository.get(job_id)

    async def _save(self, job: AcquisitionJob) -> AcquisitionJob:
        await self.repository.save(job)
        self.events.publish_after_commit(job.pull_events())
        return job
