"""Validated attachment concepts independent of HTTP and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from app.modules.attachments.domain.exceptions import AttachmentRuleViolation


@dataclass(frozen=True, slots=True)
class UploadFileName:
    """A client filename reduced to safe display metadata and a validated extension."""

    value: str
    extension: str

    @classmethod
    def create(cls, filename: str | None, allowed_extensions: set[str]) -> UploadFileName:
        """Reject missing or unsupported filenames before storage receives the upload."""
        if not filename:
            raise AttachmentRuleViolation("file_name_missing", "File name is missing")

        safe_name = PurePath(filename.replace("\\", "/")).name
        extension = PurePath(safe_name).suffix.lower()
        if extension not in allowed_extensions:
            raise AttachmentRuleViolation("file_type_not_allowed", "File type not allowed")
        return cls(value=safe_name, extension=extension)
