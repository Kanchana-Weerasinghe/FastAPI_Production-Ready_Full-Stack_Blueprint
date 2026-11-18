"""
DEPENDENCY INJECTION: decides which class implements each port and builds the use cases.

The use cases only know the ports (`ProductRepository`, `EventPublisher`); this file plugs in the real
classes. To use another implementation, change it here only. `db` and `uow` come from the root
container (app/container.py).
"""

from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.modules.product.application.use_cases import ProductUseCases
from app.modules.product.infrastructure.logging_event_publisher import LoggingEventPublisher
from app.modules.product.infrastructure.persistence.sqlalchemy_product_repository import SqlAlchemyProductRepository


class ProductContainer(containers.DeclarativeContainer):
    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)

    # Port -> implementation
    repository = providers.Factory(SqlAlchemyProductRepository, session=db.provided.scoped_session)
    events = providers.Factory(LoggingEventPublisher, uow=uow)

    # Used by router.py as Provide["product.use_cases"]
    use_cases = providers.Factory(ProductUseCases, repository=repository, events=events)
