"""
Caller identity for domain services.

Access tokens are issued by core-api (the identity service) and verified here offline, so a domain
service never calls core-api per request. Services accept them only as `Authorization: Bearer`:
callers are backends-for-frontends, other services and the API gateway, so cookie/CSRF handling
stays at the edge. Tokens are short-lived (15 minutes); revocation takes effect at expiry.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jwt

from platform_kit.errors import AuthenticationError, PermissionDeniedError

ACCESS_TOKEN_TYPE = "access"
ADMIN_ROLE = "admin"


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller, as stated by a verified access token."""

    user_id: UUID
    role: str
    token: str

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN_ROLE

    def require_role(self, *roles: str) -> None:
        if self.role not in roles and not self.is_admin:
            raise PermissionDeniedError("You do not have permission to perform this action")


class TokenVerifier:
    """Verifies access tokens signed by the identity service."""

    def __init__(self, *, secret_key: str, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    def verify(self, token: str) -> Principal:
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["exp", "iat", "sub", "type"]},
            )
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Access token expired", code="token_expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError("Invalid access token") from e
        if claims.get("type") != ACCESS_TOKEN_TYPE:
            raise AuthenticationError("Invalid access token")
        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as e:
            raise AuthenticationError("Invalid access token") from e
        return Principal(user_id=user_id, role=str(claims.get("role", "user")), token=token)


def bearer_token(authorization: str | None) -> str:
    """Extracts the token from an `Authorization: Bearer <token>` header value."""
    if not authorization:
        raise AuthenticationError("Missing bearer token")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Missing bearer token")
    return token.strip()
