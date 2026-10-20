"""Read use cases. They return domain records; the router maps them to response schemas."""

from uuid import UUID

from platform_kit.auth import Principal

from app.modules.acquisition_jobs.application.ports import JobPage, JobQuery
from app.modules.acquisition_jobs.application.use_cases._base import JobUseCase
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.value_objects import JobStatus


class GetJob(JobUseCase):
    async def execute(self, job_id: UUID, actor: Principal) -> AcquisitionJob:
        return await self._load_for_owner(job_id, actor)


class ListJobs(JobUseCase):
    async def execute(
        self, actor: Principal, *, status: JobStatus | None, offset: int, limit: int, all_owners: bool = False
    ) -> JobPage:
        """Callers see their own jobs; admins may ask for every owner's jobs."""
        owner_id = None if (all_owners and actor.is_admin) else actor.user_id
        return await self.repository.find(JobQuery(owner_id=owner_id, status=status, offset=offset, limit=limit))
