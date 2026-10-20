"""Capped offset pagination for list endpoints (camelCase JSON, like the rest of the API)."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class CamelModel(BaseModel):
    """Base for HTTP schemas: snake_case in Python, camelCase on the wire (both accepted on input)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def _page_params(
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[
        int, Query(alias="pageSize", ge=1, le=MAX_PAGE_SIZE, description=f"Items per page (max {MAX_PAGE_SIZE})")
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


# Use as a route parameter: `page: Pagination`.
Pagination = Annotated[PageParams, Depends(_page_params)]


class PageInfo(CamelModel):
    page: int
    page_size: int
    total_count: int
