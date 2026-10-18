from dependency_injector import containers, providers

from app.modules.attachments.service import AttachmentService
from app.modules.audit.service import AuditService
from app.modules.privacy.application.use_cases.service import PrivacyService
from app.modules.todos.service import TodoService


class PrivacyContainer(containers.DeclarativeContainer):
    """Providers of the privacy module (composes other modules' public services)."""

    todo_service = providers.Dependency(instance_of=TodoService)
    attachment_service = providers.Dependency(instance_of=AttachmentService)
    audit_service = providers.Dependency(instance_of=AuditService)

    service = providers.Factory(
        PrivacyService, todo_service=todo_service, attachment_service=attachment_service, audit_service=audit_service
    )
