"""Scaffold a module using domain, application ports/use cases, and infrastructure adapters.

Run from ``services/core-api/``:

    uv run python scripts/new_module.py projects
    uv run python scripts/new_module.py news --singular news_item

The starter models a user-owned named entity with a per-owner unique name rule. Review and adapt
the generated policy, persistence constraint, API contract, authorization, tests, and migration.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

TEMPLATES: dict[str, str] = {
    "__init__.py": '"""{{plural_words}} module."""\n',
    "domain/__init__.py": '"""Pure domain model and rules for {{plural_words}}."""\n',
    "domain/exceptions.py": '''"""Domain-specific rule violations for {{plural_words}}."""


class {{Singular}}NameInvalid(ValueError):
    """Raised when a {{singular_words}} name violates domain invariants."""


class {{Singular}}NameAlreadyExists(ValueError):
    """Raised when a name is already assigned within the same owner scope."""
''',
    "domain/value_objects.py": '''"""Validated values used by the {{plural_words}} domain."""

from dataclasses import dataclass

from app.modules.{{module}}.domain.exceptions import {{Singular}}NameInvalid


@dataclass(frozen=True, slots=True)
class {{Singular}}Name:
    """A normalized, non-empty {{singular_words}} name."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized or len(normalized) > 200:
            raise {{Singular}}NameInvalid("Name must contain between 1 and 200 characters")
        object.__setattr__(self, "value", normalized)
''',
    "domain/entities.py": '''"""Domain entities for {{plural_words}}."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.modules.{{module}}.domain.value_objects import {{Singular}}Name


@dataclass(frozen=True, slots=True)
class {{Singular}}:
    """A user-owned {{singular_words}} independent of the database and HTTP."""

    id: UUID
    user_id: UUID
    name: {{Singular}}Name
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(cls, *, user_id: UUID, name: {{Singular}}Name, created_by: str) -> "{{Singular}}":
        """Create a new entity and assign its identity before persistence."""
        return cls(id=uuid4(), user_id=user_id, name=name, created_by=created_by)
''',
    "domain/policies.py": '''"""Business policies for {{plural_words}}."""

from app.modules.{{module}}.domain.exceptions import {{Singular}}NameAlreadyExists


def ensure_name_available(name: str, *, already_exists: bool) -> None:
    """Reject a duplicate name within the owner's namespace."""
    if already_exists:
        raise {{Singular}}NameAlreadyExists(f"A {{singular_words}} named '{name}' already exists")
''',
    "application/__init__.py": '"""Application workflows for {{plural_words}}."""\n',
    "application/ports/__init__.py": '"""Interfaces required by {{plural_words}} use cases."""\n',
    "application/ports/repository.py": '''"""Persistence port consumed by {{plural_words}} use cases."""

from typing import Protocol
from uuid import UUID

from app.modules.{{module}}.domain.entities import {{Singular}}


class {{Singular}}Repository(Protocol):
    """Contract implemented by infrastructure persistence adapters."""

    async def exists_by_name(self, user_id: UUID, name: str) -> bool: ...

    async def add(self, entity: {{Singular}}) -> {{Singular}}: ...
''',
    "application/use_cases/__init__.py": '"""Use cases for {{plural_words}}."""\n',
    "service.py": '''"""Public application API for {{plural_words}} workflows and domain records."""

from app.modules.{{module}}.application.use_cases.create import Create{{Singular}}
from app.modules.{{module}}.domain.entities import {{Singular}}
from app.modules.{{module}}.domain.value_objects import {{Singular}}Name

__all__ = ["Create{{Singular}}", "{{Singular}}", "{{Singular}}Name"]
''',
    "application/use_cases/create.py": '''"""Create-{{singular_module}} application workflow."""

from uuid import UUID

from app.core.errors import BadRequestError, ConflictError
from app.modules.{{module}}.application.ports.repository import {{Singular}}Repository
from app.modules.{{module}}.domain.entities import {{Singular}}
from app.modules.{{module}}.domain.exceptions import {{Singular}}NameAlreadyExists, {{Singular}}NameInvalid
from app.modules.{{module}}.domain.policies import ensure_name_available
from app.modules.{{module}}.domain.value_objects import {{Singular}}Name


class Create{{Singular}}:
    """Coordinates name validation, uniqueness policy, and persistence."""

    def __init__(self, repository: {{Singular}}Repository) -> None:
        self._repository = repository

    async def execute(self, *, user_id: UUID, created_by: str, name: str) -> {{Singular}}:
        """Create an owned entity or raise the application's stable conflict error."""
        try:
            value = {{Singular}}Name(name)
        except {{Singular}}NameInvalid as error:
            raise BadRequestError(str(error), code="{{module}}_name_invalid") from error
        exists = await self._repository.exists_by_name(user_id, value.value)
        try:
            ensure_name_available(value.value, already_exists=exists)
        except {{Singular}}NameAlreadyExists as error:
            raise ConflictError(str(error), code="{{module}}_name_conflict") from error
        return await self._repository.add(
            {{Singular}}.create(user_id=user_id, name=value, created_by=created_by)
        )
