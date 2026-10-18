from dependency_injector import containers, providers

from app.core.database import Database
from app.modules.audit.service import AuditService
from app.modules.flags.application.use_cases.service import FeatureFlagService
from app.modules.flags.infrastructure.persistence.repository import FeatureFlagRepository


class FlagsContainer(containers.DeclarativeContainer):
    """Providers of the feature-flags module."""

    db = providers.Dependency(instance_of=Database)
    audit_service = providers.Dependency(instance_of=AuditService)

    repository = providers.Factory(FeatureFlagRepository, session=db.provided.scoped_session)
    service = providers.Factory(FeatureFlagService, repository=repository, audit=audit_service)
