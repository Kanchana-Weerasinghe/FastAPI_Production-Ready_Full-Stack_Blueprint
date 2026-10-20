"""Persistence contract for append-only audit records."""

from typing import Any, Protocol

from app.modules.audit.domain.entities import AuditEntry


class AuditRepositoryPort(Protocol):
    async def append(self, values: dict[str, Any]) -> AuditEntry: ...

    async def list_entries(self, filters: dict[str, Any]) -> dict[str, Any]: ...

    async def list_by_cursor(
        self, filters: dict[str, Any], *, cursor: str | None, limit: int
    ) -> tuple[list[AuditEntry], str | None]: ...
