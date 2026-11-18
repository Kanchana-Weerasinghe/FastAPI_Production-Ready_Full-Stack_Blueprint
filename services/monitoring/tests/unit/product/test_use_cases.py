"""
USE-CASE TESTS: the steps of each use case, with in-memory fakes instead of the database and the broker.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.product.application.use_cases import CreateProductCommand, ProductUseCases, UpdateProductCommand
from app.modules.product.domain.exceptions import InvalidProductState, ProductCodeTaken, ProductNotFound
from app.modules.product.domain.value_objects import ProductStatus
from tests.unit.product.fakes import FakeEventPublisher, FakeProductRepository

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def repo() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def events() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def use_cases(repo: FakeProductRepository, events: FakeEventPublisher) -> ProductUseCases:
    return ProductUseCases(repo, events, clock=lambda: NOW)  # fixed clock: predictable timestamps


async def test_create_saves_and_publishes_created(
    use_cases: ProductUseCases, repo: FakeProductRepository, events: FakeEventPublisher
) -> None:
    product = await use_cases.create(CreateProductCommand(name=" Blue  pen ", code="itm-001"))
    assert (product.name.value, product.code.value) == ("Blue pen", "ITM-001")
    assert product.id in repo.rows
    assert events.names == ["ProductCreated"]


async def test_create_refuses_a_taken_code(use_cases: ProductUseCases, repo: FakeProductRepository) -> None:
    await use_cases.create(CreateProductCommand(name="Blue pen", code="ITM-001"))
    with pytest.raises(ProductCodeTaken):
        await use_cases.create(CreateProductCommand(name="Red pen", code="itm-001"))
    assert len(repo.rows) == 1  # nothing saved


async def test_get_an_unknown_id_is_not_found(use_cases: ProductUseCases) -> None:
    with pytest.raises(ProductNotFound):
        await use_cases.get(uuid4())


async def test_list_filters_by_status_and_paginates(use_cases: ProductUseCases) -> None:
    for name, code in [("Pencil", "ITM-003"), ("Blue pen", "ITM-001"), ("Marker", "ITM-002")]:
        await use_cases.create(CreateProductCommand(name=name, code=code))
    page = await use_cases.list(status=None, offset=0, limit=2)
    assert [x.name.value for x in page.items] == ["Blue pen", "Marker"]
    assert page.total == 3
    archived = await use_cases.list(status=ProductStatus.ARCHIVED, offset=0, limit=10)
    assert archived.total == 0


async def test_update_changes_only_the_fields_sent(use_cases: ProductUseCases) -> None:
    product = await use_cases.create(CreateProductCommand(name="Blue pen", code="ITM-001"))
    updated = await use_cases.update(product.id, UpdateProductCommand(name="Red pen"))
    assert (updated.name.value, updated.code.value) == ("Red pen", "ITM-001")


async def test_update_may_keep_its_own_code_but_not_take_another(use_cases: ProductUseCases) -> None:
    first = await use_cases.create(CreateProductCommand(name="Blue pen", code="ITM-001"))
    await use_cases.create(CreateProductCommand(name="Red pen", code="ITM-002"))
    await use_cases.update(first.id, UpdateProductCommand(code="ITM-001"))  # its own code: fine
    with pytest.raises(ProductCodeTaken):
        await use_cases.update(first.id, UpdateProductCommand(code="ITM-002"))


async def test_archived_product_cannot_be_updated(use_cases: ProductUseCases) -> None:
    product = await use_cases.create(CreateProductCommand(name="Blue pen", code="ITM-001"))
    await use_cases.archive(product.id)
    with pytest.raises(InvalidProductState):  # the policy, run by the entity method, reached through the use case
        await use_cases.update(product.id, UpdateProductCommand(name="Red pen"))


async def test_archive_publishes_archived(use_cases: ProductUseCases, events: FakeEventPublisher) -> None:
    product = await use_cases.create(CreateProductCommand(name="Blue pen", code="ITM-001"))
    archived = await use_cases.archive(product.id)
    assert archived.status is ProductStatus.ARCHIVED
    assert events.names == ["ProductCreated", "ProductArchived"]


async def test_delete_needs_archive_first(use_cases: ProductUseCases, repo: FakeProductRepository) -> None:
    product = await use_cases.create(CreateProductCommand(name="Blue pen", code="ITM-001"))
    with pytest.raises(InvalidProductState):
        await use_cases.delete(product.id)
    await use_cases.archive(product.id)
    await use_cases.delete(product.id)
    assert repo.rows == {}
