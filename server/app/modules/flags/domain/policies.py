"""Pure feature-flag evaluation policies."""

import hashlib
from uuid import UUID


def rollout_bucket(key: str, user_id: UUID | str) -> int:
    """Return a stable percentage bucket so gradual rollouts remain deterministic."""
    digest = hashlib.sha256(f"{key}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100


def is_flag_enabled(
    *,
    key: str,
    enabled: bool,
    rollout_percentage: int,
    roles: list[str],
    user_id: UUID | str | None,
    role: str | None,
) -> bool:
    """Evaluate enabled state, role targeting, and deterministic percentage rollout."""
    if not enabled:
        return False
    if role is not None and role in roles:
        return True
    if rollout_percentage >= 100:
        return True
    return user_id is not None and rollout_bucket(key, user_id) < rollout_percentage
