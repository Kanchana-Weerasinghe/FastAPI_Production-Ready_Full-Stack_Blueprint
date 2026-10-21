"""SQLAlchemy implementation of the `JobRepository` port: maps rows <-> the AcquisitionJob aggregate."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.acquisition_jobs.application.ports import JobPage, JobQuery, JobRepository
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.exceptions import ConcurrentModification, JobNotFound
from app.modules.acquisition_jobs.domain.value_objects import (
    ACTIVE_STATUSES,
    DataSource,
    JobName,
    JobStatus,
    MaxAttempts,
    SourceType,
)
from app.modules.acquisition_jobs.infrastructure.persistence.models import AcquisitionJobs


class SqlAlchemyJobRepository(JobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, job: AcquisitionJob) -> None:
        row = AcquisitionJobs(id=job.id, version=1, **self._columns(job))
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        job.version, job.created_at = row.version, row.created_at

    async def get(self, job_id: UUID) -> AcquisitionJob:
        row = await self.session.get(AcquisitionJobs, job_id, populate_existing=True)
        if row is None:
            raise JobNotFound()
        return self._to_entity(row)

    async def save(self, job: AcquisitionJob) -> None:
        # Compare-and-set on `version`: a concurrent change makes the update match zero rows.
        result = await self.session.execute(
            update(AcquisitionJobs)
            .where(AcquisitionJobs.id == job.id, AcquisitionJobs.version == job.version)
            .values(**self._columns(job), version=job.version + 1, updated_at=func.now())
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise ConcurrentModification()
        job.version += 1

    async def find(self, query: JobQuery) -> JobPage:
        conditions = []
        if query.owner_id is not None:
            conditions.append(AcquisitionJobs.owner_id == query.owner_id)
        if query.status is not None:
            conditions.append(AcquisitionJobs.status == query.status.value)
        total = await self.session.scalar(select(func.count()).select_from(AcquisitionJobs).where(*conditions))
        rows = await self.session.scalars(
            select(AcquisitionJobs)
            .where(*conditions)
            .order_by(AcquisitionJobs.created_at.desc(), AcquisitionJobs.id)
            .offset(query.offset)
            .limit(query.limit)
        )
        return JobPage(items=[self._to_entity(row) for row in rows], total=total or 0)

    async def count_active(self, owner_id: UUID) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(AcquisitionJobs)
            .where(
                AcquisitionJobs.owner_id == owner_id,
                AcquisitionJobs.status.in_([status.value for status in ACTIVE_STATUSES]),
            )
        )
        return count or 0

    @staticmethod
    def _columns(job: AcquisitionJob) -> dict[str, object]:
        return {
            "owner_id": job.owner_id,
            "name": job.name.value,
            "source_type": job.source.type.value,
            "source_uri": job.source.uri,
            "status": job.status.value,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts.value,
            "records_collected": job.records_collected,
            "error_message": job.error_message,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }

    @staticmethod
    def _to_entity(row: AcquisitionJobs) -> AcquisitionJob:
        return AcquisitionJob(
            id=row.id,
            owner_id=row.owner_id,
            name=JobName(row.name),
            source=DataSource(SourceType(row.source_type), row.source_uri),
            max_attempts=MaxAttempts(row.max_attempts),
            status=JobStatus(row.status),
            attempts=row.attempts,
            records_collected=row.records_collected,
            error_message=row.error_message,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            version=row.version,
        )
