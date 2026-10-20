"""
The AcquisitionJob aggregate: a request to collect data from one source.

Lifecycle:

    QUEUED --start--> RUNNING --complete--> COMPLETED
       |                 |
       |                 +--fail--> FAILED --retry--> QUEUED   (while attempts < max_attempts)
       |                 |
       +-----cancel------+--cancel--> CANCELLED

State only changes through methods, so every rule below is enforced no matter which use case,
worker or API version triggers the change. Plain Python: no FastAPI, Pydantic or SQLAlchemy.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.modules.acquisition_jobs.domain.events import (
    AcquisitionJobCancelled,
    AcquisitionJobCompleted,
    AcquisitionJobFailed,
    AcquisitionJobQueued,
    DomainEvent,
)
from app.modules.acquisition_jobs.domain.exceptions import (
    InvalidFailureReason,
    InvalidProgress,
    InvalidStatusTransition,
    RetryLimitReached,
)
from app.modules.acquisition_jobs.domain.value_objects import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    DataSource,
    JobName,
    JobStatus,
    MaxAttempts,
)

FAILURE_REASON_MAX_LENGTH = 1000


@dataclass(slots=True)
class AcquisitionJob:
    # --- Properties ---
    id: UUID
    owner_id: UUID  # the user who requested it (an ID from core-api; never a foreign key)
    name: JobName
    source: DataSource
    max_attempts: MaxAttempts
    status: JobStatus
    attempts: int = 0
    records_collected: int = 0
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    version: int = 0  # optimistic-locking version; 0 = not persisted yet
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    # --- Creation ---
    @classmethod
    def create(
        cls, *, owner_id: UUID, name: JobName, source: DataSource, max_attempts: MaxAttempts, at: datetime
    ) -> "AcquisitionJob":
        job = cls(
            id=uuid4(),
            owner_id=owner_id,
            name=name,
            source=source,
            max_attempts=max_attempts,
            status=JobStatus.QUEUED,
            created_at=at,
        )
        job._record(AcquisitionJobQueued(job.id, at, owner_id=owner_id, source_type=source.type.value))
        return job

    # --- Behaviours ---
    def start(self, *, at: datetime) -> None:
        self._require_status(JobStatus.QUEUED, action="start")
        self.status = JobStatus.RUNNING
        self.attempts += 1
        self.started_at = at
        self.finished_at = None

    def record_progress(self, records: int) -> None:
        self._require_status(JobStatus.RUNNING, action="record progress for")
        if records <= 0:
            raise InvalidProgress("Progress must report at least one new record")
        self.records_collected += records

    def complete(self, *, at: datetime) -> None:
        self._require_status(JobStatus.RUNNING, action="complete")
        self.status = JobStatus.COMPLETED
        self.finished_at = at
        self._record(AcquisitionJobCompleted(self.id, at, records_collected=self.records_collected))

    def fail(self, reason: str, *, at: datetime) -> None:
        self._require_status(JobStatus.RUNNING, action="fail")
        cleaned = reason.strip()
        if not cleaned:
            raise InvalidFailureReason("A failure reason is required")
        self.status = JobStatus.FAILED
        self.error_message = cleaned[:FAILURE_REASON_MAX_LENGTH]
        self.finished_at = at
        self._record(
            AcquisitionJobFailed(
                self.id, at, attempt=self.attempts, reason=self.error_message, can_retry=self.can_retry
            )
        )

    def retry(self) -> None:
        self._require_status(JobStatus.FAILED, action="retry")
        if not self.can_retry:
            raise RetryLimitReached(f"The job already used all {self.max_attempts.value} attempts")
        self.status = JobStatus.QUEUED
        self.error_message = None
        self.records_collected = 0  # a new attempt collects from scratch

    def cancel(self, *, at: datetime) -> None:
        if self.status not in ACTIVE_STATUSES:
            raise InvalidStatusTransition(f"Cannot cancel a {self.status.value} job")
        self.status = JobStatus.CANCELLED
        self.finished_at = at
        self._record(AcquisitionJobCancelled(self.id, at))

    # --- Business questions ---
    @property
    def can_retry(self) -> bool:
        return self.status is JobStatus.FAILED and self.attempts < self.max_attempts.value

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES or (self.status is JobStatus.FAILED and not self.can_retry)

    def is_owned_by(self, user_id: UUID) -> bool:
        return self.owner_id == user_id

    # --- Domain events ---
    def pull_events(self) -> list[DomainEvent]:
        """Returns and clears the events recorded since the last call."""
        events, self._events = self._events, []
        return events

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def _require_status(self, expected: JobStatus, *, action: str) -> None:
        if self.status is not expected:
            raise InvalidStatusTransition(f"Cannot {action} a {self.status.value} job")
