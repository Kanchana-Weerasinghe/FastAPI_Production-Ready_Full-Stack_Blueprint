from dependency_injector import containers, providers

from app.core.database import Database
from app.modules.attachments.service import AttachmentService
from app.modules.todos.application.use_cases.service import TodoService
from app.modules.todos.infrastructure.persistence.repository import TodoRepository


class TodosContainer(containers.DeclarativeContainer):
    """Providers of the todos module; collaborators from other modules are injected by the root container."""

    db = providers.Dependency(instance_of=Database)
    attachment_service = providers.Dependency(instance_of=AttachmentService)

    repository = providers.Factory(TodoRepository, session=db.provided.scoped_session)
    service = providers.Factory(TodoService, todo_repository=repository, attachment_service=attachment_service)
