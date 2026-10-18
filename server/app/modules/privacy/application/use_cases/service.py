from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.modules.attachments.service import AttachmentService
from app.modules.audit.service import AuditService
from app.modules.todos.service import TodoService
from app.modules.users.service import UserAccount

EXPORT_LIMIT = 100_000


class _AttachmentView(Protocol):
    id: UUID
    file_name: str
    file_size: int
    file_type: str
    created_at: datetime
    updated_at: datetime


class PrivacyService:
    """
    Data-subject rights (GDPR art. 15/20, CCPA "right to know"): a machine-readable export of
    everything the service stores about the user. Erasure (art. 17) is account deletion
    (`DELETE /v2/user/me`), which removes the account, its content and stored files.

    Composes other modules through their public services; when adding a module that stores personal
    data, add it to the export here (see docs/governance/data-classification.md).
    """

    def __init__(
        self, todo_service: TodoService, attachment_service: AttachmentService, audit_service: AuditService
    ) -> None:
        self.todos = todo_service
        self.attachments = attachment_service
        self.audit = audit_service

    async def export(self, user: UserAccount) -> dict[str, object]:
        owned = {"user_id__eq": user.id, "page_size": EXPORT_LIMIT, "ordering": "created_at"}
        todos = (await self.todos.get_list(dict(owned), eager=["attachments"]))["founds"]
        attachments = (await self.attachments.get_list(dict(owned)))["founds"]
        events = (
            await self.audit.get_list({"actor_id__eq": user.id, "page_size": EXPORT_LIMIT, "ordering": "created_at"})
        )["founds"]
        await self.audit.record("privacy.data_exported", actor_id=user.id, resource_type="user", resource_id=user.id)
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "email_verified": user.email_verified_at is not None,
                "mfa_enabled": user.mfa_enabled_at is not None,
            },
            "todos": [
                {
                    "id": str(todo.id),
                    "user_id": str(todo.user_id),
                    "title": todo.title,
                    "description": todo.description,
                    "is_completed": todo.is_completed,
                    "attachments": [self._attachment_data(item) for item in todo.attachments],
                    "created_at": todo.created_at.isoformat(),
                    "updated_at": todo.updated_at.isoformat(),
                    "version": todo.version,
                }
                for todo in todos
            ],
            "attachments": [self._attachment_data(attachment) for attachment in attachments],
            "security_events": [
                {
                    "at": event.created_at.isoformat(),
                    "action": event.action,
                    "outcome": event.outcome,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                }
                for event in events
            ],
        }

    @staticmethod
    def _attachment_data(attachment: _AttachmentView) -> dict[str, object]:
        return {
            "id": str(attachment.id),
            "file_name": attachment.file_name,
            "file_size": attachment.file_size,
            "file_type": attachment.file_type,
            "created_at": attachment.created_at.isoformat(),
            "updated_at": attachment.updated_at.isoformat(),
            "download_url": f"/v2/attachments/{attachment.id}:download",
        }
