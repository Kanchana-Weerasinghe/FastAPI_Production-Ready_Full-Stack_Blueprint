from dependency_injector import containers, providers
from redis.asyncio import Redis

from app.core.config import config
from app.core.database import Database, UnitOfWork
from app.modules.audit.container import AuditContainer
from app.modules.auth.container import AuthContainer
from app.modules.users.container import UsersContainer

# [scaffold:container-imports]
from app.shared.integrations.autosend import AutosendClient
from app.shared.integrations.email import EMAIL_SEND_EVENT, EmailDeliveryHandler, OutboxEmailSender
from app.shared.outbox import OutboxPublisher, OutboxRelay
from app.shared.storage import LocalFileStorage
from app.shared.storage_s3 import S3FileStorage
from app.shared.tasks import TaskQueue


def _redis_client() -> Redis | None:
    return Redis.from_url(config.REDIS_URL) if config.REDIS_URL else None


class Container(containers.DeclarativeContainer):
    """
    Composition root: shared infrastructure plus one sub-container per module.

    Each module declares its own providers (`app/modules/<name>/container.py`) and receives
    infrastructure and other modules' public services here, so dependencies between modules
    are explicit in one place. Routes resolve services by path, e.g. `Provide["users.use_cases"]`.
    """

    wiring_config = containers.WiringConfiguration(packages=["app.modules"])

    # --- Infrastructure -------------------------------------------------------------------------
    db = providers.Singleton(
        Database,
        url=config.SQLALCHEMY_DATABASE_URI,
        echo=config.SQLALCHEMY_ECHO,
        search_path=config.DB_SCHEMA,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
    )
    uow = providers.Factory(UnitOfWork, db=db)
    redis = providers.Singleton(_redis_client)
    task_queue = providers.Singleton(TaskQueue, redis_url=config.REDIS_URL)
    file_storage = providers.Selector(
        providers.Callable(lambda: config.STORAGE_BACKEND),
        local=providers.Singleton(LocalFileStorage),
        s3=providers.Singleton(S3FileStorage),
    )

    # --- Email: services queue mail in the outbox; the relay hands it to the transport -----------
    autosend_client = providers.Singleton(AutosendClient)
    outbox_relay = providers.Singleton(
        OutboxRelay,
        db=db,
        handlers=providers.Dict({EMAIL_SEND_EVENT: providers.Factory(EmailDeliveryHandler, transport=autosend_client)}),
    )
    outbox_publisher = providers.Factory(
        OutboxPublisher, session=db.provided.scoped_session, uow=uow, relay=outbox_relay
    )
    mailer = providers.Factory(OutboxEmailSender, publisher=outbox_publisher)

    # --- Modules --------------------------------------------------------------------------------
    audit = providers.Container(AuditContainer, db=db)
    users = providers.Container(UsersContainer, db=db, uow=uow, storage=file_storage, audit_service=audit.service)
    auth = providers.Container(
        AuthContainer, db=db, uow=uow, user_use_cases=users.use_cases, email_client=mailer, audit_service=audit.service
    )
    # [scaffold:container-providers]
