from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.flags.domain.entities import FeatureFlagState
from app.modules.flags.infrastructure.persistence.models import FeatureFlags
from app.shared.repository import BaseRepository


class FeatureFlagRepository(BaseRepository[FeatureFlags, BaseModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=FeatureFlags, session=session)

    @staticmethod
    def _to_entity(flag: FeatureFlags) -> FeatureFlagState:
        return FeatureFlagState(
            key=flag.key,
            description=flag.description,
            enabled=flag.enabled,
            rollout_percentage=flag.rollout_percentage,
            roles=flag.roles,
        )

    async def list_flags(self) -> list[FeatureFlagState]:
        rows = (await self.session.execute(select(FeatureFlags).order_by(FeatureFlags.key))).scalars()
        return [self._to_entity(row) for row in rows]

    async def get_flag(self, key: str) -> FeatureFlagState | None:
        result = await self.session.execute(select(FeatureFlags).where(FeatureFlags.key == key))
        flag = result.scalar_one_or_none()
        return self._to_entity(flag) if flag is not None else None

    async def create_flag(self, values: dict[str, object]) -> FeatureFlagState:
        return self._to_entity(await super().create(values))

    async def update_flag(self, key: str, values: dict[str, object]) -> FeatureFlagState:
        flag = await self.session.scalar(select(FeatureFlags).where(FeatureFlags.key == key))
        if flag is None:
            return await self.create_flag({"key": key, **values})
        return self._to_entity(await super().update(flag, values))
