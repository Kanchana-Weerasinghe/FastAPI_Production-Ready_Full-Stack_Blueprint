"""State changes requested by the job's owner."""

from uuid import UUID

from platform_kit.auth import Principal

from app.modules.acquisition_jobs.application.use_cases._base import JobUseCase
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob


class CancelJob(JobUseCase):
    async def execute(self, job_id: UUID, actor: Principal, *, expected_version: int | None = None) -> AcquisitionJob:
        job = await self._load_for_owner(job_id, actor, expected_version=expected_version)
        job.cancel(at=self.clock())
        return await self._save(job)


class RetryJob(JobUseCase):
    async def execute(self, job_id: UUID, actor: Principal, *, expected_version: int | None = None) -> AcquisitionJob:
        job = await self._load_for_owner(job_id, actor, expected_version=expected_version)
        job.retry()
        return await self._save(job)
