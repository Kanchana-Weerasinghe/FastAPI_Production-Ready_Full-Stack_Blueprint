from typing import Any, Generic, Protocol
from uuid import UUID

from app.core.logging import logger
from app.shared.repository import AttributeValue, EagerLoading, P, T


class RepositoryProtocol(Protocol, Generic[T, P]):
    async def read_by_options(self, schema: P | dict[str, Any], eager: EagerLoading = False) -> dict[str, Any]: ...
    async def read_by_id(self, id: UUID, eager: EagerLoading = False) -> T: ...
    async def create(self, schema: P | dict[str, Any]) -> T: ...
    async def update(self, db_obj: T, schema: P | dict[str, Any]) -> T: ...
    async def update_attribute(self, db_obj: T, column: str, value: AttributeValue) -> T: ...
    async def delete(self, db_obj: T) -> None: ...


class BaseService(Generic[T, P]):
    """
    Base service layer implementing standard orchestration patterns.

    Delegates persistence to a repository while handling logging and
    cross-cutting concerns.
    """

    def __init__(self, repository: RepositoryProtocol[T, P]) -> None:
        self._repository = repository

    async def get_list(self, schema: P | dict[str, Any], eager: EagerLoading = False) -> dict[str, Any]:
        """Fetches a paginated list of records based on the provided search schema."""
        logger.info("service_read_initiated")
        return await self._repository.read_by_options(schema, eager)

    async def get_by_id(self, id: UUID, eager: EagerLoading = False) -> T:
        """Retrieves a single record by its unique identifier."""
        logger.info("service_read_by_id_initiated", id=id)
        return await self._repository.read_by_id(id, eager)

    async def add(self, schema: P | dict[str, Any]) -> T:
        """Creates a new record in the persistence layer."""
        logger.info("service_create_initiated")
        return await self._repository.create(schema)

    async def patch(self, db_obj: T, schema: P | dict[str, Any]) -> T:
        """Updates an existing record with partial data."""
        logger.info("service_update_initiated", id=db_obj.id)
        return await self._repository.update(db_obj, schema)

    async def patch_attr(self, db_obj: T, attr: str, value: AttributeValue) -> T:
        """Updates a specific attribute of a database object."""
        logger.info("service_update_attribute_initiated", attr=attr, id=db_obj.id)
        return await self._repository.update_attribute(db_obj, attr, value)

    async def remove(self, db_obj: T) -> None:
        """Permanently removes a record from the database."""
        logger.info("service_delete_initiated", id=db_obj.id)
        await self._repository.delete(db_obj)
