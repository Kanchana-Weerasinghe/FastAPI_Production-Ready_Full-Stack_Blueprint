"""
HTTP boundary of the acquisition-jobs module: validate input, resolve the caller, call one use case,
map the result to a response schema. No business rules here.
"""

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, Query, Response, status
from platform_kit.http.conditional import expected_version, set_etag
from platform_kit.http.pagination import PageInfo, Pagination

from app.auth import CurrentPrincipal
from app.modules.acquisition_jobs.application.use_cases import (
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
from app.modules.acquisition_jobs.domain.value_objects import JobStatus
from app.modules.acquisition_jobs.schemas import FailureReport, Job, JobCreate, JobList, ProgressReport

router = APIRouter(prefix="/acquisition-jobs", tags=["acquisition-jobs"])

IfMatch = Annotated[str | None, Header(description='ETag from GET (e.g. W/"3"); 412 if the job changed')]


def _job_response(response: Response, job: Job) -> Job:
    set_etag(response, job.version)
    return job


# --- Owner endpoints -----------------------------------------------------------------------------


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Job, summary="Create Acquisition Job")
@inject
async def create_job(
    body: JobCreate,
    actor: CurrentPrincipal,
    response: Response,
    use_case: CreateJob = Depends(Provide["acquisition_jobs.create_job"]),
) -> Job:
    job = await use_case.execute(
        CreateJobCommand(
            name=body.name, source_type=body.source_type, source_uri=body.source_uri, max_attempts=body.max_attempts
        ),
        actor,
    )
    response.headers["Location"] = f"{router.prefix}/{job.id}"
    return _job_response(response, Job.from_entity(job))


@router.get("/", response_model=JobList, summary="List Acquisition Jobs")
@inject
async def list_jobs(
    actor: CurrentPrincipal,
    page: Pagination,
    status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
    all_owners: Annotated[bool, Query(alias="allOwners", description="Admins only: include every owner")] = False,
    use_case: ListJobs = Depends(Provide["acquisition_jobs.list_jobs"]),
) -> JobList:
    result = await use_case.execute(
        actor, status=status_filter, offset=page.offset, limit=page.page_size, all_owners=all_owners
    )
    return JobList(
        items=[Job.from_entity(job) for job in result.items],
        page_info=PageInfo(page=page.page, page_size=page.page_size, total_count=result.total),
    )


@router.get("/{job_id}", response_model=Job, summary="Get Acquisition Job")
@inject
async def get_job(
    job_id: UUID,
    actor: CurrentPrincipal,
    response: Response,
    use_case: GetJob = Depends(Provide["acquisition_jobs.get_job"]),
) -> Job:
    return _job_response(response, Job.from_entity(await use_case.execute(job_id, actor)))


@router.post("/{job_id}:cancel", response_model=Job, summary="Cancel Acquisition Job")
@inject
async def cancel_job(
    job_id: UUID,
    actor: CurrentPrincipal,
    response: Response,
    if_match: IfMatch = None,
    use_case: CancelJob = Depends(Provide["acquisition_jobs.cancel_job"]),
) -> Job:
    job = await use_case.execute(job_id, actor, expected_version=expected_version(if_match))
    return _job_response(response, Job.from_entity(job))


@router.post("/{job_id}:retry", response_model=Job, summary="Retry Failed Acquisition Job")
@inject
async def retry_job(
    job_id: UUID,
    actor: CurrentPrincipal,
    response: Response,
    if_match: IfMatch = None,
    use_case: RetryJob = Depends(Provide["acquisition_jobs.retry_job"]),
) -> Job:
    job = await use_case.execute(job_id, actor, expected_version=expected_version(if_match))
    return _job_response(response, Job.from_entity(job))


# --- Worker endpoints (role: acquisition_worker) -------------------------------------------------


@router.post("/{job_id}:start", response_model=Job, summary="Start Acquisition Job (worker)")
@inject
async def start_job(
    job_id: UUID,
    actor: CurrentPrincipal,
    response: Response,
    use_case: StartJob = Depends(Provide["acquisition_jobs.start_job"]),
) -> Job:
    return _job_response(response, Job.from_entity(await use_case.execute(job_id, actor)))


@router.post("/{job_id}:progress", response_model=Job, summary="Report Acquisition Progress (worker)")
@inject
async def record_progress(
    job_id: UUID,
    body: ProgressReport,
    actor: CurrentPrincipal,
    response: Response,
    use_case: RecordProgress = Depends(Provide["acquisition_jobs.record_progress"]),
) -> Job:
    return _job_response(response, Job.from_entity(await use_case.execute(job_id, body.records, actor)))


@router.post("/{job_id}:complete", response_model=Job, summary="Complete Acquisition Job (worker)")
@inject
async def complete_job(
    job_id: UUID,
    actor: CurrentPrincipal,
    response: Response,
    use_case: CompleteJob = Depends(Provide["acquisition_jobs.complete_job"]),
) -> Job:
    return _job_response(response, Job.from_entity(await use_case.execute(job_id, actor)))


@router.post("/{job_id}:fail", response_model=Job, summary="Fail Acquisition Job (worker)")
@inject
async def fail_job(
    job_id: UUID,
    body: FailureReport,
    actor: CurrentPrincipal,
    response: Response,
    use_case: FailJob = Depends(Provide["acquisition_jobs.fail_job"]),
) -> Job:
    return _job_response(response, Job.from_entity(await use_case.execute(job_id, body.reason, actor)))
