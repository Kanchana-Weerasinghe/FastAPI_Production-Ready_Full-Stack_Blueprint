"""
PORT (interface): what the use cases need from storage, without saying HOW it is stored.

The use cases only know this abstract class. Two classes implement it:
- `SqlAlchemyProductRepository` (infrastructure/persistence/): the real database, used by the app;
- `FakeProductRepository` (tests/unit/product/fakes.py): a dict in memory, used by unit tests.

To add a query: add an abstract method here, then implement it in both classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.modules.product.domain.entities import Product
from app.modules.product.domain.value_objects import ProductCode, ProductStatus


@dataclass(frozen=True, slots=True)
class ProductPage:
    """One page of a list: the product on the page and how many there are in total."""

    items: list[Product]
    total: int


class ProductRepository(ABC):
    @abstractmethod
    async def add(self, product: Product) -> None:
        """Stores a new product."""

    @abstractmethod
    async def get(self, product_id: UUID) -> Product:
        """Loads one product; raises `ProductNotFound` if the id does not exist."""

    @abstractmethod
    async def list(self, *, status: ProductStatus | None, offset: int, limit: int) -> ProductPage:
        """One page of product sorted by name, optionally only those with `status`."""

    @abstractmethod
    async def update(self, product: Product) -> None:
        """Saves the changes of an existing product."""

    @abstractmethod
    async def delete(self, product_id: UUID) -> None:
        """Deletes one product; raises `ProductNotFound` if the id does not exist."""

    @abstractmethod
    async def code_exists(self, code: ProductCode, *, except_id: UUID | None = None) -> bool:
        """True if another product (not `except_id`) already uses this code (the fact the policy needs)."""
