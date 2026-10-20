from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.config import config
from app.modules.acquisition_jobs.container import AcquisitionJobsContainer


class Container(containers.DeclarativeContainer):
    """Composition root: shared infrastructure plus one sub-container per module."""

    wiring_config = containers.WiringConfiguration(packages=["app.modules"])

    db = providers.Singleton(
        Database,
        url=config.database_url,
        schema=config.DB_SCHEMA,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
        statement_timeout_ms=config.DB_STATEMENT_TIMEOUT_MS,
    )
    uow = providers.Factory(UnitOfWork, db=db)

    acquisition_jobs = providers.Container(
        AcquisitionJobsContainer, db=db, uow=uow, active_job_limit=config.ACTIVE_JOB_LIMIT_PER_OWNER
    )
