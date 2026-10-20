"""HTTP request/response shapes. They validate transport input; business rules live in the domain."""

from datetime import datetime
from uuid import UUID

from platform_kit.http.pagination import CamelModel, PageInfo
from pydantic import Field

from app.config import config
from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.value_objects import (
    JOB_NAME_MAX_LENGTH,
    MAX_ATTEMPTS_LIMIT,
    SOURCE_URI_MAX_LENGTH,
    JobStatus,
    SourceType,
)


class JobCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=JOB_NAME_MAX_LENGTH, examples=["Product catalogue crawl"])
    source_type: SourceType = Field(..., examples=[SourceType.WEB])
    source_uri: str = Field(
        ..., min_length=1, max_length=SOURCE_URI_MAX_LENGTH, examples=["https://example.org/catalogue"]
    )
    max_attempts: int = Field(config.DEFAULT_MAX_ATTEMPTS, ge=1, le=MAX_ATTEMPTS_LIMIT)


class ProgressReport(CamelModel):
    records: int = Field(..., ge=1, description="Number of new records collected since the last report")


class FailureReport(CamelModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class Job(CamelModel):
    id: UUID
    owner_id: UUID
    name: str
    source_type: SourceType
    source_uri: str
    status: JobStatus
    attempts: int
    max_attempts: int
    can_retry: bool
    records_collected: int
    error_message: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    version: int

    @classmethod
    def from_entity(cls, job: AcquisitionJob) -> "Job":
        return cls(
            id=job.id,
            owner_id=job.owner_id,
            name=job.name.value,
            source_type=job.source.type,
            source_uri=job.source.uri,
            status=job.status,
            attempts=job.attempts,
            max_attempts=job.max_attempts.value,
            can_retry=job.can_retry,
            records_collected=job.records_collected,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            version=job.version,
        )


class JobList(CamelModel):
    items: list[Job]
    page_info: PageInfo
