"""State changes reported by the acquisition worker that executes the job."""

from uuid import UUID

from platform_kit.auth import Principal

from app.modules.acquisition_jobs.application.use_cases._base import JobUseCase
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob


class StartJob(JobUseCase):
    async def execute(self, job_id: UUID, actor: Principal) -> AcquisitionJob:
        job = await self._load_for_worker(job_id, actor)
        job.start(at=self.clock())
        return await self._save(job)


class RecordProgress(JobUseCase):
    async def execute(self, job_id: UUID, records: int, actor: Principal) -> AcquisitionJob:
        job = await self._load_for_worker(job_id, actor)
        job.record_progress(records)
        return await self._save(job)


class CompleteJob(JobUseCase):
    async def execute(self, job_id: UUID, actor: Principal) -> AcquisitionJob:
        job = await self._load_for_worker(job_id, actor)
        job.complete(at=self.clock())
        return await self._save(job)


class FailJob(JobUseCase):
    async def execute(self, job_id: UUID, reason: str, actor: Principal) -> AcquisitionJob:
        job = await self._load_for_worker(job_id, actor)
        job.fail(reason, at=self.clock())
        return await self._save(job)
