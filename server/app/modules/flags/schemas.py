from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

_camel = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class FeatureFlag(BaseModel):
    model_config = _camel
    key: str
    description: str
    enabled: bool
    rollout_percentage: int
    roles: list[str]


class FeatureFlagUpdate(BaseModel):
    model_config = _camel
    description: str = Field("", max_length=500)
    enabled: bool = False
    rollout_percentage: int = Field(100, ge=0, le=100)
    roles: list[str] = Field(default_factory=list)


class EvaluatedFlags(BaseModel):
    """Flags as evaluated for the current user (what the web app uses)."""

    flags: dict[str, bool]
