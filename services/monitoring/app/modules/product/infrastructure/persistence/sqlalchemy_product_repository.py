"""
ADAPTER: the `ProductRepository` port implemented with SQLAlchemy.

Its only job is translation: entity -> table row when saving, table row -> entity when loading. No
business rules here, and no commit: the request commits when the response is successful.
"""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.application.ports import ProductPage, ProductRepository
from app.modules.product.domain.entities import Product
from app.modules.product.domain.exceptions import ProductCodeTaken, ProductNotFound
from app.modules.product.domain.value_objects import ProductCode, ProductName, ProductStatus
from app.modules.product.infrastructure.persistence.models import ProductModel


class SqlAlchemyProductRepository(ProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, product: Product) -> None:
        row = ProductModel(
            id=product.id,
            name=product.name.value,
            code=product.code.value,
            status=product.status.value,
            version=1,
        )
        self.session.add(row)
        await self._flush(product.code)
        product.created_at, product.updated_at = row.created_at, row.updated_at

    async def get(self, product_id: UUID) -> Product:
        row = await self.session.get(ProductModel, product_id, populate_existing=True)
        if row is None:
            raise ProductNotFound()
        return self._to_entity(row)

    async def list(self, *, status: ProductStatus | None, offset: int, limit: int) -> ProductPage:
        conditions = [] if status is None else [ProductModel.status == status.value]
        total = await self.session.scalar(select(func.count()).select_from(ProductModel).where(*conditions))
        rows = await self.session.scalars(
            select(ProductModel)
            .where(*conditions)
            .order_by(ProductModel.name, ProductModel.id)
            .offset(offset)
            .limit(limit)
        )
        return ProductPage(items=[self._to_entity(row) for row in rows], total=total or 0)

    async def update(self, product: Product) -> None:
        row = await self.session.get(ProductModel, product.id)
        if row is None:
            raise ProductNotFound()
        row.name, row.code, row.status = product.name.value, product.code.value, product.status.value
        row.version += 1
        await self._flush(product.code)
        product.updated_at = row.updated_at

    async def delete(self, product_id: UUID) -> None:
        result = await self.session.execute(delete(ProductModel).where(ProductModel.id == product_id))
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise ProductNotFound()

    async def code_exists(self, code: ProductCode, *, except_id: UUID | None = None) -> bool:
        query = select(ProductModel.id).where(ProductModel.code == code.value)
        if except_id is not None:
            query = query.where(ProductModel.id != except_id)
        return await self.session.scalar(query.limit(1)) is not None

    async def _flush(self, code: ProductCode) -> None:
        """Sends the SQL now. If two requests save the same code at once, the unique index wins -> 409."""
        try:
            await self.session.flush()
        except IntegrityError as e:
            raise ProductCodeTaken(f"Code {code.value} is already used") from e

    @staticmethod
    def _to_entity(row: ProductModel) -> Product:
        """Table row -> entity (value objects are rebuilt, so loaded data is checked too)."""
        return Product(
            id=row.id,
            name=ProductName(row.name),
            code=ProductCode(row.code),
            status=ProductStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
