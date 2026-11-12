"""
Shared engine of scripts/new_service.py (skill-ready) and scripts/new_service_demo.py (with a demo module).

Everything is staged in memory first (new files and edits of existing ones), then written in one go,
so `--dry-run` shows exactly what a real run would do.
"""

import json
import keyword
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from service_generator.templates_base import BASE_FILES, COMPOSE_BLOCK, PRECOMMIT_BLOCK, REPO_FILES
from service_generator.templates_demo import INITIAL_FILES, MODULE_FILES

ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = ROOT / "services"
ACCESS_DOCUMENT = ROOT / "config" / "access-control.json"
COMPOSE_FILE = ROOT / "docker-compose.yml"
PRECOMMIT_FILE = ROOT / ".pre-commit-config.yaml"
HELM_VALUES_DIR = ROOT / "deploy" / "helm" / "domain-service"

SERVICE_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
RESERVED_SERVICES = {"identity", "platform-kit", "web", "app", "config", "deploy", "specs", "qa"}
RESERVED_MODULES = {"auth"}
GRANTED_ROLES = ("user", "admin")
FIRST_PORT, PORT_STEP = 8010, 10
TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")


# --- Names --------------------------------------------------------------------------------------


def _pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _camel(text: str) -> str:
    parts = re.split(r"[-_]", text)
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def singularize(plural: str) -> str:
    head, _, last = plural.rpartition("_")
    if last.endswith("ies") and len(last) > 3:
        last = last[:-3] + "y"
    elif last.endswith(("sses", "xes", "ches", "shes", "zes")):
        last = last[:-2]
    elif last.endswith("s") and not last.endswith("ss"):
        last = last[:-1]
    return f"{head}_{last}" if head else last


@dataclass(frozen=True)
class Names:
    service: str  # kebab-case, e.g. data-acquisition
    port: int
    entities: str = ""  # module (snake plural), e.g. purchase_orders; empty for the skill-ready skeleton
    entity: str = ""  # snake singular, e.g. purchase_order

    @property
    def service_snake(self) -> str:
        return self.service.replace("-", "_")

    @property
    def service_title(self) -> str:
        return " ".join(p.capitalize() for p in self.service.split("-"))

    @property
    def privilege(self) -> str:
        return f"{_camel(self.service)}{_pascal(self.entities)}"

    @property
    def operation_ids(self) -> list[str]:
        entity, entities = _pascal(self.entity), _pascal(self.entities)
        return [f"create{entity}", f"list{entities}", f"get{entity}", f"update{entity}"] + [
            f"{verb}{entity}" for verb in ("archive", "restore", "delete")
        ]

    @property
    def tokens(self) -> dict[str, str]:
        tokens = {
            "service": self.service,
            "service_snake": self.service_snake,
            "service_title": self.service_title,
            "service_camel": _camel(self.service),
            "port": str(self.port),
            "revision": uuid.uuid4().hex[:12],
            "create_date": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.000000"),
        }
        if self.entities:
            entity_words, entities_words = self.entity.replace("_", " "), self.entities.replace("_", " ")
            tokens |= {
                "entities": self.entities,
                "entity": self.entity,
                "Entity": _pascal(self.entity),
                "Entities": _pascal(self.entities),
                "ENTITIES": self.entities.upper(),
                "entities_kebab": self.entities.replace("_", "-"),
                "entity_words": entity_words,
                "entities_words": entities_words,
                "Entity_words": entity_words.capitalize(),
                "Entities_words": entities_words.capitalize(),
                "id": "{" + self.entity + "_id}",
                "privilege": self.privilege,
            }
        return tokens


