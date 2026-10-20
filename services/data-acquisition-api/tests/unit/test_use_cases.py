"""Use cases orchestrate ports and domain rules; fakes replace the database and the event broker."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from platform_kit.auth import Principal
from platform_kit.errors import PermissionDeniedError, PreconditionFailedError

from app.modules.acquisition_jobs.application.use_cases import (
    WORKER_ROLE,
    CancelJob,
    CompleteJob,
    CreateJob,
    CreateJobCommand,
    FailJob,
    GetJob,
    ListJobs,
    RecordProgress,
    RetryJob,
    StartJob,
)
from app.modules.acquisition_jobs.domain.exceptions import ActiveJobLimitReached, InvalidSource, JobNotFound
from app.modules.acquisition_jobs.domain.value_objects import JobStatus, SourceType
from tests.fakes import FakeEventPublisher, FakeJobRepository

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
COMMAND = CreateJobCommand(
    name="Vendor feed", source_type=SourceType.API, source_uri="https://api.vendor.com/items", max_attempts=2
)


def _principal(role: str = "user") -> Principal:
    return Principal(user_id=uuid4(), role=role, token="t")


@pytest.fixture
def repo() -> FakeJobRepository:
    return FakeJobRepository()


@pytest.fixture
def events() -> FakeEventPublisher:
    return FakeEventPublisher()


def _create(repo: FakeJobRepository, events: FakeEventPublisher, limit: int = 10) -> CreateJob:
    return CreateJob(repo, events, active_job_limit=limit, clock=lambda: NOW)


async def test_create_job_persists_and_publishes(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    owner = _principal()
    job = await _create(repo, events).execute(COMMAND, owner)
    assert repo.jobs[job.id].owner_id == owner.user_id
    assert job.status is JobStatus.QUEUED
    assert events.names == ["AcquisitionJobQueued"]


async def test_create_job_rejects_invalid_source_before_persisting(
    repo: FakeJobRepository, events: FakeEventPublisher
) -> None:
    bad = CreateJobCommand(name="Feed", source_type=SourceType.API, source_uri="http://insecure", max_attempts=1)
    with pytest.raises(InvalidSource):
        await _create(repo, events).execute(bad, _principal())
    assert repo.jobs == {}
    assert events.published == []


async def test_create_job_enforces_active_limit(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    owner = _principal()
    use_case = _create(repo, events, limit=2)
    await use_case.execute(COMMAND, owner)
    await use_case.execute(COMMAND, owner)
    with pytest.raises(ActiveJobLimitReached):
        await use_case.execute(COMMAND, owner)
    # Another owner is not affected by this owner's jobs.
    await use_case.execute(COMMAND, _principal())


async def test_other_users_cannot_see_or_cancel_a_job(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    job = await _create(repo, events).execute(COMMAND, _principal())
    stranger = _principal()
    with pytest.raises(JobNotFound):
        await GetJob(repo, events).execute(job.id, stranger)
    with pytest.raises(JobNotFound):
        await CancelJob(repo, events).execute(job.id, stranger)


async def test_admin_can_see_any_job(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    job = await _create(repo, events).execute(COMMAND, _principal())
    assert (await GetJob(repo, events).execute(job.id, _principal("admin"))).id == job.id


async def test_only_workers_report_lifecycle(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    owner = _principal()
    job = await _create(repo, events).execute(COMMAND, owner)
    with pytest.raises(PermissionDeniedError):
        await StartJob(repo, events).execute(job.id, owner)


async def test_full_lifecycle_with_retry(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    owner, worker = _principal(), _principal(WORKER_ROLE)
    job = await _create(repo, events).execute(COMMAND, owner)

    await StartJob(repo, events, clock=lambda: NOW).execute(job.id, worker)
    await FailJob(repo, events, clock=lambda: NOW).execute(job.id, "HTTP 503 from vendor", worker)
    retried = await RetryJob(repo, events).execute(job.id, owner)
    assert retried.status is JobStatus.QUEUED

    await StartJob(repo, events, clock=lambda: NOW).execute(job.id, worker)
    await RecordProgress(repo, events).execute(job.id, 120, worker)
    done = await CompleteJob(repo, events, clock=lambda: NOW).execute(job.id, worker)

    assert done.status is JobStatus.COMPLETED
    assert done.attempts == 2
    assert done.records_collected == 120
    assert events.names == ["AcquisitionJobQueued", "AcquisitionJobFailed", "AcquisitionJobCompleted"]


async def test_stale_expected_version_is_rejected(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    owner = _principal()
    job = await _create(repo, events).execute(COMMAND, owner)
    with pytest.raises(PreconditionFailedError):
        await CancelJob(repo, events).execute(job.id, owner, expected_version=job.version + 1)
    cancelled = await CancelJob(repo, events).execute(job.id, owner, expected_version=job.version)
    assert cancelled.status is JobStatus.CANCELLED


async def test_list_jobs_is_scoped_to_owner_unless_admin(repo: FakeJobRepository, events: FakeEventPublisher) -> None:
    owner = _principal()
    create = _create(repo, events)
    await create.execute(COMMAND, owner)
    await create.execute(COMMAND, _principal())
    mine = await ListJobs(repo, events).execute(owner, status=None, offset=0, limit=10, all_owners=True)
    assert mine.total == 1  # all_owners is ignored for non-admins
    everyone = await ListJobs(repo, events).execute(
        _principal("admin"), status=None, offset=0, limit=10, all_owners=True
    )
    assert everyone.total == 2
