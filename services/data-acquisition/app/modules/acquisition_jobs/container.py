from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.modules.acquisition_jobs.application.use_cases import (
    CancelJob,
    CompleteJob,
    CreateJob,
    FailJob,
    GetJob,
    ListJobs,
    RecordProgress,
    RetryJob,
    StartJob,
)
from app.modules.acquisition_jobs.infrastructure.events import LoggingEventPublisher
from app.modules.acquisition_jobs.infrastructure.persistence.repository import SqlAlchemyJobRepository


class AcquisitionJobsContainer(containers.DeclarativeContainer):
    """Adapters are bound to ports here; use cases never construct their own dependencies."""

    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)
    active_job_limit = providers.Dependency(instance_of=int)

    repository = providers.Factory(SqlAlchemyJobRepository, session=db.provided.scoped_session)
    events = providers.Factory(LoggingEventPublisher, uow=uow)

    create_job = providers.Factory(CreateJob, repository=repository, events=events, active_job_limit=active_job_limit)
    get_job = providers.Factory(GetJob, repository=repository, events=events)
    list_jobs = providers.Factory(ListJobs, repository=repository, events=events)
    cancel_job = providers.Factory(CancelJob, repository=repository, events=events)
    retry_job = providers.Factory(RetryJob, repository=repository, events=events)
    start_job = providers.Factory(StartJob, repository=repository, events=events)
    record_progress = providers.Factory(RecordProgress, repository=repository, events=events)
    complete_job = providers.Factory(CompleteJob, repository=repository, events=events)
    fail_job = providers.Factory(FailJob, repository=repository, events=events)
