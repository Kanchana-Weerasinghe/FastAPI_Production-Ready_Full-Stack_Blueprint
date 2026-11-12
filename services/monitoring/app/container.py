from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.core.config import config
from app.modules.items.container import ItemsContainer


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

    items = providers.Container(ItemsContainer, db=db, uow=uow)