''',
    "infrastructure/__init__.py": '"""Infrastructure adapters for {{plural_words}}."""\n',
    "infrastructure/persistence/__init__.py": '"""SQLAlchemy persistence adapter for {{plural_words}}."""\n',
    "infrastructure/persistence/models.py": '''"""SQLAlchemy persistence model for {{plural_words}}."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class {{Plural}}(BaseModel):
    """Database representation; domain behavior belongs in ``domain/``."""

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_{{module}}_user_name"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
''',
    "infrastructure/persistence/repository.py": '''"""SQLAlchemy implementation of the {{plural_words}} repository port."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.modules.{{module}}.application.ports.repository import {{Singular}}Repository as {{Singular}}RepositoryPort
from app.modules.{{module}}.domain.entities import {{Singular}}
from app.modules.{{module}}.domain.value_objects import {{Singular}}Name
from app.modules.{{module}}.infrastructure.persistence.models import {{Plural}}


class SqlAlchemy{{Singular}}Repository({{Singular}}RepositoryPort):
    """Maps between the pure domain entity and its SQLAlchemy persistence model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists_by_name(self, user_id: UUID, name: str) -> bool:
        result = await self._session.execute(
            select({{Plural}}.id).where({{Plural}}.user_id == user_id, {{Plural}}.name == name)
        )
        return result.scalar_one_or_none() is not None

    async def add(self, entity: {{Singular}}) -> {{Singular}}:
        model = {{Plural}}(
            id=entity.id,
            user_id=entity.user_id,
            name=entity.name.value,
            created_by=entity.created_by,
            updated_by=entity.created_by,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise ConflictError(
                "A {{singular_words}} with this name already exists",
                code="{{module}}_name_conflict",
            ) from error
        await self._session.refresh(model)
        return {{Singular}}(
            id=model.id,
            user_id=model.user_id,
            name={{Singular}}Name(model.name),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
''',
    "schemas.py": '''"""HTTP request/response schemas for {{plural_words}}."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class {{Singular}}Create(BaseModel):
    """Input payload; transport validation is not a substitute for domain invariants."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str = Field(min_length=1, max_length=200)


class {{Singular}}Response(BaseModel):
    """Public representation, deliberately separate from the ORM model."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime | None
    updated_at: datetime | None
''',
    "container.py": '''"""Dependency-injection providers for {{plural_words}}."""

from dependency_injector import containers, providers

from app.core.database import Database
from app.modules.{{module}}.application.use_cases.create import Create{{Singular}}
from app.modules.{{module}}.infrastructure.persistence.repository import SqlAlchemy{{Singular}}Repository


class {{Plural}}Container(containers.DeclarativeContainer):
    """Compose the use case with its infrastructure adapter."""

    db = providers.Dependency(instance_of=Database)
    repository = providers.Factory(SqlAlchemy{{Singular}}Repository, session=db.provided.scoped_session)
    create_{{singular_module}} = providers.Factory(Create{{Singular}}, repository=repository)
''',
    "router.py": '''"""HTTP routes for {{plural_words}}."""

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import CurrentUserDep
from app.modules.{{module}}.service import Create{{Singular}}
from app.modules.{{module}}.schemas import {{Singular}}Create, {{Singular}}Response

router = APIRouter(prefix="/{{route}}", tags=["{{module}}"])
Create{{Singular}}Dep = Annotated[
    Create{{Singular}}, Depends(Provide["{{module}}.create_{{singular_module}}"])
]


