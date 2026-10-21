from dependency_injector import containers, providers

from app.core.database import Database, UnitOfWork
from app.modules.audit.public import AuditService
from app.modules.users.application.use_cases.user_use_cases import UserUseCases
from app.modules.users.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.shared.storage import FileStorage


class UsersContainer(containers.DeclarativeContainer):
    """Providers of the users module; infrastructure is injected by the root container."""

    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)
    storage: providers.Dependency[FileStorage] = providers.Dependency()
    audit_service = providers.Dependency(instance_of=AuditService)

    repository = providers.Factory(SqlAlchemyUserRepository, session=db.provided.scoped_session)
    use_cases = providers.Factory(
        UserUseCases, user_repository=repository, uow=uow, storage=storage, audit=audit_service
    )
