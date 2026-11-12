"""
HTTP SCHEMAS (Pydantic): the JSON the API accepts and returns.

They check only the SHAPE of the JSON (types, required fields, maximum length) and use camelCase on the
wire (`createdAt`). The business rules (name length, code format, unique code, archived rules) stay in the
domain, so they hold for every caller.

    Request  (POST):  {"name": "Blue pen", "code": "itm-001"}
    Request  (PATCH): {"name": "Red pen"}                        <- send only what changes
    Response:         {"id": "...", "name": "Blue pen", "code": "ITM-001", "status": "active", ...}
"""

from datetime import datetime
from uuid import UUID

from platform_kit.http.pagination import CamelModel, PageInfo
from pydantic import Field

from app.modules.items.domain.entities import Item
from app.modules.items.domain.value_objects import CODE_MAX_LENGTH, NAME_MAX_LENGTH, ItemStatus


class ItemCreate(CamelModel):
    """Body of POST /v1/items/."""

    name: str = Field(..., min_length=1, max_length=NAME_MAX_LENGTH, examples=["Blue pen"])
    code: str = Field(..., min_length=1, max_length=CODE_MAX_LENGTH, examples=["ITM-001"])


class ItemUpdate(CamelModel):
    """Body of PATCH /v1/items/{id}: every field is optional."""

    name: str | None = Field(None, min_length=1, max_length=NAME_MAX_LENGTH, examples=["Red pen"])
    code: str | None = Field(None, min_length=1, max_length=CODE_MAX_LENGTH, examples=["ITM-002"])


class ItemResponse(CamelModel):
    """One item as the API returns it."""

    id: UUID
    name: str
    code: str
    status: ItemStatus
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, item: Item) -> "ItemResponse":
        """Entity -> JSON: the only place that decides which fields are exposed."""
        return cls(
            id=item.id,
            name=item.name.value,
            code=item.code.value,
            status=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class ItemList(CamelModel):
    """GET /v1/items/: one page plus paging info (page, pageSize, totalCount)."""

    items: list[ItemResponse]
    page_info: PageInfo
