"""
USE CASES: the STEPS of each user action. No rules here (they are in policies.py, run by the entity).

Every method follows the same steps:
    1. turn the input into value objects   (they check the format: 422)
    2. load the product               (repository: 404)
    3. fetch the facts a rule needs         (e.g. "is this code taken?")
    4. call ONE entity method               (it checks its rule: 409, then changes the data)
    5. save                                  (repository)
    6. publish the events                    (sent only after the commit)

A use case receives plain values (commands, ids) and returns entities, never HTTP objects. It never
commits (the request does) and never checks roles (the router's access check does). Its dependencies
are injected by container.py, so unit tests pass in-memory fakes.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.product.application.ports import EventPublisher, ProductPage, ProductRepository
from app.modules.product.domain.entities import Product
from app.modules.product.domain.value_objects import ProductCode, ProductName, ProductStatus

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    """Input of `create`."""

    name: str
    code: str


@dataclass(frozen=True, slots=True)
class UpdateProductCommand:
    """Input of `update`: only the fields that are not None change."""

    name: str | None = None
    code: str | None = None


class ProductUseCases:
    def __init__(self, repository: ProductRepository, events: EventPublisher, clock: Clock = utc_now) -> None:
        self.repository = repository
        self.events = events
        self.clock = clock  # injected so tests can fix the time

    async def create(self, command: CreateProductCommand) -> Product:
        name, code = ProductName(command.name), ProductCode(command.code)  # 1. value objects
        taken = await self.repository.code_exists(code)  # 3. fact
        product = Product.create(name=name, code=code, code_taken=taken, at=self.clock())  # 4. entity
        await self.repository.add(product)  # 5. save
        self.events.publish_after_commit(product.pull_events())  # 6. events
        return product

    async def get(self, product_id: UUID) -> Product:
        return await self.repository.get(product_id)

    async def list(self, *, status: ProductStatus | None, offset: int, limit: int) -> ProductPage:
        return await self.repository.list(status=status, offset=offset, limit=limit)

    async def update(self, product_id: UUID, command: UpdateProductCommand) -> Product:
        product = await self.repository.get(product_id)  # 2. load
        now = self.clock()
        if command.name is not None:
            product.rename(ProductName(command.name), at=now)  # 4. entity
        if command.code is not None:
            code = ProductCode(command.code)
            taken = await self.repository.code_exists(code, except_id=product.id)  # 3. fact
            product.change_code(code, code_taken=taken, at=now)  # 4. entity
        return await self._save(product)

    async def archive(self, product_id: UUID) -> Product:
        product = await self.repository.get(product_id)
        product.archive(at=self.clock())
        return await self._save(product)

    async def restore(self, product_id: UUID) -> Product:
        product = await self.repository.get(product_id)
        product.restore(at=self.clock())
        return await self._save(product)

    async def delete(self, product_id: UUID) -> None:
        product = await self.repository.get(product_id)
        product.delete()  # the rule: archived first
        await self.repository.delete(product_id)

    async def _save(self, product: Product) -> Product:
        await self.repository.update(product)  # 5. save
        self.events.publish_after_commit(product.pull_events())  # 6. events
        return product
