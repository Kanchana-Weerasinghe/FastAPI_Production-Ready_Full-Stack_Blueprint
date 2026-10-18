import time
from typing import Annotated, Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import false, func, select, true, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from app.core.config import config
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.logging import logger
from app.shared.models import BaseModel
from app.shared.pagination import decode_cursor, encode_cursor
from app.shared.utils.query_builder import sqlalchemy_query_builder

T = TypeVar("T", bound=BaseModel)
P = TypeVar("P", bound=PydanticBaseModel, contravariant=True)

EagerLoading = Annotated[bool | list[str], "Boolean to load all eagers or specific eagers"]
AttributeValue = Annotated[int | str | bool | UUID, "Acceptable types for a single database column update"]


class BaseRepository(Generic[T, P]):
    """
    Abstract base class for data persistence using SQLAlchemy.

    Provides a standard set of CRUD operations with support for soft-deletes,
    active-record filtering, and dynamic query building.

    Attributes:
        model: The SQLAlchemy model class this repository manages.
        session: The asynchronous database session for transactions.
    """

    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def read_by_options(self, schema: P | dict[str, Any], eager: EagerLoading = False) -> dict[str, Any]:
        """
        Queries records based on filter options and pagination settings.

        Args:
            schema: Pydantic model or dict containing filters (e.g., page, page_size, ordering).
            eager: Whether to load joined relationships. Can be a bool or list of strings.

        Returns:
            A dictionary containing the list of 'founds' items and 'search_options' metadata.
        """
        start_time = time.perf_counter()
        schema_as_dict = schema.model_dump(exclude_none=True) if hasattr(schema, "model_dump") else schema
        is_active = schema_as_dict.pop("is_active", None)
        ordering = schema_as_dict.get("ordering", config.ORDERING)
        page = schema_as_dict.get("page", config.PAGE)
        page_size = schema_as_dict.get("page_size", config.PAGE_SIZE)
        column_name = ordering.removeprefix("-")
        # Defence in depth (schemas already allow-list ordering): only public mapped columns are sortable.
        if column_name.startswith("_") or column_name not in self.model.__mapper__.columns.keys():
            raise BadRequestError(detail="Invalid ordering field")
        column = getattr(self.model, column_name)
        order_query = column.desc() if ordering.startswith("-") else column.asc()
        filter_options = sqlalchemy_query_builder(self.model, schema_as_dict)
        query = select(self.model).where(self.model.is_deleted.is_(false()))
        if is_active is not None:
            query = query.where(self.model.is_active.is_(true() if is_active else false()))
        if eager:
            eager_list = eager if isinstance(eager, (list, tuple)) else getattr(self.model, "eagers", [])
            for eager_attr in eager_list:
                query = query.options(selectinload(getattr(self.model, eager_attr)))
        query = query.where(filter_options).order_by(order_query)
        if page_size != "all":
            query = query.limit(page_size).offset((page - 1) * page_size)
        result = await self.session.execute(query)
        items = list(result.scalars().all())
        count_query = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.is_deleted.is_(false()),
                filter_options,
            )
        )
        if is_active is not None:
            count_query = count_query.where(self.model.is_active.is_(true() if is_active else false()))
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar() or 0
        duration = time.perf_counter() - start_time
        logger.info(
            "read_by_options_completed",
            model=self.model.__name__,
            founds=len(items),
            total=total_count,
            duration=f"{duration:.4f}s",
        )
        return {
            "founds": items,
            "search_options": {
                "page": page,
                "page_size": page_size,
                "ordering": ordering,
                "total_count": total_count,
            },
        }

    async def read_by_id(self, id: UUID, eager: EagerLoading = False) -> T:
        """
        Retrieves a single record by its UUID.

        Args:
            id: The unique identifier of the record.
            eager: Whether to load joined relationships.

        Returns:
            The retrieved model instance.

        Raises:
            NotFoundError: If the record is missing, inactive, or deleted.
        """
        start_time = time.perf_counter()
        query = select(self.model).where(
            self.model.id == id, self.model.is_active.is_(true()), self.model.is_deleted.is_(false())
        )
        if eager:
            eager_list = eager if isinstance(eager, (list, tuple)) else getattr(self.model, "eagers", [])
            for eager_attr in eager_list:
                query = query.options(selectinload(getattr(self.model, eager_attr)))
        result = await self.session.execute(query)
        db_obj = result.scalar_one_or_none()
        duration = time.perf_counter() - start_time
        logger.info("read_by_id_completed", model=self.model.__name__, id=id, duration=f"{duration:.4f}s")
        if not db_obj:
            raise NotFoundError(detail="Record not found")
        return db_obj

    async def create(self, schema: P | dict[str, Any]) -> T:
        """
        Persists a new record to the database.

        Args:
            schema: The input data, either as a Pydantic model or a dictionary.

        Returns:
            The newly created and flushed model instance.

        Raises:
            ConflictError: If a unique constraint is violated.
        """
        start_time = time.perf_counter()
        obj_data = schema.model_dump() if hasattr(schema, "model_dump") else schema
        model_columns = self.model.__table__.columns.keys()
        data = {k: v for k, v in obj_data.items() if k in model_columns}
        db_obj = self.model(**data)
        try:
            self.session.add(db_obj)
            await self.session.flush()
            await self.session.refresh(db_obj)
            duration = time.perf_counter() - start_time
            logger.info("create_completed", model=self.model.__name__, id=db_obj.id, duration=f"{duration:.4f}s")
        except IntegrityError as e:
            logger.error("integrity_error", model=self.model.__name__, error=str(e.orig))
            # Never echo database error text (table/constraint names, values) back to the client.
            raise ConflictError(detail="Resource already exists or violates a constraint") from e
        return db_obj

    async def update(self, db_obj: T, schema: P | dict[str, Any]) -> T:
        """
        Updates an existing record with new values.

        Args:
            db_obj: The existing database object to update.
            schema: The partial update data (Pydantic model or dict).

        Returns:
            The updated model instance.
        """
        start_time = time.perf_counter()
        obj_data = schema.model_dump(exclude_none=True) if hasattr(schema, "model_dump") else schema
        model_columns = self.model.__table__.columns.keys()
        for key, value in obj_data.items():
            if key in model_columns:
                setattr(db_obj, key, value)
        await self._flush()
        await self.session.refresh(db_obj)
        duration = time.perf_counter() - start_time
        logger.info("update_completed", model=self.model.__name__, id=db_obj.id, duration=f"{duration:.4f}s")
        return db_obj

    async def update_attribute(self, db_obj: T, column: str, value: AttributeValue) -> T:
        """
        Updates a single attribute of a database object.

        Args:
            db_obj: The object to modify.
            column: The name of the database column.
            value: The new value to set.

        Returns:
            The updated model instance.
        """
        start_time = time.perf_counter()
        setattr(db_obj, column, value)
        await self._flush()
        await self.session.refresh(db_obj)
        duration = time.perf_counter() - start_time
        logger.info(
            "update_attribute_completed",
            model=self.model.__name__,
            id=db_obj.id,
            column=column,
            duration=f"{duration:.4f}s",
        )
        return db_obj

    async def delete(self, db_obj: T) -> None:
        """
        Hard-deletes a record from the database.

        Args:
            db_obj: The database object to remove.
        """
        start_time = time.perf_counter()
        await self.session.delete(db_obj)
        await self._flush()
        duration = time.perf_counter() - start_time
        logger.info("delete_completed", model=self.model.__name__, id=db_obj.id, duration=f"{duration:.4f}s")

    async def soft_delete(self, db_obj: T, deleted_by: str) -> T:
        """
        Marks a record as deleted instead of removing it. Every query in this repository already
        excludes `is_deleted` rows, so soft-deleted data disappears from the API but stays
        recoverable (and auditable) until a retention job purges it.
        """
        db_obj.is_deleted = True
        db_obj.updated_by = deleted_by
        await self._flush()
        logger.info("soft_delete_completed", model=self.model.__name__, id=db_obj.id)
        return db_obj

    async def read_by_cursor(
        self, filters: dict[str, Any], *, cursor: str | None, limit: int, descending: bool = True
    ) -> tuple[list[T], str | None]:
        """
        Keyset pagination on (created_at, id). Returns one page and the cursor of the next page
        (None when this is the last page). See `app/shared/pagination.py`.
        """
        query = select(self.model).where(
            self.model.is_deleted.is_(false()), sqlalchemy_query_builder(self.model, filters)
        )
        key = tuple_(self.model.created_at, self.model.id)
        if cursor:
            after = tuple(decode_cursor(cursor))
            query = query.where(key < after if descending else key > after)
        order = (
            (self.model.created_at.desc(), self.model.id.desc())
            if descending
            else (
                self.model.created_at.asc(),
                self.model.id.asc(),
            )
        )
        rows = list((await self.session.execute(query.order_by(*order).limit(limit + 1))).scalars())
        items = rows[:limit]
        next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if len(rows) > limit else None
        return items, next_cursor

    async def _flush(self) -> None:
        try:
            await self.session.flush()
        except StaleDataError as e:
            logger.warning("optimistic_lock_conflict", model=self.model.__name__)
            raise ConflictError(
                "The resource was modified by someone else. Reload it and try again.",
                code="concurrent_modification",
            ) from e
