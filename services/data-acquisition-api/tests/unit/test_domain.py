"""The business rules of AcquisitionJob, tested without any framework or database."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.acquisition_jobs.domain.entities import AcquisitionJob
from app.modules.acquisition_jobs.domain.exceptions import (
    ActiveJobLimitReached,
    InvalidFailureReason,
    InvalidJobName,
    InvalidMaxAttempts,
    InvalidProgress,
    InvalidSource,
    InvalidStatusTransition,
    RetryLimitReached,
)
from app.modules.acquisition_jobs.domain.policies import ensure_owner_can_queue_job
from app.modules.acquisition_jobs.domain.value_objects import DataSource, JobName, JobStatus, MaxAttempts, SourceType

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def _job(max_attempts: int = 2) -> AcquisitionJob:
    return AcquisitionJob.create(
        owner_id=uuid4(),
        name=JobName("Catalogue crawl"),
        source=DataSource(SourceType.WEB, "https://example.org/catalogue"),
        max_attempts=MaxAttempts(max_attempts),
        at=NOW,
    )


# --- Value objects (validation) ------------------------------------------------------------------


def test_job_name_is_normalized() -> None:
    assert JobName("  Catalogue    crawl ").value == "Catalogue crawl"


@pytest.mark.parametrize("name", ["", "ab", "x" * 121])
def test_job_name_length_is_enforced(name: str) -> None:
    with pytest.raises(InvalidJobName):
        JobName(name)


@pytest.mark.parametrize(
    ("source_type", "uri"),
    [
        (SourceType.WEB, "https://example.org"),
        (SourceType.WEB, "http://example.org/page"),
        (SourceType.API, "https://api.vendor.com/v1/items"),
        (SourceType.FILE, "s3://bucket/drop/"),
        (SourceType.FILE, "sftp://files.partner.com/export"),
    ],
)
def test_valid_sources(source_type: SourceType, uri: str) -> None:
    assert DataSource(source_type, uri).uri == uri


@pytest.mark.parametrize(
    ("source_type", "uri"),
    [
        (SourceType.API, "http://api.vendor.com"),  # APIs must be encrypted in transit
        (SourceType.WEB, "ftp://example.org"),
        (SourceType.FILE, "https://example.org/file.csv"),
        (SourceType.WEB, "https://"),  # no host
        (SourceType.WEB, "https://user:secret@example.org"),  # embedded credentials
        (SourceType.WEB, "   "),
    ],
)
def test_invalid_sources(source_type: SourceType, uri: str) -> None:
    with pytest.raises(InvalidSource):
        DataSource(source_type, uri)


@pytest.mark.parametrize("value", [0, 11])
def test_max_attempts_range(value: int) -> None:
    with pytest.raises(InvalidMaxAttempts):
        MaxAttempts(value)


# --- Behaviour and lifecycle ---------------------------------------------------------------------


def test_new_job_is_queued_and_records_event() -> None:
    job = _job()
    assert job.status is JobStatus.QUEUED
    assert job.attempts == 0
    assert [event.name for event in job.pull_events()] == ["AcquisitionJobQueued"]
    assert job.pull_events() == []


def test_happy_path_start_progress_complete() -> None:
    job = _job()
    job.start(at=NOW)
    job.record_progress(40)
    job.record_progress(2)
    job.complete(at=NOW)
    assert job.status is JobStatus.COMPLETED
    assert job.attempts == 1
    assert job.records_collected == 42
    assert job.is_terminal
    assert job.pull_events()[-1].name == "AcquisitionJobCompleted"


@pytest.mark.parametrize("records", [0, -5])
def test_progress_must_be_positive(records: int) -> None:
    job = _job()
    job.start(at=NOW)
    with pytest.raises(InvalidProgress):
        job.record_progress(records)


def test_cannot_complete_a_job_that_was_not_started() -> None:
    with pytest.raises(InvalidStatusTransition):
        _job().complete(at=NOW)


def test_cannot_start_twice() -> None:
    job = _job()
    job.start(at=NOW)
    with pytest.raises(InvalidStatusTransition):
        job.start(at=NOW)


def test_fail_requires_a_reason() -> None:
    job = _job()
    job.start(at=NOW)
    with pytest.raises(InvalidFailureReason):
        job.fail("   ", at=NOW)


def test_failed_job_can_be_retried_until_max_attempts() -> None:
    job = _job(max_attempts=2)
    job.start(at=NOW)
    job.record_progress(5)
    job.fail("Source timed out", at=NOW)
    assert job.can_retry
    job.retry()
    assert job.status is JobStatus.QUEUED
    assert job.records_collected == 0
    assert job.error_message is None

    job.start(at=NOW)
    job.fail("Source timed out again", at=NOW)
    assert job.attempts == 2
    assert not job.can_retry
    assert job.is_terminal
    with pytest.raises(RetryLimitReached):
        job.retry()


def test_only_failed_jobs_can_be_retried() -> None:
    with pytest.raises(InvalidStatusTransition):
        _job().retry()


@pytest.mark.parametrize("started", [False, True])
def test_active_jobs_can_be_cancelled(started: bool) -> None:
    job = _job()
    if started:
        job.start(at=NOW)
    job.cancel(at=NOW)
    assert job.status is JobStatus.CANCELLED
    assert job.finished_at == NOW


def test_finished_jobs_cannot_be_cancelled() -> None:
    job = _job()
    job.start(at=NOW)
    job.complete(at=NOW)
    with pytest.raises(InvalidStatusTransition):
        job.cancel(at=NOW)


def test_failure_reason_is_truncated() -> None:
    job = _job()
    job.start(at=NOW)
    job.fail("x" * 5000, at=NOW)
    assert job.error_message is not None
    assert len(job.error_message) == 1000


# --- Policy --------------------------------------------------------------------------------------


def test_active_job_limit_policy() -> None:
    ensure_owner_can_queue_job(active_jobs=9, limit=10)
    with pytest.raises(ActiveJobLimitReached):
        ensure_owner_can_queue_job(active_jobs=10, limit=10)
