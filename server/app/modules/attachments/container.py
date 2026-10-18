from dependency_injector import containers, providers

from app.core.database import Database, UnitOfWork
from app.modules.attachments.application.use_cases.service import AttachmentService
from app.modules.attachments.infrastructure.persistence.repository import AttachmentRepository
from app.shared.storage import FileStorage


class AttachmentsContainer(containers.DeclarativeContainer):
    """Providers of the attachments module; infrastructure is injected by the root container."""

    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)
    storage: providers.Dependency[FileStorage] = providers.Dependency()

    repository = providers.Factory(AttachmentRepository, session=db.provided.scoped_session)
    service = providers.Factory(AttachmentService, attachment_repository=repository, storage=storage, uow=uow)
