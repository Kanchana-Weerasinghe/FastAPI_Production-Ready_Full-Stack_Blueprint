"""
Who is calling, from `Authorization: Bearer <access token>` issued by the identity service (verified
offline by `platform_kit.auth`). Same names as the identity service's auth dependencies:

- `get_access_subject`: the caller as the central access check sees it (`require_access()` on every
  router). Never raises for bad credentials, so public endpoints keep working.
- `CurrentUserDep`: the signed-in caller (`Principal`: `user_id`, `role`, `token`) for routes that need
  the user ID, e.g. to pass the acting user to a use case.
- `roles_of(...)`: the single place that maps a caller to the roles named in config/access-control.json.

Ownership ("only the owner may ...") is a business rule and stays in the use cases. Never check a role
in code.
"""

from typing import Annotated

from fastapi import Depends, Header
from platform_kit.access import AccessSubject
from platform_kit.auth import Principal, TokenVerifier, bearer_token
from platform_kit.errors import AuthenticationError

from app.core.config import config

_verifier = TokenVerifier(secret_key=config.JWT_SECRET_KEY.get_secret_value(), algorithm=config.JWT_ALGORITHM)


def roles_of(principal: Principal) -> frozenset[str]:
    """The roles a caller holds, as named in the access document (today: the token's `role` claim)."""
    return frozenset({principal.role})


async def get_current_user(authorization: Annotated[str | None, Header()] = None) -> Principal:
    return _verifier.verify(bearer_token(authorization))


async def get_access_subject(authorization: Annotated[str | None, Header()] = None) -> AccessSubject:
    try:
        principal = _verifier.verify(bearer_token(authorization))
    except AuthenticationError as e:
        return AccessSubject.anonymous(e)
    return AccessSubject.signed_in(roles_of(principal))


CurrentUserDep = Annotated[Principal, Depends(get_current_user)]
