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

from app.modules.product.domain.entities import Product
from app.modules.product.domain.value_objects import CODE_MAX_LENGTH, NAME_MAX_LENGTH, ProductStatus


class ProductCreate(CamelModel):
    """Body of POST /v1/product/."""

    name: str = Field(..., min_length=1, max_length=NAME_MAX_LENGTH, examples=["Blue pen"])
    code: str = Field(..., min_length=1, max_length=CODE_MAX_LENGTH, examples=["ITM-001"])


class ProductUpdate(CamelModel):
    """Body of PATCH /v1/product/{id}: every field is optional."""

    name: str | None = Field(None, min_length=1, max_length=NAME_MAX_LENGTH, examples=["Red pen"])
    code: str | None = Field(None, min_length=1, max_length=CODE_MAX_LENGTH, examples=["ITM-002"])


class ProductResponse(CamelModel):
    """One product as the API returns it."""

    id: UUID
    name: str
    code: str
    status: ProductStatus
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, product: Product) -> "ProductResponse":
        """Entity -> JSON: the only place that decides which fields are exposed."""
        return cls(
            id=product.id,
            name=product.name.value,
            code=product.code.value,
            status=product.status,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )


class ProductList(CamelModel):
    """GET /v1/product/: one page plus paging info (page, pageSize, totalCount)."""

    items: list[ProductResponse]
    page_info: PageInfo
