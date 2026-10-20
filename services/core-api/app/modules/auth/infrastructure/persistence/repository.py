from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.entities import OneTimeToken, RefreshToken
from app.modules.auth.infrastructure.persistence.models import OneTimeTokens, RefreshTokens


class RefreshTokenRepository:
    """Persistence for refresh tokens (hashes only)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_entity(token: RefreshTokens) -> RefreshToken:
        return RefreshToken(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            family_id=token.family_id,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            replaced_by_id=token.replaced_by_id,
            user_agent=token.user_agent,
            ip_address=token.ip_address,
            created_by=token.created_by,
            updated_by=token.updated_by,
        )

    async def add(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokens(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            family_id=token.family_id,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            replaced_by_id=token.replaced_by_id,
            user_agent=token.user_agent,
            ip_address=token.ip_address,
            created_by=token.created_by,
            updated_by=token.updated_by,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(select(RefreshTokens).where(RefreshTokens.token_hash == token_hash))
        token = result.scalar_one_or_none()
        return self._to_entity(token) if token is not None else None

    async def rotate(self, token_id: UUID, replacement_id: UUID, at: datetime) -> None:
        await self.session.execute(
            update(RefreshTokens)
            .where(RefreshTokens.id == token_id, RefreshTokens.revoked_at.is_(None))
            .values(revoked_at=at, replaced_by_id=replacement_id)
        )

    async def revoke_family(self, family_id: UUID) -> None:
        await self.session.execute(
            update(RefreshTokens)
            .where(RefreshTokens.family_id == family_id, RefreshTokens.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            update(RefreshTokens)
            .where(RefreshTokens.user_id == user_id, RefreshTokens.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )


class OneTimeTokenRepository:
    """Persistence for single-use email-verification / password-reset tokens (hashes only)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_entity(token: OneTimeTokens) -> OneTimeToken:
        return OneTimeToken(
            id=token.id,
            user_id=token.user_id,
            purpose=token.purpose,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
            created_by=token.created_by,
            updated_by=token.updated_by,
        )

    async def add(self, token: OneTimeToken) -> OneTimeToken:
        model = OneTimeTokens(
            id=token.id,
            user_id=token.user_id,
            purpose=token.purpose,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
            created_by=token.created_by,
            updated_by=token.updated_by,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def get_usable(self, token_hash: str, purpose: str) -> OneTimeToken | None:
        result = await self.session.execute(
            select(OneTimeTokens).where(
                OneTimeTokens.token_hash == token_hash,
                OneTimeTokens.purpose == purpose,
                OneTimeTokens.used_at.is_(None),
                OneTimeTokens.expires_at > datetime.now(UTC),
            )
        )
        token = result.scalar_one_or_none()
        return self._to_entity(token) if token is not None else None

    async def mark_used(self, token_id: UUID, at: datetime) -> None:
        await self.session.execute(
            update(OneTimeTokens)
            .where(OneTimeTokens.id == token_id, OneTimeTokens.used_at.is_(None))
            .values(used_at=at)
        )

    async def invalidate_for_user(self, user_id: UUID, purpose: str) -> None:
        """Marks all outstanding tokens of a purpose as used (only the newest link should work)."""
        await self.session.execute(
            update(OneTimeTokens)
            .where(OneTimeTokens.user_id == user_id, OneTimeTokens.purpose == purpose, OneTimeTokens.used_at.is_(None))
            .values(used_at=datetime.now(UTC))
        )
