from typing import Any
from uuid import UUID

import structlog

from app.core.logging import logger
from app.modules.audit.application.ports.audit_repository import AuditRepositoryPort

SUCCESS = "success"
FAILURE = "failure"


class AuditService:
    """Application API for appending and querying security-relevant audit events."""

    def __init__(self, repository: AuditRepositoryPort) -> None:
        self._audit = repository

    async def record(
        self,
        action: str,
        *,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | str | None = None,
        outcome: str = SUCCESS,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Appends an event to the current transaction. Never include credentials or secrets."""
        context = structlog.contextvars.get_contextvars()
        await self._audit.append(
            {
                "actor_id": actor_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id is not None else None,
                "outcome": outcome,
                "ip_address": context.get("client_ip"),
                "user_agent": (context.get("user_agent") or "")[:500] or None,
                "request_id": context.get("request_id"),
                "details": details or {},
                "created_by": str(actor_id) if actor_id else "system",
                "updated_by": str(actor_id) if actor_id else "system",
            }
        )
        logger.info("audit_recorded", action=action, outcome=outcome, actor_id=actor_id)

    async def get_list(self, filters: dict[str, Any]) -> dict[str, Any]:
        return await self._audit.list_entries(filters)

    async def feed(self, filters: dict[str, Any], *, cursor: str | None, limit: int) -> dict[str, Any]:
        """Returns the newest-first, keyset-paginated audit trail."""
        items, next_cursor = await self._audit.list_by_cursor(filters, cursor=cursor, limit=limit)
        return {"items": items, "next_cursor": next_cursor}
