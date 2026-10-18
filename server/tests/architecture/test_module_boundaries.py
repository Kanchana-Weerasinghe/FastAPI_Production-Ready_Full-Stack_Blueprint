"""
Architecture rules for the modular monolith, enforced on every test run.

1. Layers only depend inward: `core` imports nothing from `shared`/`modules`; `shared` imports nothing
   from `modules`.
2. Domain code is framework- and persistence-agnostic. Application workflows never import HTTP
   frameworks. Persistence implementations belong under `infrastructure/`.
3. A module may use another module only through its public API (`service`, `schemas`,
   `dependencies`, `permissions`), never its persistence adapter, router or container.
4. Modules never import the composition root (`app.container`, `app.api`, `app.main`); routes
   resolve services by container path, e.g. `Provide["todos.service"]`.
5. Domain modules share `domain/`, `application/ports/`, `application/use_cases/`, and
   `infrastructure/persistence/`; `privacy` is an application-only orchestrator by design.
"""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
APPLICATION_ORCHESTRATION_MODULES = {"privacy"}
REQUIRED_DOMAIN_MODULES = {"attachments", "audit", "auth", "flags", "todos", "users"}
PUBLIC_MODULE_FILES = {"service", "schemas", "dependencies", "permissions"}
FRAMEWORK_FREE_FILES = {"service", "repository", "models"}
COMPOSITION_ROOT = ("app.container", "app.api", "app.main")


def _python_files(*parts: str) -> list[Path]:
    return sorted(APP_DIR.joinpath(*parts).rglob("*.py"))


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def _rel(path: Path) -> str:
    return path.relative_to(APP_DIR.parent).as_posix()


@pytest.mark.parametrize("path", _python_files("core"), ids=_rel)
def test_core_does_not_depend_on_outer_layers(path: Path) -> None:
    """Test that core infrastructure never imports shared code, modules or the composition root."""
    bad = [name for name in _imports(path) if name.startswith(("app.shared", "app.modules", *COMPOSITION_ROOT))]
    assert not bad, f"{_rel(path)} must not import {bad}"


@pytest.mark.parametrize("path", _python_files("shared"), ids=_rel)
def test_shared_does_not_depend_on_modules(path: Path) -> None:
    """Test that shared building blocks never import feature modules or the composition root."""
    bad = [name for name in _imports(path) if name.startswith(("app.modules", *COMPOSITION_ROOT))]
    assert not bad, f"{_rel(path)} must not import {bad}"


@pytest.mark.parametrize("path", _python_files("modules"), ids=_rel)
def test_module_boundaries(path: Path) -> None:
    """Test inward module dependencies, framework separation, and public cross-module access."""
    own_module = path.relative_to(APP_DIR / "modules").parts[0]
    module_parts = path.relative_to(APP_DIR / "modules").parts
    violations = []
    for name in _imports(path):
        if name.startswith(COMPOSITION_ROOT):
            violations.append(f"imports composition root {name}")
        if name.split(".")[0] in {"fastapi", "starlette"} and (
            path.stem in FRAMEWORK_FREE_FILES or "application" in module_parts
        ):
            violations.append(f"business code imports framework {name}")
        if "domain" in module_parts and name.split(".")[0] in {"fastapi", "starlette", "sqlalchemy"}:
            violations.append(f"domain code imports framework/persistence {name}")
        if "infrastructure" in module_parts and name.endswith((".router", ".container")):
            violations.append(f"infrastructure imports an outer layer {name}")
        parts = name.split(".")
        if parts[:2] == ["app", "modules"] and len(parts) >= 4 and parts[2] != own_module:
            if parts[3] not in PUBLIC_MODULE_FILES:
                violations.append(f"uses non-public {name}")
    assert not violations, f"{_rel(path)}: " + "; ".join(violations)


@pytest.mark.parametrize(
    "path",
    [path for path in _python_files("modules") if "application" in path.relative_to(APP_DIR / "modules").parts],
    ids=_rel,
)
def test_application_layers_do_not_depend_on_infrastructure(path: Path) -> None:
    """Application use cases and ports depend inward, never on persistence adapters."""
    bad = [
        name
        for name in _imports(path)
        if name.startswith(("sqlalchemy", "pydantic", "fastapi", "starlette"))
        or ".infrastructure" in name
        or name.endswith((".models", ".schemas"))
    ]
    assert not bad, f"{_rel(path)} must use application ports rather than infrastructure imports: {bad}"


@pytest.mark.parametrize(
    "path",
    [path for path in _python_files("modules") if "domain" in path.relative_to(APP_DIR / "modules").parts],
    ids=_rel,
)
def test_domain_layers_remain_module_local(path: Path) -> None:
    """Keep domain entities and policies independent of frameworks and other modules."""
    module_parts = path.relative_to(APP_DIR / "modules").parts
    own_module = module_parts[0]
    bad = [
        name
        for name in _imports(path)
        if name.startswith(("fastapi", "starlette", "sqlalchemy"))
        or (name.startswith("app.modules.") and name.split(".")[2] != own_module)
        or name.startswith(("app.core", "app.shared"))
    ]
    assert not bad, f"{_rel(path)} must remain framework- and module-independent: {bad}"


def test_modules_have_no_flat_persistence_facades() -> None:
    """Require persistence implementations to live exclusively under infrastructure."""
    module_dirs = [path for path in (APP_DIR / "modules").iterdir() if path.is_dir()]
    flat_facades = [
        str(module_dir / filename)
        for module_dir in module_dirs
        for filename in ("models.py", "repository.py")
        if (module_dir / filename).exists()
    ]
    assert not flat_facades


def test_modules_follow_their_declared_layer_structure() -> None:
    """Require domain modules to use the same layers and privacy to remain application-only."""
    modules_dir = APP_DIR / "modules"
    module_dirs = {
        path.name: path for path in modules_dir.iterdir() if path.is_dir() and not path.name.startswith("__")
    }
    assert REQUIRED_DOMAIN_MODULES <= set(module_dirs)
    assert APPLICATION_ORCHESTRATION_MODULES <= set(module_dirs)

    for name in set(module_dirs) - APPLICATION_ORCHESTRATION_MODULES:
        module_dir = module_dirs[name]
        for layer in (
            "domain",
            "application",
            "application/ports",
            "application/use_cases",
            "infrastructure",
            "infrastructure/persistence",
        ):
            layer_dir = module_dir / layer
            assert layer_dir.is_dir(), f"{name} is missing layer directory {layer}"
            assert (layer_dir / "__init__.py").is_file(), f"{name}/{layer} is missing __init__.py"

    privacy_dir = module_dirs["privacy"]
    assert (privacy_dir / "application/use_cases/__init__.py").is_file()
    assert not (privacy_dir / "domain").exists()
    assert not (privacy_dir / "infrastructure").exists()


@pytest.mark.parametrize(
    "module",
    sorted(path.name for path in (APP_DIR / "modules").iterdir() if path.is_dir() and not path.name.startswith("__")),
)
def test_root_service_is_a_public_application_facade(module: str) -> None:
    """Keep module public service imports stable without leaving implementation in the module root."""
    service_path = APP_DIR / "modules" / module / "service.py"
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    imports = _imports(service_path)
    assert not any(isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) for node in tree.body), (
        f"{_rel(service_path)} must re-export application APIs, not define business logic"
    )
    assert all(
        name.startswith(f"app.modules.{module}.application.") or name.startswith(f"app.modules.{module}.domain.")
        for name in imports
    ), f"{_rel(service_path)} may only expose its module's application/domain API: {imports}"