@router.post("/", response_model={{Singular}}Response, status_code=status.HTTP_201_CREATED)
@inject
async def create_{{singular_module}}(
    data: {{Singular}}Create,
    current_user: CurrentUserDep,
    use_case: Create{{Singular}}Dep,
) -> {{Singular}}Response:
    """Translate HTTP input, invoke the application workflow, and serialize its result."""
    entity = await use_case.execute(user_id=current_user.id, created_by=current_user.username, name=data.name)
    return {{Singular}}Response(
        id=entity.id,
        user_id=entity.user_id,
        name=entity.name.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
''',
}

TEST_TEMPLATES: dict[str, str] = {
    "test_domain.py": '''import pytest

from app.modules.{{module}}.domain.exceptions import {{Singular}}NameInvalid
from app.modules.{{module}}.domain.value_objects import {{Singular}}Name


def test_name_is_trimmed() -> None:
    """Verify domain names are normalized before entering an entity."""
    assert {{Singular}}Name("  Example  ").value == "Example"


def test_blank_name_is_rejected() -> None:
    """Verify whitespace-only names violate the domain invariant."""
    with pytest.raises({{Singular}}NameInvalid):
        {{Singular}}Name("   ")
''',
    "test_create.py": '''from uuid import UUID

import pytest

from app.core.errors import ConflictError
from app.modules.{{module}}.application.use_cases.create import Create{{Singular}}
from app.modules.{{module}}.domain.entities import {{Singular}}
from app.modules.{{module}}.domain.value_objects import {{Singular}}Name


class Fake{{Singular}}Repository:
    def __init__(self, *, name_exists: bool = False) -> None:
        self.name_exists = name_exists
        self.saved: {{Singular}} | None = None

    async def exists_by_name(self, _user_id: UUID, _name: str) -> bool:
        return self.name_exists

    async def add(self, entity: {{Singular}}) -> {{Singular}}:
        self.saved = entity
        return entity


async def test_create_persists_domain_entity() -> None:
    """Verify the use case validates and sends a domain entity through its port."""
    repository = Fake{{Singular}}Repository()
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    created = await Create{{Singular}}(repository).execute(
        user_id=user_id,
        created_by="test-user",
        name=" Example ",
    )

    assert repository.saved == created
    assert created.user_id == user_id
    assert created.name == {{Singular}}Name("Example")


async def test_create_rejects_duplicate_name() -> None:
    """Verify the domain policy prevents duplicate names before persistence."""
    repository = Fake{{Singular}}Repository(name_exists=True)
    user_id = UUID("00000000-0000-0000-0000-000000000001")

    with pytest.raises(ConflictError, match="already exists"):
        await Create{{Singular}}(repository).execute(
            user_id=user_id,
            created_by="test-user",
            name="Example",
        )

    assert repository.saved is None
''',
}


def _pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _render(template: str, context: dict[str, str]) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda match: context[match.group(1)], template)


def _insert_before(path: Path, marker: str, line: str) -> None:
    text = path.read_text(encoding="utf-8")
    token = f"# [scaffold:{marker}]"
    if token not in text:
        sys.exit(f"Marker {token} not found in {path}")
    if line.strip() in text:
        return
    indentation = text[: text.index(token)].rsplit("\n", 1)[-1]
    path.write_text(text.replace(token, f"{line}\n{indentation}{token}", 1), encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="Plural module name in snake_case, e.g. projects")
    parser.add_argument("--singular", help="Singular entity name in snake_case")
    args = parser.parse_args()

    module = args.name.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", module):
        sys.exit("Module name must be snake_case (letters, digits, underscores)")
    singular = args.singular or (module[:-1] if module.endswith("s") else module)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", singular):
        sys.exit("Singular name must be snake_case (letters, digits, underscores)")
    module_dir = APP / "modules" / module
    if module_dir.exists():
        sys.exit(f"{module_dir} already exists")

    plural_class, singular_class = _pascal(module), _pascal(singular)
    context = {
        "module": module,
        "singular_module": singular,
        "Plural": plural_class,
        "Singular": singular_class,
        "route": module.replace("_", "-"),
        "plural_words": module.replace("_", " "),
        "singular_words": singular.replace("_", " "),
    }
    module_dir.mkdir(parents=True)
    for relative_path, template in TEMPLATES.items():
        output_path = module_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_render(template, context), encoding="utf-8", newline="")

    test_dir = ROOT / "tests" / "unit" / "modules" / module
    test_dir.mkdir(parents=True, exist_ok=True)
    for filename, template in TEST_TEMPLATES.items():
        (test_dir / filename).write_text(_render(template, context), encoding="utf-8", newline="")

    _insert_before(
        APP / "models.py",
        "model-imports",
        f"from app.modules.{module}.infrastructure.persistence.models import {plural_class}",
    )
    _insert_before(APP / "models.py", "model-exports", f'"{plural_class}",')
    _insert_before(
        APP / "container.py",
        "container-imports",
        f"from app.modules.{module}.container import {plural_class}Container",
    )
    _insert_before(
        APP / "container.py",
        "container-providers",
        f"{module} = providers.Container({plural_class}Container, db=db)",
    )
    _insert_before(
        APP / "api.py",
        "router-imports",
        f"from app.modules.{module}.router import router as {module}_router",
    )
    _insert_before(APP / "api.py", "router-includes", f"api_v2.include_router({module}_router)")

    subprocess.run(["ruff", "check", "--fix", "--quiet", str(module_dir)], cwd=ROOT, check=True)
    subprocess.run(["ruff", "format", "--quiet", str(module_dir)], cwd=ROOT, check=True)
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(test_dir)], cwd=ROOT, check=True)
    subprocess.run(["ruff", "format", "--quiet", str(test_dir)], cwd=ROOT, check=True)

    print(f"Created layered module '{module}' at {module_dir.relative_to(ROOT)}.")
    print("Review the generated domain policy and uniqueness constraint; they are examples, not universal rules.")
    print("Next steps:")
    print(f'  1. Extend the generated tests, then run: uv run alembic revision --autogenerate -m "create {module}"')
    print("  2. Review the migration and update docs/API_FLOW.md and docs/DATABASE_DESIGN.md.")
    print("  3. Add any cross-module or external checks as application ports and wire adapters in the container.")


if __name__ == "__main__":
    main()
