from dependency_injector import containers, providers

from app.core.database import Database, UnitOfWork
from app.modules.audit.service import AuditService
from app.modules.users.application.use_cases.service import UserService
from app.modules.users.infrastructure.persistence.repository import UserRepository
from app.shared.storage import FileStorage


class UsersContainer(containers.DeclarativeContainer):
    """Providers of the users module; infrastructure is injected by the root container."""

    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)
    storage: providers.Dependency[FileStorage] = providers.Dependency()
    audit_service = providers.Dependency(instance_of=AuditService)

    repository = providers.Factory(UserRepository, session=db.provided.scoped_session)
    service = providers.Factory(UserService, user_repository=repository, uow=uow, storage=storage, audit=audit_service)
