"""
The access policy: which operations (FastAPI `operation_id`s) each role may call in one service.

Source of truth is the central access document (`config/access-control.json`), shared by every
service and shaped like the future access tables:

    {
      "privileges": {
        "<privilegeKey>": {"name": "...", "description": "...", "endpoints": {"<service>": ["<operationId>", ...]}}
      },
      "roles": {"<role>": ["<privilegeKey>", ...]}
    }

Each service keeps only its own entries (`AccessPolicy.for_service`). Every caller, signed in or
not, implicitly holds the `anonymous` role, so public endpoints are granted to that role.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ANONYMOUS_ROLE = "anonymous"


class AccessConfigError(ValueError):
    """The access document is missing, malformed or inconsistent. Services refuse to start with it."""


class _Privilege(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = ""
    endpoints: dict[str, list[str]]


class AccessDocument(BaseModel):
    """The parsed central access document (all services)."""

    model_config = ConfigDict(extra="forbid")

    privileges: dict[str, _Privilege]
    roles: dict[str, list[str]]

    @model_validator(mode="after")
    def _roles_reference_known_privileges(self) -> "AccessDocument":
        unknown = sorted(
            f"{role} -> {key}" for role, keys in self.roles.items() for key in keys if key not in self.privileges
        )
        if unknown:
            raise ValueError(f"Roles reference unknown privileges: {', '.join(unknown)}")
        return self


@dataclass(frozen=True, slots=True)
class AccessSubject:
    """Who is calling, as far as access control cares: signed in or not, and with which roles."""

    authenticated: bool
    roles: frozenset[str] = frozenset()
    # Why credentials that were sent got rejected; raised if the endpoint is not public.
    authentication_error: Exception | None = None

    @classmethod
    def anonymous(cls, error: Exception | None = None) -> "AccessSubject":
        return cls(authenticated=False, authentication_error=error)

    @classmethod
    def signed_in(cls, roles: Iterable[str]) -> "AccessSubject":
        return cls(authenticated=True, roles=frozenset(roles))


@dataclass(frozen=True, slots=True)
class AccessPolicy:
    """Role -> operationIds for one service."""

    service: str
    role_operations: Mapping[str, frozenset[str]] = field(default_factory=dict)
    # Operations every signed-in caller may call regardless of role (used by test lookups).
    any_authenticated: frozenset[str] = frozenset()

    def operations_for(self, subject: AccessSubject) -> frozenset[str]:
        granted = set(self.role_operations.get(ANONYMOUS_ROLE, frozenset()))
        if subject.authenticated:
            granted |= self.any_authenticated
            for role in subject.roles:
                granted |= self.role_operations.get(role, frozenset())
        return frozenset(granted)

    @property
    def operations(self) -> frozenset[str]:
        """Every operationId this policy mentions (for validation against the service's routes)."""
        mentioned: set[str] = set(self.any_authenticated)
        for operations in self.role_operations.values():
            mentioned |= operations
        return frozenset(mentioned)

    @classmethod
    def for_service(cls, document: AccessDocument, service: str) -> "AccessPolicy":
        role_operations = {
            role: frozenset(
                operation for key in keys for operation in document.privileges[key].endpoints.get(service, [])
            )
            for role, keys in document.roles.items()
        }
        return cls(service=service, role_operations=role_operations)


def parse_access_document(data: Any) -> AccessDocument:
    try:
        return AccessDocument.model_validate(data)
    except ValidationError as e:
        raise AccessConfigError(f"Invalid access document: {e}") from e
