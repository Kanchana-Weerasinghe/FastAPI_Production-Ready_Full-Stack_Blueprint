"""Public application API for attachment workflows and attachment records."""

from app.modules.attachments.application.use_cases.service import AttachmentService
from app.modules.attachments.domain.entities import AttachmentRecord

__all__ = ["AttachmentRecord", "AttachmentService"]
