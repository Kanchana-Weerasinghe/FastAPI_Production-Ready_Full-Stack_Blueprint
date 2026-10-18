from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.core.config import config

T = TypeVar("T")


class PaginationMixin(BaseModel):
    """Reusable mixin for handling pagination and ordering in query parameters."""

    # Subclasses extend this allow-list; sorting is only permitted on these (indexed, non-sensitive) columns.
    ORDERING_FIELDS: ClassVar[frozenset[str]] = frozenset({"created_at", "updated_at"})

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    page: int | None = Field(1, description="The page number to retrieve", ge=1)
    page_size: int | None = Field(
        config.PAGE_SIZE,
        alias="pageSize",
        description=f"Number of items per page (max {config.MAX_PAGE_SIZE})",
        ge=1,
        le=config.MAX_PAGE_SIZE,
    )
    ordering: str | None = Field("-created_at", description="Field to sort by. Prefix with '-' for descending order")

    @field_validator("ordering")
    @classmethod
    def validate_ordering(cls, value: str | None) -> str | None:
        if value is not None and value.removeprefix("-") not in cls.ORDERING_FIELDS:
            allowed = ", ".join(sorted(cls.ORDERING_FIELDS))
            raise ValueError(f"Ordering must be one of: {allowed} (prefix with '-' for descending)")
        return value


class CursorParams(BaseModel):
    """Query parameters for keyset (cursor) pagination."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    cursor: str | None = Field(None, description="Opaque cursor from the previous page's `nextCursor`")
    limit: int = Field(config.PAGE_SIZE, ge=1, le=config.MAX_PAGE_SIZE, description="Items per page")


class CursorPage(BaseModel, Generic[T]):
    """A page of a cursor-paginated list. `next_cursor` is null on the last page."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    items: list[T]
    next_cursor: str | None


class SearchOptions(BaseModel):
    """Metadata describing the pagination state of a list response."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    ordering: str = Field(..., description="Active sort order")
    total_count: int = Field(..., description="Total number of items matching the query")


class BaseListResponse(BaseModel, Generic[T]):
    """Standard wrapper for paginated list results."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    founds: list[T] = Field(..., description="The list of retrieved items")
    search_options: SearchOptions = Field(..., description="Pagination metadata")
