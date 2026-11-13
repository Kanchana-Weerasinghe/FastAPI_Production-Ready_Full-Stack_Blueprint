"""
USE-CASE TESTS: the steps of each use case, with in-memory fakes instead of the database and the broker.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.items.application.use_cases import CreateItemCommand, ItemUseCases, UpdateItemCommand
from app.modules.items.domain.exceptions import InvalidItemState, ItemCodeTaken, ItemNotFound
from app.modules.items.domain.value_objects import ItemStatus
from tests.unit.items.fakes import FakeEventPublisher, FakeItemRepository

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def repo() -> FakeItemRepository:
    return FakeItemRepository()


@pytest.fixture
def events() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def use_cases(repo: FakeItemRepository, events: FakeEventPublisher) -> ItemUseCases:
    return ItemUseCases(repo, events, clock=lambda: NOW)  # fixed clock: predictable timestamps


async def test_create_saves_and_publishes_created(
    use_cases: ItemUseCases, repo: FakeItemRepository, events: FakeEventPublisher
) -> None:
    item = await use_cases.create(CreateItemCommand(name=" Blue  pen ", code="itm-001"))
    assert (item.name.value, item.code.value) == ("Blue pen", "ITM-001")
    assert item.id in repo.rows
    assert events.names == ["ItemCreated"]


async def test_create_refuses_a_taken_code(use_cases: ItemUseCases, repo: FakeItemRepository) -> None:
    await use_cases.create(CreateItemCommand(name="Blue pen", code="ITM-001"))
    with pytest.raises(ItemCodeTaken):
        await use_cases.create(CreateItemCommand(name="Red pen", code="itm-001"))
    assert len(repo.rows) == 1  # nothing saved


async def test_get_an_unknown_id_is_not_found(use_cases: ItemUseCases) -> None:
    with pytest.raises(ItemNotFound):
        await use_cases.get(uuid4())


async def test_list_filters_by_status_and_paginates(use_cases: ItemUseCases) -> None:
    for name, code in [("Pencil", "ITM-003"), ("Blue pen", "ITM-001"), ("Marker", "ITM-002")]:
        await use_cases.create(CreateItemCommand(name=name, code=code))
    page = await use_cases.list(status=None, offset=0, limit=2)
    assert [x.name.value for x in page.items] == ["Blue pen", "Marker"]
    assert page.total == 3
    archived = await use_cases.list(status=ItemStatus.ARCHIVED, offset=0, limit=10)
    assert archived.total == 0


async def test_update_changes_only_the_fields_sent(use_cases: ItemUseCases) -> None:
    item = await use_cases.create(CreateItemCommand(name="Blue pen", code="ITM-001"))
    updated = await use_cases.update(item.id, UpdateItemCommand(name="Red pen"))
    assert (updated.name.value, updated.code.value) == ("Red pen", "ITM-001")


async def test_update_may_keep_its_own_code_but_not_take_another(use_cases: ItemUseCases) -> None:
    first = await use_cases.create(CreateItemCommand(name="Blue pen", code="ITM-001"))
    await use_cases.create(CreateItemCommand(name="Red pen", code="ITM-002"))
    await use_cases.update(first.id, UpdateItemCommand(code="ITM-001"))  # its own code: fine
    with pytest.raises(ItemCodeTaken):
        await use_cases.update(first.id, UpdateItemCommand(code="ITM-002"))


async def test_archived_item_cannot_be_updated(use_cases: ItemUseCases) -> None:
    item = await use_cases.create(CreateItemCommand(name="Blue pen", code="ITM-001"))
    await use_cases.archive(item.id)
    with pytest.raises(InvalidItemState):  # the policy, run by the entity method, reached through the use case
        await use_cases.update(item.id, UpdateItemCommand(name="Red pen"))


async def test_archive_publishes_archived(use_cases: ItemUseCases, events: FakeEventPublisher) -> None:
    item = await use_cases.create(CreateItemCommand(name="Blue pen", code="ITM-001"))
    archived = await use_cases.archive(item.id)
    assert archived.status is ItemStatus.ARCHIVED
    assert events.names == ["ItemCreated", "ItemArchived"]


async def test_delete_needs_archive_first(use_cases: ItemUseCases, repo: FakeItemRepository) -> None:
    item = await use_cases.create(CreateItemCommand(name="Blue pen", code="ITM-001"))
    with pytest.raises(InvalidItemState):
        await use_cases.delete(item.id)
    await use_cases.archive(item.id)
    await use_cases.delete(item.id)
    assert repo.rows == {}
