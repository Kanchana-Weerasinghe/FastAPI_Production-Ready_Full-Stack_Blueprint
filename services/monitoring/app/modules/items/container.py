"""
DEPENDENCY INJECTION: decides which class implements each port and builds the use cases.

The use cases only know the ports (`ItemRepository`, `EventPublisher`); this file plugs in the real
classes. To use another implementation, change it here only. `db` and `uow` come from the root
container (app/container.py).
"""

from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.modules.items.application.use_cases import ItemUseCases
from app.modules.items.infrastructure.logging_event_publisher import LoggingEventPublisher
from app.modules.items.infrastructure.persistence.sqlalchemy_item_repository import SqlAlchemyItemRepository


class ItemsContainer(containers.DeclarativeContainer):
    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)

    # Port -> implementation
    repository = providers.Factory(SqlAlchemyItemRepository, session=db.provided.scoped_session)
    events = providers.Factory(LoggingEventPublisher, uow=uow)

    # Used by router.py as Provide["items.use_cases"]
    use_cases = providers.Factory(ItemUseCases, repository=repository, events=events)
