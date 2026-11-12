"""
USE CASES: the STEPS of each user action. No rules here (they are in policies.py, run by the entity).

Every method follows the same steps:
    1. turn the input into value objects   (they check the format: 422)
    2. load the item               (repository: 404)
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

from app.modules.items.application.ports import EventPublisher, ItemPage, ItemRepository
from app.modules.items.domain.entities import Item
from app.modules.items.domain.value_objects import ItemCode, ItemName, ItemStatus

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CreateItemCommand:
    """Input of `create`."""

    name: str
    code: str


@dataclass(frozen=True, slots=True)
class UpdateItemCommand:
    """Input of `update`: only the fields that are not None change."""

    name: str | None = None
    code: str | None = None


class ItemUseCases:
    def __init__(self, repository: ItemRepository, events: EventPublisher, clock: Clock = utc_now) -> None:
        self.repository = repository
        self.events = events
        self.clock = clock  # injected so tests can fix the time

    async def create(self, command: CreateItemCommand) -> Item:
        name, code = ItemName(command.name), ItemCode(command.code)  # 1. value objects
        taken = await self.repository.code_exists(code)  # 3. fact
        item = Item.create(name=name, code=code, code_taken=taken, at=self.clock())  # 4. entity
        await self.repository.add(item)  # 5. save
        self.events.publish_after_commit(item.pull_events())  # 6. events
        return item

    async def get(self, item_id: UUID) -> Item:
        return await self.repository.get(item_id)

    async def list(self, *, status: ItemStatus | None, offset: int, limit: int) -> ItemPage:
        return await self.repository.list(status=status, offset=offset, limit=limit)

    async def update(self, item_id: UUID, command: UpdateItemCommand) -> Item:
        item = await self.repository.get(item_id)  # 2. load
        now = self.clock()
        if command.name is not None:
            item.rename(ItemName(command.name), at=now)  # 4. entity
        if command.code is not None:
            code = ItemCode(command.code)
            taken = await self.repository.code_exists(code, except_id=item.id)  # 3. fact
            item.change_code(code, code_taken=taken, at=now)  # 4. entity
        return await self._save(item)

    async def archive(self, item_id: UUID) -> Item:
        item = await self.repository.get(item_id)
        item.archive(at=self.clock())
        return await self._save(item)

    async def restore(self, item_id: UUID) -> Item:
        item = await self.repository.get(item_id)
        item.restore(at=self.clock())
        return await self._save(item)

    async def delete(self, item_id: UUID) -> None:
        item = await self.repository.get(item_id)
        item.delete()  # the rule: archived first
        await self.repository.delete(item_id)

    async def _save(self, item: Item) -> Item:
        await self.repository.update(item)  # 5. save
        self.events.publish_after_commit(item.pull_events())  # 6. events
        return item
