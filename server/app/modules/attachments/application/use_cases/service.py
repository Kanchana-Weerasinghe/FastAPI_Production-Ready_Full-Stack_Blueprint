import mimetypes
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

from app.core.config import config
from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.modules.attachments.application.ports.attachment_repository import AttachmentRepositoryPort
from app.modules.attachments.domain.entities import AttachmentRecord
from app.modules.attachments.domain.exceptions import AttachmentRuleViolation
from app.modules.attachments.domain.value_objects import UploadFileName
from app.shared.actor import Actor
from app.shared.storage import FileStorage
from app.shared.unit_of_work import UnitOfWork


class AttachmentService:
    """
    Public API of the attachments module: uploads, private file storage and linking to todos.

    Framework-agnostic: it receives a plain binary stream, not an HTTP upload object.
    """

    def __init__(self, attachment_repository: AttachmentRepositoryPort, storage: FileStorage, uow: UnitOfWork):
        self._attachments = attachment_repository
        self.storage = storage
        self.uow = uow

    async def add_attachment(
        self,
        source: BinaryIO,
        filename: str | None,
        content_type: str | None,
        owner: Actor,
        todo_id: UUID | None = None,
    ) -> AttachmentRecord:
        """Streams a file into private storage and creates an attachment record in the database."""
        logger.info("attachment_upload_initiated", todo_id=todo_id)
        try:
            upload_name = UploadFileName.create(filename, set(config.ALLOWED_FILE_EXTENSIONS))
        except AttachmentRuleViolation as error:
            logger.warning("attachment_add_failed_domain_validation", code=error.code)
            raise BadRequestError(detail=str(error), code=error.code) from error
        file_name = upload_name.value
        file_ext = upload_name.extension
        storage_key, file_size = await self.storage.save(source, owner.id, file_ext, config.MAX_UPLOAD_SIZE_BYTES)
        logger.info("attachment_file_saved", storage_key=storage_key, user_id=owner.id)
        attachment_data = {
            "todo_id": todo_id,
            "user_id": owner.id,
            "file_name": file_name,
            "storage_key": storage_key,
            "file_size": file_size,
            # Derived from the extension rather than trusting the client-declared Content-Type.
            "file_type": mimetypes.guess_type(file_name)[0] or content_type or "application/octet-stream",
            "created_by": owner.username,
            "updated_by": owner.username,
        }
        try:
            return await self._attachments.create_attachment(attachment_data)
        except BaseException:
            await self.storage.delete(storage_key)
            raise

    async def remove(self, db_obj: AttachmentRecord) -> None:
        """Deletes the record now and the stored file after commit (a rollback keeps both)."""
        await self._attachments.delete_attachment(db_obj.id)
        self.uow.after_commit(self.storage.delete, db_obj.storage_key)

    async def get_list(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await self._attachments.list_attachments(filters)

    async def get_by_id(self, attachment_id: UUID) -> AttachmentRecord:
        return await self._attachments.get_attachment(attachment_id)

    async def link_to_todo(self, attachment_ids: list[UUID], todo_id: UUID, owner_id: UUID) -> None:
        """
        Links pre-uploaded attachments to a todo, but only those owned by `owner_id`.

        Attachments of other users are reported as not found (rather than forbidden) so that
        attachment IDs belonging to someone else cannot be probed.
        """
        for attachment_id in attachment_ids:
            attachment = await self._attachments.get_attachment(attachment_id)
            if attachment.user_id != owner_id:
                logger.warning("attachment_link_denied_not_owner", attachment_id=attachment_id, todo_id=todo_id)
                raise NotFoundError(detail="Attachment not found", code="attachment_not_found")
            await self._attachments.link_to_todo(attachment_id, todo_id)

    async def resolve_download(self, db_obj: AttachmentRecord) -> Path | str:
        """
        Where to fetch the file from: a short-lived pre-signed URL (object storage) or a local path
        to stream. Raises 404 when the stored file is missing.
        """
        url = await self.storage.download_url(db_obj.storage_key, db_obj.file_name, db_obj.file_type)
        if url is not None:
            return url
        return await self.get_file_path(db_obj)

    async def get_file_path(self, db_obj: AttachmentRecord) -> Path:
        """Resolves the locally stored file of an attachment, raising 404 when it is missing on disk."""
        if not await self.storage.exists(db_obj.storage_key):
            raise NotFoundError(detail="File not found on disk", code="file_missing")
        return self.storage.path(db_obj.storage_key)
