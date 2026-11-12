r'''
The demo module (a working example aggregate, from domain rules to a live API) and its first migration.
Used by scripts/new_service_demo.py on top of templates_base.BASE_FILES. Placeholders are `{{name}}` tokens.
'''

# ---------------------------------------------------------------------------------------------
# Only when the service is created: the first module's migration (later modules: autogenerate).
# ---------------------------------------------------------------------------------------------

INITIAL_FILES: dict[str, str] = {
    "migrations/versions/{{revision}}_create_{{entities}}.py": r'''"""create {{entities}}

Revision ID: {{revision}}
Revises:
Create Date: {{create_date}}

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.config import config

# revision identifiers, used by Alembic.
revision: str = "{{revision}}"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = config.DB_SCHEMA


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "{{entities}}",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("archived_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_{{entities}}")),
        schema=SCHEMA,
    )
    op.create_index("ix_{{entities}}_owner_status", "{{entities}}", ["owner_id", "status"], unique=False, schema=SCHEMA)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_{{entities}}_owner_status", table_name="{{entities}}", schema=SCHEMA)
    op.drop_table("{{entities}}", schema=SCHEMA)
''',
}

# ---------------------------------------------------------------------------------------------
# One module (starter aggregate)
# ---------------------------------------------------------------------------------------------

INTEGRATION_TEST = r'''"""
HTTP behaviour of /v1/{{entities_kebab}}: the real app, database and access document.

Most tests use the real config/access-control.json (role "user" holds the module's privilege);
`deny_access()` / `grant_access(...)` replace it for one test while the real check still runs.
"""

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from tests.integrations.conftest import isolated_app_transaction  # noqa: F401  (autouse: per-test rollback)

BASE = "/v1/{{entities_kebab}}"
ClientFactory = Callable[..., Awaitable[AsyncClient]]


async def _create(http: AsyncClient, name: str = "Starter") -> dict[str, Any]:
    response = await http.post(f"{BASE}/", json={"name": name, "description": "First one"})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_sign_in_is_required(client: ClientFactory) -> None:
    http = await client()
    response = await http.get(f"{BASE}/")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_caller_without_a_grant_is_refused(client: ClientFactory, deny_access: Callable[[], None]) -> None:
    deny_access()
    http = await client(user_id=uuid4())
    response = await http.get(f"{BASE}/")
    assert response.status_code == 403
    assert response.json()["code"] == "access_denied"


async def test_a_grant_opens_exactly_that_operation(
    client: ClientFactory, grant_access: Callable[..., None]
) -> None:
    grant_access("list{{Entities}}")
    http = await client(user_id=uuid4())
    assert (await http.get(f"{BASE}/")).status_code == 200
    assert (await http.post(f"{BASE}/", json={"name": "Not granted"})).status_code == 403


async def test_owner_lifecycle(client: ClientFactory) -> None:
    http = await client(user_id=uuid4())
    created = await http.post(f"{BASE}/", json={"name": "Starter", "description": "First"})
    assert created.status_code == 201, created.text
    {{entity}} = created.json()
    assert created.headers["Location"] == f"{BASE}/{ {{entity}}['id'] }"
    assert created.headers["ETag"] == 'W/"1"'
    url = f"{BASE}/{ {{entity}}['id'] }"

    fetched = await http.get(url)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Starter"

    renamed = await http.patch(url, json={"name": "Renamed"}, headers={"If-Match": 'W/"1"'})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Renamed"
    assert renamed.json()["description"] == "First"
    assert renamed.headers["ETag"] == 'W/"2"'

    archived = await http.post(f"{url}:archive", headers={"If-Match": 'W/"2"'})
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    blocked = await http.patch(url, json={"name": "Not allowed"})
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "invalid_status_transition"

    restored = await http.post(f"{url}:restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    deleted = await http.delete(url, headers={"If-Match": restored.headers["ETag"]})
    assert deleted.status_code == 204
    gone = await http.get(url)
    assert gone.status_code == 404
    assert gone.json()["code"] == "{{entity}}_not_found"


async def test_stale_if_match_is_rejected(client: ClientFactory) -> None:
    http = await client(user_id=uuid4())
    {{entity}} = await _create(http)
    response = await http.post(f"{BASE}/{ {{entity}}['id'] }:archive", headers={"If-Match": 'W/"99"'})
    assert response.status_code == 412


async def test_other_owners_see_nothing(client: ClientFactory) -> None:
    {{entity}} = await _create(await client(user_id=uuid4()))
    stranger = await client(user_id=uuid4())
    assert (await stranger.get(f"{BASE}/{ {{entity}}['id'] }")).status_code == 404
    listed = await stranger.get(f"{BASE}/")
    assert listed.json()["pageInfo"]["totalCount"] == 0


async def test_list_filters_and_paginates(client: ClientFactory) -> None:
    http = await client(user_id=uuid4())
    await _create(http, "First")
    second = await _create(http, "Second")
    await http.post(f"{BASE}/{second['id']}:archive")

    page = await http.get(f"{BASE}/", params={"pageSize": 1})
    assert page.status_code == 200
    assert len(page.json()["items"]) == 1
    assert page.json()["pageInfo"]["totalCount"] == 2

    active = await http.get(f"{BASE}/", params={"status": "active"})
    assert [x["name"] for x in active.json()["items"]] == ["First"]


async def test_domain_validation_is_a_problem_response(client: ClientFactory) -> None:
    http = await client(user_id=uuid4())
    response = await http.post(f"{BASE}/", json={"name": "ab"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_{{entity}}_name"
'''


_M = "app/modules/{{entities}}"

