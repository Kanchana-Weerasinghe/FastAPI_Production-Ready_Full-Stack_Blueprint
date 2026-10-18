from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.alias_generators import to_camel

from app.shared.schemas import BaseListResponse, PaginationMixin


class AttachmentBase(BaseModel):
    """Base schema for attachment data containing file metadata."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    file_name: str = Field(..., description="Original name of the uploaded file")
    file_size: int = Field(..., description="Size of the file in bytes")
    file_type: str = Field(..., description="MIME type of the file")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")


class Attachment(AttachmentBase):
    """Full attachment schema including the unique identifier."""

    id: UUID = Field(..., description="Unique attachment identifier")

    @computed_field(alias="downloadUrl", description="Authenticated, ownership-checked download path")  # type: ignore[prop-decorator]
    @property
    def download_url(self) -> str:
        return f"/v2/attachments/{self.id}:download"


class FindAttachment(PaginationMixin):
    """Schema for filtering and paginating attachments."""

    ORDERING_FIELDS: ClassVar[frozenset[str]] = PaginationMixin.ORDERING_FIELDS | {"file_name", "file_size"}
    file_name__contains: str | None = Field(None, alias="fileName", description="Filter by partial file name match")


class AttachmentListResponse(BaseListResponse[Attachment]):
    pass
