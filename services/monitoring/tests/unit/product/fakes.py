"""
TEST DOUBLES: in-memory versions of the ports, so use-case tests run without a database or a broker.
They implement the same interfaces as the real adapters.
"""

from collections.abc import Sequence
from copy import deepcopy
from uuid import UUID

from app.modules.product.application.ports import EventPublisher, ProductPage, ProductRepository
from app.modules.product.domain.entities import Product
from app.modules.product.domain.events import DomainEvent
from app.modules.product.domain.exceptions import ProductNotFound
from app.modules.product.domain.value_objects import ProductCode, ProductStatus


class FakeProductRepository(ProductRepository):
    def __init__(self) -> None:
        self.rows: dict[UUID, Product] = {}  # stands in for the table

    @staticmethod
    def _row(product: Product) -> Product:
        """A stored copy, like a database row: pending events are not stored."""
        stored = deepcopy(product)
        stored.pull_events()
        return stored

    async def add(self, product: Product) -> None:
        self.rows[product.id] = self._row(product)

    async def get(self, product_id: UUID) -> Product:
        if product_id not in self.rows:
            raise ProductNotFound()
        return deepcopy(self.rows[product_id])

    async def list(self, *, status: ProductStatus | None, offset: int, limit: int) -> ProductPage:
        matches = sorted(
            (x for x in self.rows.values() if status is None or x.status is status), key=lambda x: x.name.value
        )
        return ProductPage(items=matches[offset : offset + limit], total=len(matches))

    async def update(self, product: Product) -> None:
        if product.id not in self.rows:
            raise ProductNotFound()
        self.rows[product.id] = self._row(product)

    async def delete(self, product_id: UUID) -> None:
        if self.rows.pop(product_id, None) is None:
            raise ProductNotFound()

    async def code_exists(self, code: ProductCode, *, except_id: UUID | None = None) -> bool:
        return any(x.code == code and x.id != except_id for x in self.rows.values())


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []  # tests assert on this list

    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)

    @property
    def names(self) -> list[str]:
        return [event.name for event in self.published]
