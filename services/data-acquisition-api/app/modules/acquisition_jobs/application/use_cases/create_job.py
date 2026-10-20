from dataclasses import dataclass

from platform_kit.auth import Principal

from app.modules.acquisition_jobs.application.ports import EventPublisher, JobRepository
from app.modules.acquisition_jobs.application.use_cases._base import Clock, JobUseCase, utc_now
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.policies import ensure_owner_can_queue_job
from app.modules.acquisition_jobs.domain.value_objects import DataSource, JobName, MaxAttempts, SourceType


@dataclass(frozen=True, slots=True)
class CreateJobCommand:
    """Transport-neutral input: the router maps the HTTP body to this."""

    name: str
    source_type: SourceType
    source_uri: str
    max_attempts: int


class CreateJob(JobUseCase):
    """Queues a new acquisition job for the caller."""

    def __init__(
        self, repository: JobRepository, events: EventPublisher, *, active_job_limit: int, clock: Clock = utc_now
    ) -> None:
        super().__init__(repository, events, clock)
        self.active_job_limit = active_job_limit

    async def execute(self, command: CreateJobCommand, actor: Principal) -> AcquisitionJob:
        # 1. Value objects validate the input (invariants).
        name = JobName(command.name)
        source = DataSource(command.source_type, command.source_uri)
        max_attempts = MaxAttempts(command.max_attempts)
        # 2. Fetch the facts the policy needs, then apply it.
        active = await self.repository.count_active(actor.user_id)
        ensure_owner_can_queue_job(active_jobs=active, limit=self.active_job_limit)
        # 3. Create the aggregate, persist it, publish its events after commit.
        job = AcquisitionJob.create(
            owner_id=actor.user_id, name=name, source=source, max_attempts=max_attempts, at=self.clock()
        )
        await self.repository.add(job)
        self.events.publish_after_commit(job.pull_events())
        return job
