"""Resolves the caller from `Authorization: Bearer <access token>` issued by core-api."""

from typing import Annotated

from fastapi import Depends, Header
from platform_kit.auth import Principal, TokenVerifier, bearer_token

from app.config import config

_verifier = TokenVerifier(secret_key=config.JWT_SECRET_KEY.get_secret_value(), algorithm=config.JWT_ALGORITHM)


async def get_principal(authorization: Annotated[str | None, Header()] = None) -> Principal:
    return _verifier.verify(bearer_token(authorization))


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
