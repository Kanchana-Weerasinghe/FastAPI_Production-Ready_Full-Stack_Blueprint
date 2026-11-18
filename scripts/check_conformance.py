"""
Conformance check: does hand-written code follow the framework's architecture, folder structure and
coding standards (AGENTS.md)? Run it from the repository root before opening a pull request.

    python scripts/check_conformance.py                     # every service, static rules + tools
    python scripts/check_conformance.py monitoring          # one service
    python scripts/check_conformance.py --static-only       # rules only (fast, no uv needed)
    python scripts/check_conformance.py --changed           # only report files changed vs master
    python scripts/check_conformance.py --strict            # warnings fail too
    python scripts/check_conformance.py --list-rules        # what is checked, and why

Two stages:
1. Static rules (this file, stdlib only): structure, layer imports, module boundaries, routes and
   access control, transactions, errors, UTC datetimes, naming. Each finding prints `path:line`.
2. Tools (per service, via uv): ruff check, ruff format --check, mypy, pytest tests/architecture.

Exit code 0 = conformant, 1 = errors (or warnings with --strict).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "services"
ACCESS_DOCUMENT = ROOT / "config" / "access-control.json"

# --------------------------------------------------------------------------------------------- rules

ERROR, WARNING = "error", "warning"

RULES: dict[str, tuple[str, str]] = {
    # Folder structure
    "STR001": (ERROR, "A business module has domain/, application/ports/, application/use_cases/, infrastructure/persistence/ (each with __init__.py)."),
    "STR002": (ERROR, "A business module has public.py, router.py, schemas.py and container.py at its root."),
    "STR003": (ERROR, "No models.py / repository.py at a module root: persistence lives in infrastructure/persistence/."),
    "STR004": (WARNING, "Unexpected file at a module root; put code in its layer folder."),
    "STR005": (WARNING, "A business module has unit tests (a tests/unit/**/<module>/ folder)."),
    # Layers and boundaries
    "LAY001": (ERROR, "app/core imports nothing from app.shared, app.modules or the composition root."),
    "LAY002": (ERROR, "app/shared imports nothing from app.modules or the composition root."),
    "LAY003": (ERROR, "domain/ is plain Python: no web framework, ORM, Pydantic, HTTP client, DI, app.core/app.shared or other modules."),
    "LAY004": (ERROR, "application/ never imports web frameworks, ORM, Pydantic, HTTP clients, DI, infrastructure, schemas or ORM models."),
    "LAY005": (ERROR, "infrastructure/ never imports a router or container."),
    "LAY006": (ERROR, "Another module is used only through its public API (public.py; auth.dependencies for the caller)."),
    "LAY007": (ERROR, "Modules never import the composition root (app.container, app.api, app.main)."),
    "LAY008": (ERROR, "A service never imports another service's code (use HTTP or events)."),
    "LAY009": (ERROR, "router.py stays thin: no ORM or infrastructure imports; call a use case."),
    "PUB001": (ERROR, "public.py only re-exports its own module's application/domain API (no classes or functions)."),
    # Routes and access control
    "API001": (ERROR, "Every module APIRouter has dependencies=[require_access()]."),
    "API002": (ERROR, "Every route declares a camelCase operation_id."),
    "API003": (ERROR, "operation_id is unique within the service."),
    "API004": (ERROR, "Every operation_id is granted in config/access-control.json for its service."),
    "API005": (WARNING, "config/access-control.json grants an operation_id no route declares (stale entry)."),
    "API006": (ERROR, "Every route applies a rate limit (rate_limit(...) in its or the router's dependencies)."),
    "API007": (WARNING, "Route handlers are async def."),
    # Coding standards
    "COD001": (ERROR, "No HTTPException outside the HTTP layer: raise errors from app/core/errors.py."),
    "COD002": (WARNING, "Routers raise application errors rather than HTTPException."),
    "COD003": (ERROR, "Services and repositories never commit/rollback: the request middleware owns the transaction."),
    "COD004": (ERROR, "Timestamps are timezone-aware UTC: no datetime.utcnow(), datetime.now() / fromtimestamp() without tz."),
    "COD005": (ERROR, "Never check a role in code: grant operations in config/access-control.json."),
    "COD006": (WARNING, "No print() in application code: use the structured logger."),
    "COD007": (ERROR, "No blocking time.sleep() / requests in async application code."),
    # Naming
    "NAM001": (WARNING, "Ports are ABCs named after their role (e.g. UserRepository(ABC))."),
    "NAM002": (WARNING, "Database adapters are sqlalchemy_<entity>_repository.py with class SqlAlchemy<Entity>Repository."),
    "NAM003": (WARNING, "Use-case files live in application/use_cases/ and are named *_use_cases.py or after one use case."),
    "NAM004": (WARNING, "Module folders are snake_case."),
    # Tools
    "TOOL": (ERROR, "ruff check, ruff format --check, mypy and the architecture tests pass."),
}

COMPOSITION_ROOT = ("app.container", "app.api", "app.main")
WEB = ("fastapi", "starlette")
DOMAIN_FORBIDDEN = (*WEB, "pydantic", "sqlalchemy", "httpx", "requests", "dependency_injector", "app.core", "app.shared")
APPLICATION_FORBIDDEN = (*WEB, "pydantic", "sqlalchemy", "httpx", "requests", "dependency_injector")
DOMAIN_PLATFORM_ALLOWED = ("platform_kit.errors",)
APPLICATION_PLATFORM_ALLOWED = ("platform_kit.errors", "platform_kit.auth", "platform_kit.logging")
PUBLIC_MODULE_FILES = {"public", "schemas", "dependencies"}
REQUIRED_LAYERS = ("domain", "application", "application/ports", "application/use_cases", "infrastructure", "infrastructure/persistence")
REQUIRED_ROOT_FILES = ("public.py", "router.py", "schemas.py", "container.py")
ALLOWED_ROOT_FILES = {"__init__.py", "public.py", "router.py", "schemas.py", "container.py", "dependencies.py", "emails.py", "README.md"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "api_route"}
CAMEL_CASE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
ROLE_NAME = re.compile(r"(^|_)(roles?|is_admin|is_superuser|is_staff)$")


@dataclass(frozen=True)
class Finding:
    rule: str
    path: Path
    line: int
    message: str

    @property
    def severity(self) -> str:
        return RULES[self.rule][0]

    def location(self) -> str:
        return f"{self.path.relative_to(ROOT).as_posix()}:{self.line}"


@dataclass
class Service:
    name: str
    root: Path
    findings: list[Finding] = field(default_factory=list)
    tool_results: dict[str, bool] = field(default_factory=dict)

    @property
    def app(self) -> Path:
        return self.root / "app"

    def add(self, rule: str, path: Path, line: int, message: str) -> None:
        # One finding per rule and line (`from x import y` is checked as both `x` and `x.y`).
        if not any(f.rule == rule and f.path == path and f.line == line for f in self.findings):
            self.findings.append(Finding(rule, path, line, message))


# --------------------------------------------------------------------------------------------- helpers


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None  # ruff reports it


def _imports(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module, node.lineno
            # `from app.modules.x import infrastructure` style
            for alias in node.names:
                yield f"{node.module}.{alias.name}", node.lineno


def _starts(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == p or name.startswith(p + ".") for p in prefixes)


def _py_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def _kwarg(call: ast.Call, name: str) -> ast.expr | None:
    return next((kw.value for kw in call.keywords if kw.arg == name), None)


def _mentions_rate_limit(expr: ast.expr | None, module_names: dict[str, str]) -> bool:
    if expr is None:
        return False
    if "rate_limit" in ast.unparse(expr):
        return True
    return any(
        isinstance(node, ast.Name) and "rate_limit" in module_names.get(node.id, "") for node in ast.walk(expr)
    )


def _is_layered(module_dir: Path) -> bool:
    """A business module (has layers or routes); support modules such as a bare auth/ are skipped."""
    return (module_dir / "domain").is_dir() or (module_dir / "router.py").is_file()


def _modules(service: Service) -> list[Path]:
    modules_dir = service.app / "modules"
    if not modules_dir.is_dir():
        return []
    return sorted(p for p in modules_dir.iterdir() if p.is_dir() and not p.name.startswith(("__", ".")))


# --------------------------------------------------------------------------------------------- checks


def check_structure(service: Service) -> None:
    unit_dirs = {p.name for p in (service.root / "tests").rglob("*") if p.is_dir()} if (service.root / "tests").is_dir() else set()
    for module in _modules(service):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", module.name):
            service.add("NAM004", module, 1, f"module folder '{module.name}' is not snake_case")
        for flat in ("models.py", "repository.py"):
            if (module / flat).is_file():
                service.add("STR003", module / flat, 1, f"move {flat} into infrastructure/persistence/")
        if not _is_layered(module):
            continue
        for layer in REQUIRED_LAYERS:
            layer_dir = module / layer
            if not layer_dir.is_dir():
                service.add("STR001", module, 1, f"{module.name} is missing {layer}/")
            elif not (layer_dir / "__init__.py").is_file():
                service.add("STR001", layer_dir, 1, f"{module.name}/{layer}/ is missing __init__.py")
        for required in REQUIRED_ROOT_FILES:
            if not (module / required).is_file():
                service.add("STR002", module, 1, f"{module.name} is missing {required}")
        for entry in module.iterdir():
            if entry.is_file() and entry.name not in ALLOWED_ROOT_FILES | {"models.py", "repository.py"} and entry.suffix == ".py":
                service.add("STR004", entry, 1, f"'{entry.name}' at the root of {module.name}/; move it into a layer")
        if module.name not in unit_dirs:
            service.add("STR005", module, 1, f"no tests folder named '{module.name}' under tests/")


def check_imports(service: Service, other_services: tuple[str, ...]) -> None:
    app = service.app
    for path in _py_files(app):
        tree = _parse(path)
        if tree is None:
            continue
        rel = path.relative_to(app).parts
        area = rel[0] if len(rel) > 1 else ""
        module_parts = rel[2:] if area == "modules" and len(rel) > 2 else ()
        own_module = rel[1] if area == "modules" and len(rel) > 2 else ""
        layer = module_parts[0] if len(module_parts) > 1 else ""

        for name, line in _imports(tree):
            if _starts(name, other_services):
                service.add("LAY008", path, line, f"imports another service: {name}")
            if area == "core" and _starts(name, ("app.shared", "app.modules", *COMPOSITION_ROOT)):
                service.add("LAY001", path, line, f"core imports {name}")
            if area == "shared" and _starts(name, ("app.modules", *COMPOSITION_ROOT)):
                service.add("LAY002", path, line, f"shared imports {name}")
            if area != "modules" or not own_module:
                continue
            if _starts(name, COMPOSITION_ROOT):
                service.add("LAY007", path, line, f"module imports the composition root {name}")
            parts = name.split(".")
            if parts[:2] == ["app", "modules"] and len(parts) >= 4 and parts[2] != own_module:
                if parts[3] not in PUBLIC_MODULE_FILES:
                    service.add("LAY006", path, line, f"uses non-public {name}; import app.modules.{parts[2]}.public")
            if layer == "domain":
                if _starts(name, DOMAIN_FORBIDDEN):
                    service.add("LAY003", path, line, f"domain imports {name}")
                elif name.startswith("platform_kit") and not _starts(name, DOMAIN_PLATFORM_ALLOWED):
                    service.add("LAY003", path, line, f"domain imports {name} (only platform_kit.errors is allowed)")
                elif parts[:2] == ["app", "modules"] and len(parts) > 2 and parts[2] != own_module:
                    service.add("LAY003", path, line, f"domain imports another module: {name}")
            elif layer == "application":
                if _starts(name, APPLICATION_FORBIDDEN):
                    service.add("LAY004", path, line, f"application imports {name}")
                elif ".infrastructure" in name or name.endswith((".models", ".schemas", ".router", ".container")):
                    service.add("LAY004", path, line, f"application imports {name}; depend on a port instead")
                elif name.startswith("platform_kit") and not _starts(name, APPLICATION_PLATFORM_ALLOWED):
                    service.add("LAY004", path, line, f"application imports {name}")
            elif layer == "infrastructure" and name.endswith((".router", ".container")):
                service.add("LAY005", path, line, f"infrastructure imports {name}")
            if path.name == "router.py" and len(module_parts) == 1:
                if _starts(name, ("sqlalchemy",)) or ".infrastructure" in name:
                    service.add("LAY009", path, line, f"router imports {name}; go through a use case")


def check_public_api(service: Service) -> None:
    for module in _modules(service):
        public = module / "public.py"
        tree = _parse(public) if public.is_file() else None
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                service.add("PUB001", public, node.lineno, f"public.py defines '{node.name}'; move it to application/")
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                own = f"app.modules.{module.name}."
                if not (node.module.startswith(own + "application") or node.module.startswith(own + "domain")):
                    service.add("PUB001", public, node.lineno, f"public.py re-exports {node.module}")


def check_routes(service: Service, access: dict[str, set[str]]) -> None:
    declared: dict[str, Finding] = {}
    for module in _modules(service):
        router = module / "router.py"
        tree = _parse(router) if router.is_file() else None
        if tree is None:
            continue
        module_names = {
            target.id: ast.unparse(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        router_vars: dict[str, bool] = {}  # router variable -> router-level rate limit
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and ast.unparse(node.func).split(".")[-1] == "APIRouter":
                deps = _kwarg(node, "dependencies")
                if deps is None or "require_access" not in ast.unparse(deps):
                    service.add("API001", router, node.lineno, "APIRouter(...) lacks dependencies=[require_access()]")
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if ast.unparse(node.value.func).split(".")[-1] == "APIRouter":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            router_vars[target.id] = _mentions_rate_limit(_kwarg(node.value, "dependencies"), module_names)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not (
                    isinstance(deco, ast.Call)
                    and isinstance(deco.func, ast.Attribute)
                    and deco.func.attr in HTTP_METHODS
                    and isinstance(deco.func.value, ast.Name)
                    and deco.func.value.id in router_vars
                ):
                    continue
                if isinstance(node, ast.FunctionDef):
                    service.add("API007", router, node.lineno, f"route '{node.name}' is not async def")
                op = _kwarg(deco, "operation_id")
                if not (isinstance(op, ast.Constant) and isinstance(op.value, str)):
                    service.add("API002", router, deco.lineno, f"route '{node.name}' has no literal operation_id")
                else:
                    op_id = op.value
                    if not CAMEL_CASE.match(op_id):
                        service.add("API002", router, deco.lineno, f"operation_id '{op_id}' is not camelCase")
                    if op_id in declared:
                        service.add("API003", router, deco.lineno, f"operation_id '{op_id}' also at {declared[op_id].location()}")
                    else:
                        declared[op_id] = Finding("API003", router, deco.lineno, op_id)
                    if op_id not in access.get(service.name, set()):
                        service.add("API004", router, deco.lineno, f"'{op_id}' is not granted to any privilege for '{service.name}'")
                if not (router_vars[deco.func.value.id] or _mentions_rate_limit(_kwarg(deco, "dependencies"), module_names)):
                    service.add("API006", router, deco.lineno, f"route '{node.name}' has no rate_limit(...) dependency")

    for op_id in sorted(access.get(service.name, set()) - set(declared)):
        service.add("API005", ACCESS_DOCUMENT, 1, f"'{op_id}' ({service.name}) matches no route")


def check_coding_rules(service: Service) -> None:
    app = service.app
    for path in _py_files(app):
        tree = _parse(path)
        if tree is None:
            continue
        rel = path.relative_to(app).as_posix()
        in_http_layer = path.name == "router.py" or rel.startswith("core/") or rel in {"main.py", "api.py"}
        in_business = rel.startswith(("modules/", "shared/"))
        in_async_code = rel.startswith("modules/")
        for node in ast.walk(tree):
            # COD001/COD002: HTTPException
            if isinstance(node, ast.Raise) and node.exc is not None and "HTTPException" in ast.unparse(node.exc):
                rule = "COD002" if path.name == "router.py" else ("COD001" if not in_http_layer else "")
                if rule:
                    service.add(rule, path, node.lineno, "raises HTTPException; raise an app/core/errors.py error")
            if isinstance(node, ast.ImportFrom) and not in_http_layer and any(a.name == "HTTPException" for a in node.names):
                service.add("COD001", path, node.lineno, "imports HTTPException outside the HTTP layer")
            if not isinstance(node, (ast.Call, ast.Compare)):
                continue
            if isinstance(node, ast.Compare):
                # COD005: role checks
                if in_business and "/infrastructure/" not in rel:
                    for side in (node.left, *node.comparators):
                        names = [n.attr if isinstance(n, ast.Attribute) else n.id for n in ast.walk(side) if isinstance(n, (ast.Attribute, ast.Name))]
                        if any(ROLE_NAME.search(n) for n in names):
                            service.add("COD005", path, node.lineno, f"role check `{ast.unparse(node)}`; use access-control.json")
                            break
                continue
            func = ast.unparse(node.func)
            # COD003: commits
            if in_business and isinstance(node.func, ast.Attribute) and node.func.attr in {"commit", "rollback"}:
                service.add("COD003", path, node.lineno, f"`{func}()`; the middleware owns the transaction (use uow.after_commit)")
            # COD004: naive datetimes
            short = func.removeprefix("datetime.")
            has_tz = any(kw.arg == "tz" for kw in node.keywords)
            if short in {"utcnow", "utcfromtimestamp"} and func.startswith("datetime"):
                service.add("COD004", path, node.lineno, f"`{func}()` is naive; use datetime.now(UTC)")
            elif func in {"datetime.now", "datetime.datetime.now"} and not node.args and not has_tz:
                service.add("COD004", path, node.lineno, f"`{func}()` without tz; use datetime.now(UTC)")
            elif func in {"datetime.fromtimestamp", "datetime.datetime.fromtimestamp"} and len(node.args) < 2 and not has_tz:
                service.add("COD004", path, node.lineno, f"`{func}()` without tz=UTC")
            elif func in {"datetime.today", "datetime.datetime.today"}:
                service.add("COD004", path, node.lineno, f"`{func}()` is naive; use datetime.now(UTC)")
            # COD006: print
            if func == "print":
                service.add("COD006", path, node.lineno, "print(); use the structured logger")
            # COD007: blocking calls
            if in_async_code and (func == "time.sleep" or func.startswith("requests.")):
                service.add("COD007", path, node.lineno, f"blocking `{func}()`; use asyncio.sleep / httpx.AsyncClient")


def check_naming(service: Service) -> None:
    for module in _modules(service):
        if not _is_layered(module):
            continue
        for port in _py_files(module / "application" / "ports"):
            tree = _parse(port)
            if tree is None or port.name == "__init__.py":
                continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                bases = {ast.unparse(b).split(".")[-1] for b in node.bases}
                if "Protocol" in bases:
                    service.add("NAM001", port, node.lineno, f"port '{node.name}' is a Protocol; use ABC")
                if node.name.endswith("Port"):
                    service.add("NAM001", port, node.lineno, f"port '{node.name}': drop the 'Port' suffix")
        for adapter in _py_files(module / "infrastructure" / "persistence"):
            if adapter.name in {"__init__.py", "models.py"}:
                continue
            match = re.fullmatch(r"sqlalchemy_([a-z0-9_]+)_repository\.py", adapter.name)
            if not match:
                service.add("NAM002", adapter, 1, f"'{adapter.name}': name it sqlalchemy_<entity>_repository.py")
                continue
            tree = _parse(adapter)
            classes = [n for n in tree.body if isinstance(n, ast.ClassDef)] if tree else []
            expected = "SqlAlchemy" + "".join(p.capitalize() for p in match.group(1).split("_")) + "Repository"
            if classes and not any(c.name == expected for c in classes):
                service.add("NAM002", adapter, classes[0].lineno, f"expected class {expected}")
        for use_case in _py_files(module / "application" / "use_cases"):
            if use_case.name != "__init__.py" and use_case.name in {"service.py", "services.py", "utils.py", "helpers.py"}:
                service.add("NAM003", use_case, 1, f"'{use_case.name}': name it <entity>_use_cases.py or after the use case")


# --------------------------------------------------------------------------------------------- tools

TOOLS = {
    "ruff check": ["uv", "run", "ruff", "check", "."],
    "ruff format": ["uv", "run", "ruff", "format", "--check", "."],
    "mypy": ["uv", "run", "mypy", "."],
    # --noconftest: the architecture tests are pure static checks; the root conftest would start Postgres (Docker).
    "architecture tests": ["uv", "run", "pytest", "tests/architecture", "-q", "-p", "no:cacheprovider", "--noconftest"],
}


def run_tools(service: Service, skip_mypy: bool, verbose: bool) -> None:
    for label, command in TOOLS.items():
        if skip_mypy and label == "mypy":
            continue
        if label == "architecture tests" and not (service.root / "tests" / "architecture").is_dir():
            continue
        print(f"  {DIM}running {label} ...{RESET}", flush=True)
        proc = subprocess.run(command, cwd=service.root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        service.tool_results[label] = proc.returncode == 0
        if proc.returncode != 0 or verbose:
            output = (proc.stdout + proc.stderr).strip().splitlines()
            tail = output if verbose else output[-25:]
            for line in tail:
                print(f"    {line}")


# --------------------------------------------------------------------------------------------- output

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
if USE_COLOR and os.name == "nt":
    os.system("")  # enables ANSI escape codes on Windows terminals
RED, YELLOW, GREEN, DIM, BOLD, RESET = (
    ("\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[1m", "\033[0m") if USE_COLOR else ("",) * 6
)


def print_findings(service: Service) -> None:
    by_rule: dict[str, list[Finding]] = {}
    for finding in sorted(service.findings, key=lambda f: (f.rule, str(f.path), f.line)):
        by_rule.setdefault(finding.rule, []).append(finding)
    if not by_rule:
        print(f"  {GREEN}no rule violations{RESET}")
    for rule, findings in by_rule.items():
        severity, description = RULES[rule]
        color = RED if severity == ERROR else YELLOW
        print(f"\n  {color}{BOLD}{rule}{RESET} {color}[{severity}]{RESET} {description}")
        for f in findings:
            print(f"    {f.location()}  {DIM}{f.message}{RESET}")


def print_summary(services: list[Service], strict: bool) -> bool:
    print(f"\n{BOLD}Summary{RESET}")
    print(f"  {'service':<14}{'errors':>8}{'warnings':>10}   tools")
    ok = True
    for s in services:
        errors = sum(f.severity == ERROR for f in s.findings)
        warnings = sum(f.severity == WARNING for f in s.findings)
        tools = ", ".join(f"{name} {'ok' if passed else 'FAILED'}" for name, passed in s.tool_results.items()) or "skipped"
        failed = errors > 0 or (strict and warnings > 0) or not all(s.tool_results.values())
        ok = ok and not failed
        mark = f"{RED}FAIL{RESET}" if failed else f"{GREEN}PASS{RESET}"
        print(f"  {s.name:<14}{errors:>8}{warnings:>10}   {tools}   {mark}")
    print(f"\n{GREEN + 'Conformant.' if ok else RED + 'Not conformant: fix the errors above.'}{RESET}")
    return ok


# --------------------------------------------------------------------------------------------- main


def load_access() -> dict[str, set[str]]:
    granted: dict[str, set[str]] = {}
    if not ACCESS_DOCUMENT.is_file():
        return granted
    document = json.loads(ACCESS_DOCUMENT.read_text(encoding="utf-8"))
    for privilege in document.get("privileges", {}).values():
        for service, operations in privilege.get("endpoints", {}).items():
            granted.setdefault(service, set()).update(operations)
    return granted


def changed_files(base: str) -> set[Path]:
    def git(*args: str) -> list[str]:
        proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return proc.stdout.splitlines() if proc.returncode == 0 else []

    names = git("diff", "--name-only", f"{base}...HEAD") + git("diff", "--name-only", "HEAD")
    names += git("ls-files", "--others", "--exclude-standard")
    return {(ROOT / n).resolve() for n in names}


def _touches(path: Path, changed: set[Path]) -> bool:
    """A file finding counts if the file changed; a folder finding if anything inside it changed."""
    resolved = path.resolve()
    return resolved in changed or (path.is_dir() and any(resolved in c.parents for c in changed))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check code against the framework's architecture and standards.")
    parser.add_argument("services", nargs="*", help="service names under services/ (default: all)")
    parser.add_argument("--static-only", action="store_true", help="skip ruff, mypy and the architecture tests")
    parser.add_argument("--no-mypy", action="store_true", help="skip mypy (the slowest tool)")
    parser.add_argument("--changed", nargs="?", const="master", metavar="BASE", help="report only files changed vs BASE (default master)")
    parser.add_argument("--strict", action="store_true", help="warnings fail the check too")
    parser.add_argument("--verbose", action="store_true", help="print full tool output")
    parser.add_argument("--list-rules", action="store_true", help="print every rule and exit")
    args = parser.parse_args()

    if args.list_rules:
        for rule, (severity, description) in RULES.items():
            print(f"{rule:<8}{severity:<9}{description}")
        return 0

    available = sorted(p.name for p in SERVICES_DIR.iterdir() if (p / "app").is_dir())
    unknown = set(args.services) - set(available)
    if unknown:
        parser.error(f"unknown service(s) {sorted(unknown)}; available: {available}")
    services = [Service(name, SERVICES_DIR / name) for name in (args.services or available)]
    access = load_access()
    only = changed_files(args.changed) if args.changed else None

    for service in services:
        print(f"\n{BOLD}== {service.name}{RESET}  {DIM}{service.root.relative_to(ROOT).as_posix()}{RESET}")
        check_structure(service)
        check_imports(service, tuple(n for n in available if n != service.name))
        check_public_api(service)
        check_routes(service, access)
        check_coding_rules(service)
        check_naming(service)
        if only is not None:
            service.findings = [f for f in service.findings if _touches(f.path, only)]
        print_findings(service)
        if not args.static_only:
            print()
            run_tools(service, args.no_mypy, args.verbose)

    return 0 if print_summary(services, args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
