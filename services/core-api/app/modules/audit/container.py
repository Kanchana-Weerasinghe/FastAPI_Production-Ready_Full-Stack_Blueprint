from dependency_injector import containers, providers

from app.core.database import Database
from app.modules.audit.application.use_cases.service import AuditService
from app.modules.audit.infrastructure.persistence.repository import AuditLogRepository


class AuditContainer(containers.DeclarativeContainer):
    """Providers of the audit module."""

    db = providers.Dependency(instance_of=Database)

    repository = providers.Factory(AuditLogRepository, session=db.provided.scoped_session)
    service = providers.Factory(AuditService, repository=repository)
