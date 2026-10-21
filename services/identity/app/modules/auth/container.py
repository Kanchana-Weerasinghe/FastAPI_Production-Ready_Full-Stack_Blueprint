from dependency_injector import containers, providers

from app.core.database import Database, UnitOfWork
from app.modules.audit.public import AuditService
from app.modules.auth.application.ports.email_sender import EmailSender
from app.modules.auth.application.use_cases.service import AuthService
from app.modules.auth.infrastructure.persistence.repository import OneTimeTokenRepository, RefreshTokenRepository
from app.modules.users.public import UserUseCases


class AuthContainer(containers.DeclarativeContainer):
    """Providers of the auth module; collaborators from other modules are injected by the root container."""

    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)
    user_use_cases = providers.Dependency(instance_of=UserUseCases)
    email_client: providers.Dependency[EmailSender] = providers.Dependency()
    audit_service = providers.Dependency(instance_of=AuditService)

    refresh_tokens = providers.Factory(RefreshTokenRepository, session=db.provided.scoped_session)
    one_time_tokens = providers.Factory(OneTimeTokenRepository, session=db.provided.scoped_session)
    service = providers.Factory(
        AuthService,
        user_use_cases=user_use_cases,
        refresh_tokens=refresh_tokens,
        one_time_tokens=one_time_tokens,
        email_client=email_client,
        uow=uow,
        audit=audit_service,
    )
