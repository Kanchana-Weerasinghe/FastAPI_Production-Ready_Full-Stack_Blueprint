"""Persistence-independent feature-flag configuration."""

from dataclasses import dataclass
from typing import Protocol


class FeatureFlagLike(Protocol):
    """Attributes required to evaluate a flag, including the SQLAlchemy adapter model."""

    key: str
    description: str
    enabled: bool
    rollout_percentage: int
    roles: list[str]


@dataclass(slots=True)
class FeatureFlagState:
    key: str
    description: str
    enabled: bool
    rollout_percentage: int
    roles: list[str]
