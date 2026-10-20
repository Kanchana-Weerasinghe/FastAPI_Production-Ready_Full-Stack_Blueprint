from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.domain.entities import AuditEntry
from app.modules.audit.infrastructure.persistence.models import AuditLogs
from app.shared.repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLogs, BaseModel]):
    """Insert and query audit entries. No update/delete use cases exist for this table."""

    def __init__(self, session: AsyncSession):
        super().__init__(model=AuditLogs, session=session)

    @staticmethod
    def _to_entity(row: AuditLogs) -> AuditEntry:
        return AuditEntry(
            id=row.id,
            created_at=row.created_at,
            actor_id=row.actor_id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            outcome=row.outcome,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            request_id=row.request_id,
            details=row.details,
        )

    async def append(self, values: dict[str, Any]) -> AuditEntry:
        return self._to_entity(await super().create(values))

    async def list_entries(self, filters: dict[str, Any]) -> dict[str, Any]:
        result = await self.read_by_options(filters)
        return {**result, "founds": [self._to_entity(row) for row in result["founds"]]}

    async def list_by_cursor(
        self, filters: dict[str, Any], *, cursor: str | None, limit: int
    ) -> tuple[list[AuditEntry], str | None]:
        entries, next_cursor = await super().read_by_cursor(filters, cursor=cursor, limit=limit)
        return [self._to_entity(row) for row in entries], next_cursor