MODULE_FILES: dict[str, str] = {
    f"{_M}/__init__.py": "",
    f"{_M}/domain/__init__.py": "",
    f"{_M}/domain/exceptions.py": r'''"""
Named business errors of the {{entities_words}} domain.

They extend the framework-agnostic `platform_kit.errors` types, so each rule violation has a stable
`code` and maps to an RFC 9457 response without the domain knowing about HTTP.
"""

from platform_kit.errors import ConflictError, NotFoundError, UnprocessableError


class Invalid{{Entity}}Name(UnprocessableError):
    code = "invalid_{{entity}}_name"


class InvalidDescription(UnprocessableError):
    code = "invalid_{{entity}}_description"


class InvalidStatusTransition(ConflictError):
    code = "invalid_status_transition"


class {{Entity}}LimitReached(ConflictError):
    code = "{{entity}}_limit_reached"


class {{Entity}}NotFound(NotFoundError):
    code = "{{entity}}_not_found"

    def __init__(self) -> None:
        super().__init__("{{Entity_words}} not found")


class ConcurrentModification(ConflictError):
    code = "concurrent_modification"

    def __init__(self) -> None:
        super().__init__("The {{entity_words}} was changed by another request; reload it and retry")
''',
    f"{_M}/domain/value_objects.py": r'''"""Small immutable values that validate themselves; an invalid value can never be constructed."""

from dataclasses import dataclass
from enum import StrEnum

from app.modules.{{entities}}.domain.exceptions import Invalid{{Entity}}Name, InvalidDescription

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 2000


class {{Entity}}Status(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class {{Entity}}Name:
    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split())
        if not NAME_MIN_LENGTH <= len(normalized) <= NAME_MAX_LENGTH:
            raise Invalid{{Entity}}Name(f"Name must contain {NAME_MIN_LENGTH}-{NAME_MAX_LENGTH} characters")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class Description:
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        if not cleaned or len(cleaned) > DESCRIPTION_MAX_LENGTH:
            raise InvalidDescription(f"Description must contain 1-{DESCRIPTION_MAX_LENGTH} characters")
        object.__setattr__(self, "value", cleaned)

    @classmethod
    def optional(cls, raw: str | None) -> "Description | None":
        """No text (None or only whitespace) means no description."""
        return None if raw is None or not raw.strip() else cls(raw)
''',
    f"{_M}/domain/events.py": r'''"""
Domain events: facts other domains may react to.

The entity records them; the use case hands them to the `EventPublisher` port after a successful
commit. Event names and fields are part of this service's public contract, like its API.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    {{entity}}_id: UUID
    occurred_at: datetime

    @property
    def name(self) -> str:
        return type(self).__name__


@dataclass(frozen=True, slots=True)
class {{Entity}}Created(DomainEvent):
    owner_id: UUID


@dataclass(frozen=True, slots=True)
class {{Entity}}Archived(DomainEvent):
    pass


@dataclass(frozen=True, slots=True)
class {{Entity}}Restored(DomainEvent):
    pass


@dataclass(frozen=True, slots=True)
class {{Entity}}Deleted(DomainEvent):
    pass
''',
    f"{_M}/domain/policies.py": r'''"""
Policies: business decisions that need facts the entity does not hold.

The use case fetches the facts (through ports) and passes them in; the policy stays a pure, easily
tested function. A database constraint or lock is still needed where races matter.
"""

from app.modules.{{entities}}.domain.exceptions import {{Entity}}LimitReached


def ensure_owner_can_create(*, active: int, limit: int) -> None:
    """An owner may have at most `limit` active {{entities_words}}."""
    if active >= limit:
        raise {{Entity}}LimitReached(f"You already have {active} active {{entities_words}} (limit {limit})")
''',
    f"{_M}/domain/entities.py": r'''"""
The {{Entity}} aggregate (generated starter: replace its fields and rules with the real ones).

    ACTIVE --archive--> ARCHIVED --restore--> ACTIVE

State only changes through methods, so every rule holds no matter which use case or API version
triggers the change. Plain Python: no FastAPI, Pydantic or SQLAlchemy.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.modules.{{entities}}.domain.events import (
    DomainEvent,
    {{Entity}}Archived,
    {{Entity}}Created,
    {{Entity}}Deleted,
    {{Entity}}Restored,
)
from app.modules.{{entities}}.domain.exceptions import InvalidStatusTransition
from app.modules.{{entities}}.domain.value_objects import Description, {{Entity}}Name, {{Entity}}Status


@dataclass(slots=True)
class {{Entity}}:
    # --- Properties ---
    id: UUID
    owner_id: UUID  # the user who created it (an ID from the identity service; never a foreign key)
    name: {{Entity}}Name
    description: Description | None
    status: {{Entity}}Status
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    version: int = 0  # optimistic-locking version; 0 = not persisted yet
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    # --- Creation ---
    @classmethod
    def create(
        cls, *, owner_id: UUID, name: {{Entity}}Name, description: Description | None, at: datetime
    ) -> "{{Entity}}":
        {{entity}} = cls(
            id=uuid4(),
            owner_id=owner_id,
            name=name,
            description=description,
            status={{Entity}}Status.ACTIVE,
            created_at=at,
            updated_at=at,
        )
        {{entity}}._record({{Entity}}Created({{entity}}.id, at, owner_id=owner_id))
        return {{entity}}

    # --- Behaviours ---
    def rename(self, name: {{Entity}}Name, *, at: datetime) -> None:
        self._require_active("rename")
        self.name = name
        self.updated_at = at

    def describe(self, description: Description | None, *, at: datetime) -> None:
        self._require_active("change")
        self.description = description
        self.updated_at = at

    def archive(self, *, at: datetime) -> None:
        self._require_active("archive")
        self.status = {{Entity}}Status.ARCHIVED
        self.archived_at = at
        self.updated_at = at
        self._record({{Entity}}Archived(self.id, at))

    def restore(self, *, at: datetime) -> None:
        if self.status is not {{Entity}}Status.ARCHIVED:
            raise InvalidStatusTransition(f"Only an archived {{entity_words}} can be restored, not a {self.status.value} one")
        self.status = {{Entity}}Status.ACTIVE
        self.archived_at = None
        self.updated_at = at
        self._record({{Entity}}Restored(self.id, at))

    def delete(self, *, at: datetime) -> None:
        """Records the deletion; the repository removes the row."""
        self._record({{Entity}}Deleted(self.id, at))

    # --- Business questions ---
    @property
    def is_active(self) -> bool:
        return self.status is {{Entity}}Status.ACTIVE

    def is_owned_by(self, user_id: UUID) -> bool:
        return self.owner_id == user_id

    # --- Domain events ---
    def pull_events(self) -> list[DomainEvent]:
        """Returns and clears the events recorded since the last call."""
        events, self._events = self._events, []
        return events

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def _require_active(self, action: str) -> None:
        if not self.is_active:
            raise InvalidStatusTransition(f"Cannot {action} an {self.status.value} {{entity_words}}")
''',
    f"{_M}/application/__init__.py": "",
    f"{_M}/application/ports/__init__.py": r'''from app.modules.{{entities}}.application.ports.event_publisher import EventPublisher
from app.modules.{{entities}}.application.ports.{{entity}}_repository import {{Entity}}Page, {{Entity}}Query, {{Entity}}Repository

__all__ = ["EventPublisher", "{{Entity}}Page", "{{Entity}}Query", "{{Entity}}Repository"]
''',
    f"{_M}/application/ports/{{{{entity}}}}_repository.py": r'''"""
Port: what the use cases need from storage.

An abstract base class, so implementations declare it explicitly (`class X({{Entity}}Repository)`) and
Python refuses to create one that forgets a method. Implementations: `SqlAlchemy{{Entity}}Repository`
(infrastructure) and `Fake{{Entity}}Repository` (tests).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.modules.{{entities}}.domain.entities import {{Entity}}
from app.modules.{{entities}}.domain.value_objects import {{Entity}}Status


@dataclass(frozen=True, slots=True)
class {{Entity}}Query:
    owner_id: UUID
    status: {{Entity}}Status | None
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class {{Entity}}Page:
    items: list[{{Entity}}]
    total: int


class {{Entity}}Repository(ABC):
    @abstractmethod
    async def add(self, {{entity}}: {{Entity}}) -> None: ...

    @abstractmethod
    async def get(self, {{entity}}_id: UUID) -> {{Entity}}:
        """Raises `{{Entity}}NotFound` when it does not exist."""

    @abstractmethod
    async def save(self, {{entity}}: {{Entity}}) -> None:
        """Persists a change; raises `ConcurrentModification` if it changed since it was loaded."""

    @abstractmethod
    async def remove(self, {{entity}}: {{Entity}}) -> None:
        """Deletes it; raises `ConcurrentModification` if it changed since it was loaded."""

    @abstractmethod
    async def find(self, query: {{Entity}}Query) -> {{Entity}}Page: ...

    @abstractmethod
    async def count_active(self, owner_id: UUID) -> int: ...
''',
    f"{_M}/application/ports/event_publisher.py": r'''"""How domain events leave the service. Today a logging adapter; later an outbox + message broker."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.modules.{{entities}}.domain.events import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        """Publishes the events only if the current transaction commits."""
''',
    f"{_M}/application/use_cases/__init__.py": r'''from app.modules.{{entities}}.application.use_cases.{{entity}}_use_cases import (
    Create{{Entity}}Command,
    Update{{Entity}}Command,
    {{Entity}}UseCases,
)

__all__ = ["Create{{Entity}}Command", "Update{{Entity}}Command", "{{Entity}}UseCases"]
''',
    f"{_M}/application/use_cases/{{{{entity}}}}_use_cases.py": r'''"""
Use cases of the {{Entity}} aggregate: validate input with value objects, apply policies, change the
aggregate through its methods, persist through the port and publish events after commit.

They take transport-neutral values (commands, IDs) and return domain records; the router maps HTTP
to and from them. Ownership is a business rule: for anyone but the owner a {{entity_words}} does not
exist (404, no ID probing). Who may call an operation at all is the central access check's job.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from platform_kit.errors import PreconditionFailedError

from app.modules.{{entities}}.application.ports import EventPublisher, {{Entity}}Page, {{Entity}}Query, {{Entity}}Repository
from app.modules.{{entities}}.domain.entities import {{Entity}}
from app.modules.{{entities}}.domain.exceptions import {{Entity}}NotFound
from app.modules.{{entities}}.domain.policies import ensure_owner_can_create
from app.modules.{{entities}}.domain.value_objects import Description, {{Entity}}Name, {{Entity}}Status

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Create{{Entity}}Command:
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class Update{{Entity}}Command:
    """Only the fields that were sent change. `change_description` tells "clear it" from "not sent"."""

    name: str | None = None
    description: str | None = None
    change_description: bool = False


class {{Entity}}UseCases:
    def __init__(
        self, repository: {{Entity}}Repository, events: EventPublisher, *, max_per_owner: int, clock: Clock = utc_now
    ) -> None:
        self.repository = repository
        self.events = events
        self.max_per_owner = max_per_owner
        self.clock = clock

    async def create(self, command: Create{{Entity}}Command, actor_id: UUID) -> {{Entity}}:
        # 1. Value objects validate the input (invariants).
        name = {{Entity}}Name(command.name)
        description = Description.optional(command.description)
        # 2. Fetch the facts the policy needs, then apply it.
        ensure_owner_can_create(active=await self.repository.count_active(actor_id), limit=self.max_per_owner)
        # 3. Create the aggregate, persist it, publish its events after commit.
        {{entity}} = {{Entity}}.create(owner_id=actor_id, name=name, description=description, at=self.clock())
        await self.repository.add({{entity}})
        self.events.publish_after_commit({{entity}}.pull_events())
        return {{entity}}

    async def get(self, {{entity}}_id: UUID, actor_id: UUID) -> {{Entity}}:
        return await self._load_owned({{entity}}_id, actor_id)

    async def search(
        self, actor_id: UUID, *, status: {{Entity}}Status | None, offset: int, limit: int
    ) -> {{Entity}}Page:
        return await self.repository.find({{Entity}}Query(owner_id=actor_id, status=status, offset=offset, limit=limit))

    async def update(
        self,
        {{entity}}_id: UUID,
        command: Update{{Entity}}Command,
        actor_id: UUID,
        *,
        expected_version: int | None = None,
    ) -> {{Entity}}:
        {{entity}} = await self._load_owned({{entity}}_id, actor_id, expected_version=expected_version)
        now = self.clock()
        if command.name is not None:
            {{entity}}.rename({{Entity}}Name(command.name), at=now)
        if command.change_description:
            {{entity}}.describe(Description.optional(command.description), at=now)
        return await self._save({{entity}})

    async def archive(self, {{entity}}_id: UUID, actor_id: UUID, *, expected_version: int | None = None) -> {{Entity}}:
        {{entity}} = await self._load_owned({{entity}}_id, actor_id, expected_version=expected_version)
        {{entity}}.archive(at=self.clock())
        return await self._save({{entity}})

    async def restore(self, {{entity}}_id: UUID, actor_id: UUID, *, expected_version: int | None = None) -> {{Entity}}:
        {{entity}} = await self._load_owned({{entity}}_id, actor_id, expected_version=expected_version)
        {{entity}}.restore(at=self.clock())
        return await self._save({{entity}})

    async def delete(self, {{entity}}_id: UUID, actor_id: UUID, *, expected_version: int | None = None) -> None:
        {{entity}} = await self._load_owned({{entity}}_id, actor_id, expected_version=expected_version)
        {{entity}}.delete(at=self.clock())
        await self.repository.remove({{entity}})
        self.events.publish_after_commit({{entity}}.pull_events())

    # --- Shared steps ---
    async def _load_owned(
        self, {{entity}}_id: UUID, actor_id: UUID, *, expected_version: int | None = None
    ) -> {{Entity}}:
        {{entity}} = await self.repository.get({{entity}}_id)
        if not {{entity}}.is_owned_by(actor_id):
            raise {{Entity}}NotFound()
        if expected_version is not None and {{entity}}.version != expected_version:
            raise PreconditionFailedError(
                "The {{entity_words}} was modified by someone else; reload it and retry",
                extra={"current_etag": f'W/"{ {{entity}}.version }"'},
            )
        return {{entity}}

    async def _save(self, {{entity}}: {{Entity}}) -> {{Entity}}:
        await self.repository.save({{entity}})
        self.events.publish_after_commit({{entity}}.pull_events())
        return {{entity}}
''',
    f"{_M}/infrastructure/__init__.py": "",
    f"{_M}/infrastructure/logging_event_publisher.py": r'''"""
`EventPublisher` adapter that writes events to the structured log after commit.

It keeps the service self-contained until a message broker exists. To let other domains consume the
events, replace it with an outbox adapter (store events in the same transaction, relay them to the
broker) and wire it in `container.py`; the use cases do not change.
"""

from collections.abc import Sequence
from dataclasses import asdict

from platform_kit.database import UnitOfWork
from platform_kit.logging import logger

from app.modules.{{entities}}.application.ports import EventPublisher
from app.modules.{{entities}}.domain.events import DomainEvent


class LoggingEventPublisher(EventPublisher):
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        if events:
            self.uow.after_commit(self._log, list(events))

    @staticmethod
    async def _log(events: list[DomainEvent]) -> None:
        for event in events:
            payload = {k: str(v) for k, v in asdict(event).items()}
            logger.info("domain_event_published", event_name=event.name, **payload)
''',
    f"{_M}/infrastructure/persistence/__init__.py": "",
    f"{_M}/infrastructure/persistence/models.py": r'''from datetime import datetime
from uuid import UUID

from platform_kit.persistence import AuditColumnsMixin
from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class {{Entity}}Model(AuditColumnsMixin, Base):
    """Row shape of the {{Entity}} aggregate. Only the repository uses this class."""

    __tablename__ = "{{entities}}"
    __table_args__ = (Index("ix_{{entities}}_owner_status", "owner_id", "status"),)

    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)  # identity service user ID, no FK
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
''',
    f"{_M}/infrastructure/persistence/sqlalchemy_{{{{entity}}}}_repository.py": r'''"""SQLAlchemy implementation of the `{{Entity}}Repository` port: maps rows <-> the {{Entity}} aggregate."""

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.{{entities}}.application.ports import {{Entity}}Page, {{Entity}}Query, {{Entity}}Repository
from app.modules.{{entities}}.domain.entities import {{Entity}}
from app.modules.{{entities}}.domain.exceptions import ConcurrentModification, {{Entity}}NotFound
from app.modules.{{entities}}.domain.value_objects import Description, {{Entity}}Name, {{Entity}}Status
from app.modules.{{entities}}.infrastructure.persistence.models import {{Entity}}Model


class SqlAlchemy{{Entity}}Repository({{Entity}}Repository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, {{entity}}: {{Entity}}) -> None:
        row = {{Entity}}Model(id={{entity}}.id, version=1, **self._columns({{entity}}))
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        {{entity}}.version, {{entity}}.created_at, {{entity}}.updated_at = row.version, row.created_at, row.updated_at

    async def get(self, {{entity}}_id: UUID) -> {{Entity}}:
        row = await self.session.get({{Entity}}Model, {{entity}}_id, populate_existing=True)
        if row is None:
            raise {{Entity}}NotFound()
        return self._to_entity(row)

    async def save(self, {{entity}}: {{Entity}}) -> None:
        # Compare-and-set on `version`: a concurrent change makes the update match zero rows.
        result = await self.session.execute(
            update({{Entity}}Model)
            .where({{Entity}}Model.id == {{entity}}.id, {{Entity}}Model.version == {{entity}}.version)
            .values(**self._columns({{entity}}), version={{entity}}.version + 1, updated_at=func.now())
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise ConcurrentModification()
        {{entity}}.version += 1

    async def remove(self, {{entity}}: {{Entity}}) -> None:
        result = await self.session.execute(
            delete({{Entity}}Model).where({{Entity}}Model.id == {{entity}}.id, {{Entity}}Model.version == {{entity}}.version)
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise ConcurrentModification()

    async def find(self, query: {{Entity}}Query) -> {{Entity}}Page:
        conditions = [{{Entity}}Model.owner_id == query.owner_id]
        if query.status is not None:
            conditions.append({{Entity}}Model.status == query.status.value)
        total = await self.session.scalar(select(func.count()).select_from({{Entity}}Model).where(*conditions))
        rows = await self.session.scalars(
            select({{Entity}}Model)
            .where(*conditions)
            .order_by({{Entity}}Model.created_at.desc(), {{Entity}}Model.id)
            .offset(query.offset)
            .limit(query.limit)
        )
        return {{Entity}}Page(items=[self._to_entity(row) for row in rows], total=total or 0)

    async def count_active(self, owner_id: UUID) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from({{Entity}}Model)
            .where({{Entity}}Model.owner_id == owner_id, {{Entity}}Model.status == {{Entity}}Status.ACTIVE.value)
        )
        return count or 0

    @staticmethod
    def _columns({{entity}}: {{Entity}}) -> dict[str, object]:
        return {
            "owner_id": {{entity}}.owner_id,
            "name": {{entity}}.name.value,
            "description": {{entity}}.description.value if {{entity}}.description else None,
            "status": {{entity}}.status.value,
            "archived_at": {{entity}}.archived_at,
        }

    @staticmethod
    def _to_entity(row: {{Entity}}Model) -> {{Entity}}:
        return {{Entity}}(
            id=row.id,
            owner_id=row.owner_id,
            name={{Entity}}Name(row.name),
            description=Description.optional(row.description),
            status={{Entity}}Status(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
            archived_at=row.archived_at,
            version=row.version,
        )
''',
    f"{_M}/container.py": r'''from dependency_injector import containers, providers
from platform_kit.database import Database, UnitOfWork

from app.modules.{{entities}}.application.use_cases import {{Entity}}UseCases
from app.modules.{{entities}}.infrastructure.logging_event_publisher import LoggingEventPublisher
from app.modules.{{entities}}.infrastructure.persistence.sqlalchemy_{{entity}}_repository import SqlAlchemy{{Entity}}Repository


class {{Entities}}Container(containers.DeclarativeContainer):
    """Adapters are bound to ports here; use cases never construct their own dependencies."""

    db = providers.Dependency(instance_of=Database)
    uow = providers.Dependency(instance_of=UnitOfWork)
    max_per_owner = providers.Dependency(instance_of=int)

    repository = providers.Factory(SqlAlchemy{{Entity}}Repository, session=db.provided.scoped_session)
    events = providers.Factory(LoggingEventPublisher, uow=uow)

    use_cases = providers.Factory({{Entity}}UseCases, repository=repository, events=events, max_per_owner=max_per_owner)
''',
    f"{_M}/public.py": r'''"""
Public API of the {{entities}} module: the only file other modules of this service may import from
(re-exports only). Other *services* never import it: they call `/v1/{{entities_kebab}}` or consume
the published domain events.
"""

from app.modules.{{entities}}.application.use_cases import Create{{Entity}}Command, Update{{Entity}}Command, {{Entity}}UseCases
from app.modules.{{entities}}.domain.entities import {{Entity}}

__all__ = ["Create{{Entity}}Command", "Update{{Entity}}Command", "{{Entity}}", "{{Entity}}UseCases"]
''',
    f"{_M}/schemas.py": r'''"""HTTP request/response shapes. They validate transport input; business rules live in the domain."""

from datetime import datetime
from uuid import UUID

from platform_kit.http.pagination import CamelModel, PageInfo
from pydantic import Field

from app.modules.{{entities}}.domain.entities import {{Entity}}
from app.modules.{{entities}}.domain.value_objects import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH, {{Entity}}Status


class {{Entity}}Create(CamelModel):
    name: str = Field(..., min_length=1, max_length=NAME_MAX_LENGTH, examples=["My first {{entity_words}}"])
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)


class {{Entity}}Update(CamelModel):
    """Send only what changes; `"description": null` clears the description."""

    name: str | None = Field(None, min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)


class {{Entity}}Response(CamelModel):
    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    status: {{Entity}}Status
    created_at: datetime | None
    updated_at: datetime | None
    archived_at: datetime | None
    version: int

    @classmethod
    def from_entity(cls, {{entity}}: {{Entity}}) -> "{{Entity}}Response":
        return cls(
            id={{entity}}.id,
            owner_id={{entity}}.owner_id,
            name={{entity}}.name.value,
            description={{entity}}.description.value if {{entity}}.description else None,
            status={{entity}}.status,
            created_at={{entity}}.created_at,
            updated_at={{entity}}.updated_at,
            archived_at={{entity}}.archived_at,
            version={{entity}}.version,
        )


class {{Entity}}List(CamelModel):
    items: list[{{Entity}}Response]
    page_info: PageInfo
''',
    f"{_M}/router.py": r'''"""
HTTP boundary of the {{entities}} module: validate input, resolve the caller, call one use case, map
the result to a response schema. No business rules here.

Every route has a stable `operation_id` (never rename it), granted in `config/access-control.json`, and a
`rate_limit(...)`.
"""

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from platform_kit.access import require_access
from platform_kit.http.conditional import expected_version, set_etag
from platform_kit.http.pagination import PageInfo, Pagination

from app.core.security import rate_limit
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.{{entities}}.application.use_cases import Create{{Entity}}Command, Update{{Entity}}Command, {{Entity}}UseCases
from app.modules.{{entities}}.domain.value_objects import {{Entity}}Status
from app.modules.{{entities}}.schemas import {{Entity}}Create, {{Entity}}List, {{Entity}}Response, {{Entity}}Update

router = APIRouter(prefix="/{{entities_kebab}}", tags=["{{entities_kebab}}"], dependencies=[require_access()])

IfMatch = Annotated[str | None, Header(description='ETag from GET (e.g. W/"3"); 412 if it changed')]
USE_CASES = "{{entities}}.use_cases"
# Rate limits per client, like the identity service: reads are cheap, writes are limited harder.
READ_LIMIT = [rate_limit("200/minute")]
WRITE_LIMIT = [rate_limit("60/minute")]


def _respond(response: Response, body: {{Entity}}Response) -> {{Entity}}Response:
    set_etag(response, body.version)
    return body


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model={{Entity}}Response,
    dependencies=WRITE_LIMIT, operation_id="create{{Entity}}",
    summary="Create {{Entity_words}}",
)
@inject
async def create_{{entity}}(
    body: {{Entity}}Create,
    actor: CurrentUserDep,
    request: Request,
    response: Response,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> {{Entity}}Response:
    {{entity}} = await use_cases.create(Create{{Entity}}Command(name=body.name, description=body.description), actor.user_id)
    response.headers["Location"] = f"{request.url.path.rstrip('/')}/{ {{entity}}.id }"
    return _respond(response, {{Entity}}Response.from_entity({{entity}}))


@router.get("/", response_model={{Entity}}List, dependencies=READ_LIMIT, operation_id="list{{Entities}}", summary="List {{Entities_words}}")
@inject
async def list_{{entities}}(
    actor: CurrentUserDep,
    page: Pagination,
    status_filter: Annotated[{{Entity}}Status | None, Query(alias="status")] = None,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> {{Entity}}List:
    result = await use_cases.search(actor.user_id, status=status_filter, offset=page.offset, limit=page.page_size)
    return {{Entity}}List(
        items=[{{Entity}}Response.from_entity(x) for x in result.items],
        page_info=PageInfo(page=page.page, page_size=page.page_size, total_count=result.total),
    )


@router.get("/{{id}}", response_model={{Entity}}Response, dependencies=READ_LIMIT, operation_id="get{{Entity}}", summary="Get {{Entity_words}}")
@inject
async def get_{{entity}}(
    {{entity}}_id: UUID,
    actor: CurrentUserDep,
    response: Response,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> {{Entity}}Response:
    return _respond(response, {{Entity}}Response.from_entity(await use_cases.get({{entity}}_id, actor.user_id)))


@router.patch(
    "/{{id}}", response_model={{Entity}}Response, dependencies=WRITE_LIMIT, operation_id="update{{Entity}}", summary="Update {{Entity_words}}"
)
@inject
async def update_{{entity}}(
    {{entity}}_id: UUID,
    body: {{Entity}}Update,
    actor: CurrentUserDep,
    response: Response,
    if_match: IfMatch = None,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> {{Entity}}Response:
    command = Update{{Entity}}Command(
        name=body.name, description=body.description, change_description="description" in body.model_fields_set
    )
    {{entity}} = await use_cases.update({{entity}}_id, command, actor.user_id, expected_version=expected_version(if_match))
    return _respond(response, {{Entity}}Response.from_entity({{entity}}))


@router.post(
    "/{{id}}:archive",
    response_model={{Entity}}Response,
    dependencies=WRITE_LIMIT, operation_id="archive{{Entity}}",
    summary="Archive {{Entity_words}}",
)
@inject
async def archive_{{entity}}(
    {{entity}}_id: UUID,
    actor: CurrentUserDep,
    response: Response,
    if_match: IfMatch = None,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> {{Entity}}Response:
    {{entity}} = await use_cases.archive({{entity}}_id, actor.user_id, expected_version=expected_version(if_match))
    return _respond(response, {{Entity}}Response.from_entity({{entity}}))


@router.post(
    "/{{id}}:restore",
    response_model={{Entity}}Response,
    dependencies=WRITE_LIMIT, operation_id="restore{{Entity}}",
    summary="Restore {{Entity_words}}",
)
@inject
async def restore_{{entity}}(
    {{entity}}_id: UUID,
    actor: CurrentUserDep,
    response: Response,
    if_match: IfMatch = None,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> {{Entity}}Response:
    {{entity}} = await use_cases.restore({{entity}}_id, actor.user_id, expected_version=expected_version(if_match))
    return _respond(response, {{Entity}}Response.from_entity({{entity}}))


@router.delete(
    "/{{id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=WRITE_LIMIT, operation_id="delete{{Entity}}",
    summary="Delete {{Entity_words}}",
)
@inject
async def delete_{{entity}}(
    {{entity}}_id: UUID,
    actor: CurrentUserDep,
    if_match: IfMatch = None,
    use_cases: {{Entity}}UseCases = Depends(Provide[USE_CASES]),
) -> Response:
    await use_cases.delete({{entity}}_id, actor.user_id, expected_version=expected_version(if_match))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
''',
    # --- tests ---------------------------------------------------------------------------------
    "tests/unit/{{entities}}/__init__.py": "",
    "tests/unit/{{entities}}/fakes.py": r'''"""In-memory test doubles for the {{entities}} ports."""

from collections.abc import Sequence
from copy import deepcopy
from uuid import UUID

from app.modules.{{entities}}.application.ports import EventPublisher, {{Entity}}Page, {{Entity}}Query, {{Entity}}Repository
from app.modules.{{entities}}.domain.entities import {{Entity}}
from app.modules.{{entities}}.domain.events import DomainEvent
from app.modules.{{entities}}.domain.exceptions import ConcurrentModification, {{Entity}}NotFound
from app.modules.{{entities}}.domain.value_objects import {{Entity}}Status


class Fake{{Entity}}Repository({{Entity}}Repository):
    def __init__(self) -> None:
        self.rows: dict[UUID, {{Entity}}] = {}

    @staticmethod
    def _snapshot({{entity}}: {{Entity}}) -> {{Entity}}:
        """Stored state only, like a database row: pending events are not persisted."""
        stored = deepcopy({{entity}})
        stored.pull_events()
        return stored

    async def add(self, {{entity}}: {{Entity}}) -> None:
        {{entity}}.version = 1
        self.rows[{{entity}}.id] = self._snapshot({{entity}})

    async def get(self, {{entity}}_id: UUID) -> {{Entity}}:
        if {{entity}}_id not in self.rows:
            raise {{Entity}}NotFound()
        return deepcopy(self.rows[{{entity}}_id])

    async def save(self, {{entity}}: {{Entity}}) -> None:
        stored = self.rows.get({{entity}}.id)
        if stored is None or stored.version != {{entity}}.version:
            raise ConcurrentModification()
        {{entity}}.version += 1
        self.rows[{{entity}}.id] = self._snapshot({{entity}})

    async def remove(self, {{entity}}: {{Entity}}) -> None:
        stored = self.rows.get({{entity}}.id)
        if stored is None or stored.version != {{entity}}.version:
            raise ConcurrentModification()
        del self.rows[{{entity}}.id]

    async def find(self, query: {{Entity}}Query) -> {{Entity}}Page:
        matches = [
            x
            for x in self.rows.values()
            if x.owner_id == query.owner_id and (query.status is None or x.status is query.status)
        ]
        return {{Entity}}Page(items=matches[query.offset : query.offset + query.limit], total=len(matches))

    async def count_active(self, owner_id: UUID) -> int:
        return sum(1 for x in self.rows.values() if x.owner_id == owner_id and x.status is {{Entity}}Status.ACTIVE)


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    def publish_after_commit(self, events: Sequence[DomainEvent]) -> None:
        self.published.extend(events)

    @property
    def names(self) -> list[str]:
        return [event.name for event in self.published]
''',
    "tests/unit/{{entities}}/test_domain.py": r'''"""Domain rules of the {{Entity}} aggregate: value objects, behaviours, invariants and the policy."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.{{entities}}.domain.entities import {{Entity}}
from app.modules.{{entities}}.domain.exceptions import (
    Invalid{{Entity}}Name,
    InvalidDescription,
    InvalidStatusTransition,
    {{Entity}}LimitReached,
)
from app.modules.{{entities}}.domain.policies import ensure_owner_can_create
from app.modules.{{entities}}.domain.value_objects import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    Description,
    {{Entity}}Name,
    {{Entity}}Status,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _new() -> {{Entity}}:
    return {{Entity}}.create(owner_id=uuid4(), name={{Entity}}Name("Starter"), description=None, at=NOW)


class TestValueObjects:
    def test_name_collapses_whitespace(self) -> None:
        assert {{Entity}}Name("  My   first  ").value == "My first"

    @pytest.mark.parametrize("raw", ["ab", "   ", "x" * (NAME_MAX_LENGTH + 1)])
    def test_name_length_is_enforced(self, raw: str) -> None:
        with pytest.raises(Invalid{{Entity}}Name):
            {{Entity}}Name(raw)

    def test_blank_description_means_none(self) -> None:
        assert Description.optional("   ") is None
        assert Description.optional(None) is None

    def test_description_is_trimmed_and_limited(self) -> None:
        assert Description(" text ").value == "text"
        with pytest.raises(InvalidDescription):
            Description("x" * (DESCRIPTION_MAX_LENGTH + 1))


class TestLifecycle:
    def test_create_is_active_and_records_event(self) -> None:
        {{entity}} = _new()
        assert {{entity}}.status is {{Entity}}Status.ACTIVE
        assert [e.name for e in {{entity}}.pull_events()] == ["{{Entity}}Created"]
        assert {{entity}}.pull_events() == []

    def test_archive_then_restore(self) -> None:
        {{entity}} = _new()
        {{entity}}.archive(at=NOW)
        assert {{entity}}.status is {{Entity}}Status.ARCHIVED
        assert {{entity}}.archived_at == NOW
        {{entity}}.restore(at=NOW)
        assert {{entity}}.is_active
        assert {{entity}}.archived_at is None

    def test_archived_cannot_be_changed(self) -> None:
        {{entity}} = _new()
        {{entity}}.archive(at=NOW)
        with pytest.raises(InvalidStatusTransition):
            {{entity}}.rename({{Entity}}Name("New name"), at=NOW)
        with pytest.raises(InvalidStatusTransition):
            {{entity}}.archive(at=NOW)

    def test_only_archived_can_be_restored(self) -> None:
        with pytest.raises(InvalidStatusTransition):
            _new().restore(at=NOW)


class TestPolicy:
    def test_limit_reached(self) -> None:
        with pytest.raises({{Entity}}LimitReached):
            ensure_owner_can_create(active=3, limit=3)

    def test_below_limit(self) -> None:
        ensure_owner_can_create(active=2, limit=3)
''',
    "tests/unit/{{entities}}/test_use_cases.py": r'''"""Use cases orchestrate ports and domain rules; fakes replace the database and the event broker."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from platform_kit.errors import PreconditionFailedError

from app.modules.{{entities}}.application.use_cases import Create{{Entity}}Command, Update{{Entity}}Command, {{Entity}}UseCases
from app.modules.{{entities}}.domain.exceptions import Invalid{{Entity}}Name, {{Entity}}LimitReached, {{Entity}}NotFound
from app.modules.{{entities}}.domain.value_objects import {{Entity}}Status
from tests.unit.{{entities}}.fakes import FakeEventPublisher, Fake{{Entity}}Repository

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LIMIT = 2


@pytest.fixture
def repo() -> Fake{{Entity}}Repository:
    return Fake{{Entity}}Repository()


@pytest.fixture
def events() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def use_cases(repo: Fake{{Entity}}Repository, events: FakeEventPublisher) -> {{Entity}}UseCases:
    return {{Entity}}UseCases(repo, events, max_per_owner=LIMIT, clock=lambda: NOW)


@pytest.fixture
def owner() -> UUID:
    return uuid4()


async def test_create_persists_and_publishes(
    use_cases: {{Entity}}UseCases, repo: Fake{{Entity}}Repository, events: FakeEventPublisher, owner: UUID
) -> None:
    {{entity}} = await use_cases.create(Create{{Entity}}Command(name=" Starter ", description="Text"), owner)
    assert {{entity}}.id in repo.rows
    assert {{entity}}.name.value == "Starter"
    assert {{entity}}.version == 1
    assert events.names == ["{{Entity}}Created"]


async def test_create_validates_input(use_cases: {{Entity}}UseCases, owner: UUID) -> None:
    with pytest.raises(Invalid{{Entity}}Name):
        await use_cases.create(Create{{Entity}}Command(name="ab"), owner)


async def test_create_enforces_the_limit_per_owner(use_cases: {{Entity}}UseCases, owner: UUID) -> None:
    for i in range(LIMIT):
        await use_cases.create(Create{{Entity}}Command(name=f"Number {i}"), owner)
    with pytest.raises({{Entity}}LimitReached):
        await use_cases.create(Create{{Entity}}Command(name="One too many"), owner)
    # Another owner is not affected.
    await use_cases.create(Create{{Entity}}Command(name="Someone else"), uuid4())


async def test_strangers_get_not_found(use_cases: {{Entity}}UseCases, owner: UUID) -> None:
    {{entity}} = await use_cases.create(Create{{Entity}}Command(name="Private"), owner)
    with pytest.raises({{Entity}}NotFound):
        await use_cases.get({{entity}}.id, uuid4())


async def test_update_changes_only_sent_fields(use_cases: {{Entity}}UseCases, owner: UUID) -> None:
    {{entity}} = await use_cases.create(Create{{Entity}}Command(name="Before", description="Keep me"), owner)
    updated = await use_cases.update({{entity}}.id, Update{{Entity}}Command(name="After"), owner)
    assert (updated.name.value, updated.description and updated.description.value) == ("After", "Keep me")
    cleared = await use_cases.update({{entity}}.id, Update{{Entity}}Command(change_description=True), owner)
    assert cleared.description is None
    assert cleared.version == 3


async def test_stale_version_is_rejected(use_cases: {{Entity}}UseCases, owner: UUID) -> None:
    {{entity}} = await use_cases.create(Create{{Entity}}Command(name="Versioned"), owner)
    with pytest.raises(PreconditionFailedError):
        await use_cases.archive({{entity}}.id, owner, expected_version={{entity}}.version + 1)


async def test_archive_restore_delete(
    use_cases: {{Entity}}UseCases, repo: Fake{{Entity}}Repository, events: FakeEventPublisher, owner: UUID
) -> None:
    {{entity}} = await use_cases.create(Create{{Entity}}Command(name="Lifecycle"), owner)
    assert (await use_cases.archive({{entity}}.id, owner)).status is {{Entity}}Status.ARCHIVED
    assert (await use_cases.restore({{entity}}.id, owner)).status is {{Entity}}Status.ACTIVE
    await use_cases.delete({{entity}}.id, owner)
    assert {{entity}}.id not in repo.rows
    assert events.names == ["{{Entity}}Created", "{{Entity}}Archived", "{{Entity}}Restored", "{{Entity}}Deleted"]


async def test_search_returns_own_only(use_cases: {{Entity}}UseCases, owner: UUID) -> None:
    await use_cases.create(Create{{Entity}}Command(name="Mine"), owner)
    await use_cases.create(Create{{Entity}}Command(name="Theirs"), uuid4())
    page = await use_cases.search(owner, status=None, offset=0, limit=10)
    assert [x.name.value for x in page.items] == ["Mine"]
    assert page.total == 1
''',
    "tests/unit/__init__.py": "",
    "tests/integrations/test_{{entities}}_api.py": INTEGRATION_TEST,
}
