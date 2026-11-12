"""
TEST DOUBLES: in-memory versions of the ports, so use-case tests run without a database or a broker.
They implement the same interfaces as the real adapters.
"""

from collections.abc import Sequence
from copy import deepcopy
from uuid import UUID

from app.modules.items.application.ports import EventPublisher, ItemPage, ItemRepository
from app.modules.items.domain.entities import Item
from app.modules.items.domain.events import DomainEvent
from app.modules.items.domain.exceptions import ItemNotFound
from app.modules.items.domain.value_objects import ItemCode, ItemStatus


class FakeItemRepository(ItemRepository):
    def __init__(self) -> None:
        self.rows: dict[UUID, Item] = {}  # stands in for the table

    @staticmethod
    def _row(item: Item) -> Item:
        """A stored copy, like a database row: pending events are not stored."""
        stored = deepcopy(item)
        stored.pull_events()
        return stored

    async def add(self, item: Item) -> None:
        self.rows[item.id] = self._row(item)

    async def get(self, item_id: UUID) -> Item:
        if item_id not in self.rows:
            raise ItemNotFound()
        return deepcopy(self.rows[item_id])

    async def list(self, *, status: ItemStatus | None, offset: int, limit: int) -> ItemPage:
        matches = sorted(
            (x for x in self.rows.values() if status is None or x.status is status), key=lambda x: x.name.value
        )
        return ItemPage(items=matches[offset : offset + limit], total=len(matches))

    async def update(self, item: Item) -> None:
        if item.id not in self.rows:
            raise ItemNotFound()
        self.rows[item.id] = self._row(item)

    async def delete(self, item_id: UUID) -> None:
        if self.rows.pop(item_id, None) is None:
            raise ItemNotFound()

    async def code_exists(self, code: ItemCode, *, except_id: UUID | None = None) -> bool:
        return any(x.code == code and x.id != except_id for x in self.rows.values())


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []  # tests assert on this list

    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)

    @property
    def names(self) -> list[str]:
        return [event.name for event in self.published]
