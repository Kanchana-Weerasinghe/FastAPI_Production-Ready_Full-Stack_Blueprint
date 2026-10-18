from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.modules.attachments.schemas import Attachment
from app.shared.schemas import BaseListResponse, PaginationMixin


class TodoBase(BaseModel):
    """Base schema for Todo items shared across Create and Update operations."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    title: str = Field(..., description="The title of the task")
    description: str | None = Field(None, description="Detailed description of the task")
    is_completed: bool = Field(False, description="Whether the task has been finished")


class TodoCreate(TodoBase):
    """Schema for creating a new Todo item."""

    attachment_ids: list[UUID] | None = Field(None, description="Optional list of attachment IDs to link to this task")


class TodoUpdate(BaseModel):
    """Schema for updating an existing Todo item. All fields are optional."""

    model_config = TodoBase.model_config
    title: str | None = Field(None, description="Updated title")
    description: str | None = Field(None, description="Updated description")
    is_completed: bool | None = Field(None, description="Updated completion status")
    attachment_ids: list[UUID] | None = Field(None, description="New list of attachment IDs to link")


class Todo(TodoBase):
    """Full Todo item schema including system-generated fields and relationships."""

    id: UUID = Field(..., description="Unique task identifier")
    user_id: UUID = Field(..., description="Owner's user identifier")
    attachments: list[Attachment] = Field([], description="List of files attached to this task")
    created_at: datetime = Field(..., description="Timestamp when the task was created")
    updated_at: datetime = Field(..., description="Timestamp when the task was last modified")
    version: int = Field(..., description="Optimistic-locking version (also sent as the ETag header)")


class FindTodo(PaginationMixin):
    """Schema for filtering and paginating tasks."""

    ORDERING_FIELDS: ClassVar[frozenset[str]] = PaginationMixin.ORDERING_FIELDS | {"title", "is_completed"}
    title__contains: str | None = Field(None, alias="title", description="Filter by partial title match")
    id__eq: UUID | None = Field(None, alias="id", description="Filter by exact task ID")
    is_active: bool | None = Field(True, alias="isActive", description="Filter by active/archived status")


class TodoListItem(BaseModel):
    """Simplified Todo schema for list views to optimize payload size."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    is_completed: bool = Field(..., description="Completion status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TodoListResponse(BaseListResponse[TodoListItem]):
    pass
