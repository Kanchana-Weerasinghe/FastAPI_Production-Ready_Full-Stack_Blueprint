"""
ADAPTER: the `ItemRepository` port implemented with SQLAlchemy.

Its only job is translation: entity -> table row when saving, table row -> entity when loading. No
business rules here, and no commit: the request commits when the response is successful.
"""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.items.application.ports import ItemPage, ItemRepository
from app.modules.items.domain.entities import Item
from app.modules.items.domain.exceptions import ItemCodeTaken, ItemNotFound
from app.modules.items.domain.value_objects import ItemCode, ItemName, ItemStatus
from app.modules.items.infrastructure.persistence.models import ItemModel


class SqlAlchemyItemRepository(ItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, item: Item) -> None:
        row = ItemModel(
            id=item.id,
            name=item.name.value,
            code=item.code.value,
            status=item.status.value,
            version=1,
        )
        self.session.add(row)
        await self._flush(item.code)
        item.created_at, item.updated_at = row.created_at, row.updated_at

    async def get(self, item_id: UUID) -> Item:
        row = await self.session.get(ItemModel, item_id, populate_existing=True)
        if row is None:
            raise ItemNotFound()
        return self._to_entity(row)

    async def list(self, *, status: ItemStatus | None, offset: int, limit: int) -> ItemPage:
        conditions = [] if status is None else [ItemModel.status == status.value]
        total = await self.session.scalar(select(func.count()).select_from(ItemModel).where(*conditions))
        rows = await self.session.scalars(
            select(ItemModel).where(*conditions).order_by(ItemModel.name, ItemModel.id).offset(offset).limit(limit)
        )
        return ItemPage(items=[self._to_entity(row) for row in rows], total=total or 0)

    async def update(self, item: Item) -> None:
        row = await self.session.get(ItemModel, item.id)
        if row is None:
            raise ItemNotFound()
        row.name, row.code, row.status = item.name.value, item.code.value, item.status.value
        row.version += 1
        await self._flush(item.code)
        item.updated_at = row.updated_at

    async def delete(self, item_id: UUID) -> None:
        result = await self.session.execute(delete(ItemModel).where(ItemModel.id == item_id))
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise ItemNotFound()

    async def code_exists(self, code: ItemCode, *, except_id: UUID | None = None) -> bool:
        query = select(ItemModel.id).where(ItemModel.code == code.value)
        if except_id is not None:
            query = query.where(ItemModel.id != except_id)
        return await self.session.scalar(query.limit(1)) is not None

    async def _flush(self, code: ItemCode) -> None:
        """Sends the SQL now. If two requests save the same code at once, the unique index wins -> 409."""
        try:
            await self.session.flush()
        except IntegrityError as e:
            raise ItemCodeTaken(f"Code {code.value} is already used") from e

    @staticmethod
    def _to_entity(row: ItemModel) -> Item:
        """Table row -> entity (value objects are rebuilt, so loaded data is checked too)."""
        return Item(
            id=row.id,
            name=ItemName(row.name),
            code=ItemCode(row.code),
            status=ItemStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