def render(text: str, tokens: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in tokens:
            raise KeyError(f"Unknown template token {{{{{key}}}}}")
        return tokens[key]

    return TOKEN_RE.sub(replace, text)


def validate_service_name(name: str, *, new: bool) -> Path:
    if not SERVICE_RE.match(name):
        sys.exit(f"service name {name!r} must be kebab-case, e.g. billing or data-acquisition")
    if name in RESERVED_SERVICES:
        sys.exit(f"{name!r} is reserved")
    service_dir = SERVICES_DIR / name
    if new and service_dir.exists():
        sys.exit(f"services/{name} already exists; choose another name or remove that folder first")
    if not new and not (service_dir / "app" / "core" / "config.py").exists():
        sys.exit(f"services/{name} is not a service generated by these scripts")
    return service_dir


def module_names(module: str, singular: str | None) -> tuple[str, str]:
    singular = singular or singularize(module)
    for value, what in ((module, "--module"), (singular, "--singular")):
        if not MODULE_RE.match(value) or keyword.iskeyword(value) or value in RESERVED_MODULES:
            sys.exit(f"{what} {value!r} must be snake_case (e.g. purchase_orders), not a keyword, not 'auth'")
    return module, singular


# --- Staged writing -----------------------------------------------------------------------------


class Writer:
    def __init__(self, *, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.new: dict[Path, str] = {}
        self.changed: dict[Path, tuple[str, bool]] = {}  # path -> (LF text, file used CRLF)
        self.warnings: list[str] = []

    def add(self, path: Path, content: str) -> None:
        if path.exists():
            if path.read_text(encoding="utf-8") != content:
                self.warnings.append(f"kept existing {_rel(path)}")
            return
        self.new[path] = content

    def add_templates(self, base: Path, templates: dict[str, str], tokens: dict[str, str]) -> None:
        for rel, content in templates.items():
            self.add(base / render(rel, tokens), render(content, tokens))

    def edit(self, path: Path, change: Callable[[str], str | None]) -> None:
        """Applies `change` to a staged or existing file (LF inside; original line endings kept)."""
        if path in self.new:
            updated = change(self.new[path])
            if updated is not None:
                self.new[path] = updated
            return
        if path in self.changed:
            text, crlf = self.changed[path]
        elif path.exists():
            raw = path.read_bytes().decode("utf-8")
            text, crlf = raw.replace("\r\n", "\n"), "\r\n" in raw
        else:
            self.warnings.append(f"{_rel(path)} not found: update it by hand")
            return
        updated = change(text)
        if updated is not None and updated != text:
            self.changed[path] = (updated, crlf)

    def flush(self) -> None:
        prefix = "would " if self.dry_run else ""
        for path in sorted(self.new):
            print(f"{prefix}create  {_rel(path)}")
        for path in sorted(self.changed):
            print(f"{prefix}update  {_rel(path)}")
        for warning in self.warnings:
            print(f"! {warning}")
        if self.dry_run:
            return
        for path, content in self.new.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        for path, (text, crlf) in self.changed.items():
            path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _insert_after_last(text: str, prefixes: tuple[str, ...], line: str) -> str:
    """Inserts `line` after the last line starting with the first prefix that matches any line."""
    lines = text.split("\n")
    if line in lines:
        return text
    for prefix in prefixes:
        indexes = [i for i, existing in enumerate(lines) if existing.startswith(prefix)]
        if indexes:
            lines.insert(indexes[-1] + 1, line)
            return "\n".join(lines)
    raise ValueError(f"no line starting with {prefixes[0]!r}")


# --- Service skeleton and repository-level wiring -----------------------------------------------


def stage_service(writer: Writer, names: Names) -> None:
    tokens = names.tokens
    writer.add_templates(SERVICES_DIR / names.service, BASE_FILES, tokens)
    writer.add_templates(ROOT, REPO_FILES, tokens)
    _stage_compose(writer, tokens)
    _stage_precommit(writer, tokens)


def _stage_compose(writer: Writer, tokens: dict[str, str]) -> None:
    def change(text: str) -> str | None:
        if re.search(rf"^  {re.escape(tokens['service'])}:\s*$", text, flags=re.M):
            return None
        anchor = re.search(r"^  web:\s*$", text, flags=re.M) or re.search(r"^volumes:\s*$", text, flags=re.M)
        if anchor is None:
            writer.warnings.append("docker-compose.yml: no `web:` service or `volumes:` key; add the service by hand")
            return None
        return text[: anchor.start()] + render(COMPOSE_BLOCK, tokens) + text[anchor.start() :]

    writer.edit(COMPOSE_FILE, change)


def _stage_precommit(writer: Writer, tokens: dict[str, str]) -> None:
    def change(text: str) -> str | None:
        if f"id: {tokens['service']}-ruff" in text:
            return None
        marker = "      - id: platform-kit-checks"
        if marker not in text:
            writer.warnings.append(".pre-commit-config.yaml: platform-kit hook not found; add the service hooks by hand")
            return None
        return text.replace(marker, render(PRECOMMIT_BLOCK, tokens) + marker, 1)

    writer.edit(PRECOMMIT_FILE, change)


def next_free_port() -> int:
    taken = {8000}
    if COMPOSE_FILE.exists():
        taken |= {int(p) for p in re.findall(r'"(\d+):\d+"', COMPOSE_FILE.read_text(encoding="utf-8"))}
    for pyproject in SERVICES_DIR.glob("*/pyproject.toml"):
        taken |= {int(p) for p in re.findall(r"--port (\d+)", pyproject.read_text(encoding="utf-8"))}
    port = FIRST_PORT
    while port in taken:
        port += PORT_STEP
    return port


# --- Demo module -------------------------------------------------------------------------------


def stage_demo_module(writer: Writer, names: Names, *, initial_migration: bool) -> None:
    """Adds the demo module and wires it into the service, the access document and the deploy values."""
    service_dir = SERVICES_DIR / names.service
    tokens = names.tokens
    writer.add_templates(service_dir, MODULE_FILES, tokens)
    if initial_migration:
        writer.add_templates(service_dir, INITIAL_FILES, tokens)
    wire_module(writer, names)
    _stage_privilege(
        writer,
        names,
        names.operation_ids,
        f"Create, read, change and delete your own {names.entities.replace('_', ' ')} (demo module).",
    )


def stage_boilerplate_module(writer: Writer, names: Names) -> None:
    """Adds a CRUD example module, its migration (chained to the current head) and its grant."""
    from service_generator.templates_module import MIGRATION
    from service_generator.templates_module import MODULE_FILES as BOILERPLATE_FILES

    service_dir = SERVICES_DIR / names.service
    tokens = names.tokens
    writer.add_templates(service_dir, BOILERPLATE_FILES, tokens)
    head = alembic_head(service_dir / "migrations" / "versions")
    migration_tokens = tokens | {
        "down_revision": repr(head),
        "down_revision_text": head or "",
    }
    writer.add(
        service_dir / "migrations" / "versions" / f"{tokens['revision']}_create_{names.entities}.py",
        render(MIGRATION, migration_tokens),
    )
    wire_module(writer, names, with_limit=False)
    entity, entities = _pascal(names.entity), _pascal(names.entities)
    _stage_privilege(
        writer,
        names,
        [
            f"create{entity}",
            f"list{entities}",
            f"get{entity}",
            f"update{entity}",
            f"archive{entity}",
            f"restore{entity}",
            f"delete{entity}",
        ],
        f"Create, read, update, archive, restore and delete {names.entities.replace('_', ' ')}.",
    )


def alembic_head(versions_dir: Path) -> str | None:
    """The single head revision of a service's migrations (None when there are none yet)."""
    revisions: set[str] = set()
    parents: set[str] = set()
    for path in versions_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'^revision\s*(?::[^=]*)?=\s*["\']([^"\']+)["\']', text, flags=re.M)
        if not match:
            continue
        revisions.add(match.group(1))
        down = re.search(r"^down_revision\s*(?::[^=]*)?=\s*(.+)$", text, flags=re.M)
        if down:
            parents |= set(re.findall(r'["\']([^"\']+)["\']', down.group(1)))
    heads = sorted(revisions - parents)
    if len(heads) > 1:
        sys.exit(f"{_rel(versions_dir)} has several heads {heads}: merge them first (alembic merge heads)")
    return heads[0] if heads else None


def wire_module(writer: Writer, names: Names, *, with_limit: bool = True) -> None:
    """Mounts the router, registers the model and container; `with_limit` adds the per-owner limit setting."""
    service_dir = SERVICES_DIR / names.service
    e, setting = names.entities, f"MAX_{names.entities.upper()}_PER_OWNER"
    container_cls = f"{_pascal(names.entities)}Container"
    edits: dict[str, Callable[[str], str]] = {
        "app/api.py": lambda t: _insert_after_last(
            _insert_after_last(
                t,
                ("from app.modules.", "from fastapi import APIRouter"),
                f"from app.modules.{e}.router import router as {e}_router",
            ),
            ("api_v1.include_router(", "api_v1 = APIRouter("),
            f"api_v1.include_router({e}_router)",
        ),
        "app/models.py": lambda t: _insert_after_last(
            t,
            ("from app.modules.", "from app.db import Base"),
            f"from app.modules.{e}.infrastructure.persistence.models import {_pascal(names.entity)}Model  # noqa: F401",
        ),
        "app/container.py": lambda t: (
            _insert_after_last(
                t,
                ("from app.modules.", "from app.core.config import config"),
                f"from app.modules.{e}.container import {container_cls}",
            ).rstrip("\n")
            + (
                f"\n\n    {e} = providers.Container(\n        {container_cls}, db=db, uow=uow, max_per_owner=config.{setting}\n    )\n"
                if with_limit
                else f"\n\n    {e} = providers.Container({container_cls}, db=db, uow=uow)\n"
            )
        ),
    }
    if with_limit:
        edits["app/core/config.py"] = lambda t: t.replace(
            "\n\n\nconfig = Settings()", f"\n    {setting}: int = 100\n\n\nconfig = Settings()", 1
        )
        edits[".env.example"] = lambda t: t.rstrip("\n") + f"\n{setting}=100\n"
    for rel, change in edits.items():
        try:
            writer.edit(service_dir / rel, change)
        except ValueError as error:
            writer.warnings.append(f"{rel}: {error}; wire the module by hand")
    if not with_limit:
        return
    try:
        writer.edit(
            HELM_VALUES_DIR / f"values-{names.service}.yaml",
            lambda t: _insert_after_last(t, ("  PROBLEM_TYPE_BASE_URI:",), f'  {setting}: "100"'),
        )
    except ValueError:
        writer.warnings.append(f"values-{names.service}.yaml: add {setting} under `config:` by hand")


def _stage_privilege(writer: Writer, names: Names, operation_ids: list[str], description: str) -> None:
    def change(text: str) -> str:
        document = json.loads(text)
        privileges, roles = document.setdefault("privileges", {}), document.setdefault("roles", {})
        words = names.entities.replace("_", " ")
        privileges.setdefault(
            names.privilege,
            {
                "name": f"{names.service_title}: {words}",
                "description": description,
                "endpoints": {names.service: operation_ids},
            },
        )
        granted = [role for role in GRANTED_ROLES if role in roles]
        if not granted:
            writer.warnings.append(f"no {GRANTED_ROLES} roles in the access document: grant {names.privilege!r} by hand")
        for role in granted:
            if names.privilege not in roles[role]:
                roles[role].append(names.privilege)
        return json.dumps(document, indent=2, ensure_ascii=False) + ("\n" if text.endswith("\n") else "")

    writer.edit(ACCESS_DOCUMENT, change)


# --- Tooling ------------------------------------------------------------------------------------


def run_tooling(service_dir: Path, *, lock: bool) -> bool:
    """uv lock/sync, ruff format + fix, OpenAPI export (which also proves the app starts)."""
    uv = shutil.which("uv")
    if uv is None:
        print("! uv not found: run `uv sync`, `uv run task format` and `uv run task openapi` in the service folder.")
        return False
    steps = ([["lock"]] if lock else []) + [
        ["sync"],
        ["run", "ruff", "format", "."],
        ["run", "ruff", "check", "--fix", "."],
        ["run", "python", "scripts/export_openapi.py"],
    ]
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    for step in steps:
        print(f"$ uv {' '.join(step)}")
        if subprocess.run([uv, *step], cwd=service_dir, env=env, check=False).returncode != 0:
            print(f"! step failed in {_rel(service_dir)}; fix it and re-run the remaining steps by hand.")
            return False
    return True
