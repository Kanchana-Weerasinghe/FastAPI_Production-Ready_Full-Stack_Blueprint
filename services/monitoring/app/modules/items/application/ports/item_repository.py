"""
PORT (interface): what the use cases need from storage, without saying HOW it is stored.

The use cases only know this abstract class. Two classes implement it:
- `SqlAlchemyItemRepository` (infrastructure/persistence/): the real database, used by the app;
- `FakeItemRepository` (tests/unit/items/fakes.py): a dict in memory, used by unit tests.

To add a query: add an abstract method here, then implement it in both classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.modules.items.domain.entities import Item
from app.modules.items.domain.value_objects import ItemCode, ItemStatus


@dataclass(frozen=True, slots=True)
class ItemPage:
    """One page of a list: the items on the page and how many there are in total."""

    items: list[Item]
    total: int


class ItemRepository(ABC):
    @abstractmethod
    async def add(self, item: Item) -> None:
        """Stores a new item."""

    @abstractmethod
    async def get(self, item_id: UUID) -> Item:
        """Loads one item; raises `ItemNotFound` if the id does not exist."""

    @abstractmethod
    async def list(self, *, status: ItemStatus | None, offset: int, limit: int) -> ItemPage:
        """One page of items sorted by name, optionally only those with `status`."""

    @abstractmethod
    async def update(self, item: Item) -> None:
        """Saves the changes of an existing item."""

    @abstractmethod
    async def delete(self, item_id: UUID) -> None:
        """Deletes one item; raises `ItemNotFound` if the id does not exist."""

    @abstractmethod
    async def code_exists(self, code: ItemCode, *, except_id: UUID | None = None) -> bool:
        """True if another item (not `except_id`) already uses this code (the fact the policy needs)."""
