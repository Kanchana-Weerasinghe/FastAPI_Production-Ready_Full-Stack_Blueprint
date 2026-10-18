"""Persistence contract for feature-flag management."""

from typing import Any, Protocol

from app.modules.flags.domain.entities import FeatureFlagState


class FeatureFlagRepositoryPort(Protocol):
    async def list_flags(self) -> list[FeatureFlagState]: ...

    async def get_flag(self, key: str) -> FeatureFlagState | None: ...

    async def create_flag(self, values: dict[str, Any]) -> FeatureFlagState: ...

    async def update_flag(self, key: str, values: dict[str, Any]) -> FeatureFlagState: ...
