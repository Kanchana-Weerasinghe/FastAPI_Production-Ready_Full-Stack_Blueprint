import time
from typing import Any

from app.modules.audit.service import AuditService
from app.modules.flags.application.ports.feature_flag_repository import FeatureFlagRepositoryPort
from app.modules.flags.domain.entities import FeatureFlagLike, FeatureFlagState
from app.modules.flags.domain.policies import is_flag_enabled, rollout_bucket
from app.shared.actor import Actor

CACHE_TTL_SECONDS = 30.0
# Per-process cache of all flags: evaluating a flag must not cost a query per request. Changes
# propagate within CACHE_TTL_SECONDS (immediately in the process that made the change).
_cache: dict[str, Any] = {"loaded_at": 0.0, "flags": {}}


def bucket(key: str, user_id: object) -> int:
    """Stable 0-99 bucket per (flag, user): the same user stays in or out as the percentage grows."""
    return rollout_bucket(key, str(user_id))


def invalidate_cache() -> None:
    _cache["loaded_at"] = 0.0


class FeatureFlagService:
    """Public API of the flags module: evaluate flags, and manage them (admin)."""

    def __init__(self, repository: FeatureFlagRepositoryPort, audit: AuditService):
        self._flags = repository
        self.audit = audit

    async def _snapshot(self) -> dict[str, FeatureFlagState]:
        if time.monotonic() - _cache["loaded_at"] > CACHE_TTL_SECONDS:
            _cache["flags"] = {flag.key: flag for flag in await self._flags.list_flags()}
            _cache["loaded_at"] = time.monotonic()
        flags: dict[str, FeatureFlagState] = _cache["flags"]
        return flags

    @staticmethod
    def evaluate(flag: FeatureFlagLike | None, user_id: object | None, role: str | None) -> bool:
        if flag is None:
            return False
        return is_flag_enabled(
            key=flag.key,
            enabled=flag.enabled,
            rollout_percentage=flag.rollout_percentage,
            roles=flag.roles,
            user_id=str(user_id) if user_id is not None else None,
            role=role,
        )

    async def is_enabled(self, key: str, actor: Actor | None = None, role: str | None = None) -> bool:
        flags = await self._snapshot()
        return self.evaluate(flags.get(key), actor.id if actor else None, role)

    async def evaluate_all(self, actor: Actor, role: str | None) -> dict[str, bool]:
        flags = await self._snapshot()
        return {key: self.evaluate(flag, actor.id, role) for key, flag in flags.items()}

    async def list_all(self) -> list[FeatureFlagState]:
        return await self._flags.list_flags()

    async def upsert(self, key: str, data: dict[str, Any], actor: Actor) -> FeatureFlagState:
        flag = await self._flags.get_flag(key)
        values = {**data, "updated_by": actor.username}
        if flag is None:
            flag = await self._flags.create_flag({"key": key, **values, "created_by": actor.username})
        else:
            flag = await self._flags.update_flag(key, values)
        await self.audit.record(
            "feature_flag.updated",
            actor_id=actor.id,
            resource_type="feature_flag",
            resource_id=key,
            details=data,
        )
        invalidate_cache()
        return flag
