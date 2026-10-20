"""
Layer rules for this service, enforced on every test run:

- domain/: plain Python; may use `platform_kit.errors` only (framework-agnostic error types).
- application/: may use domain, its own ports and framework-free platform-kit parts; never
  infrastructure, web frameworks, ORMs or HTTP clients.
- No module imports another service's code: other services are reached over HTTP or events.
"""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
MODULES = sorted(p for p in (APP_DIR / "modules").iterdir() if p.is_dir() and not p.name.startswith("__"))

FORBIDDEN_IN_DOMAIN = ("fastapi", "starlette", "pydantic", "sqlalchemy", "httpx", "dependency_injector", "app.config")
FORBIDDEN_IN_APPLICATION = ("fastapi", "starlette", "pydantic", "sqlalchemy", "httpx", "dependency_injector")
ALLOWED_PLATFORM_IN_DOMAIN = ("platform_kit.errors",)
ALLOWED_PLATFORM_IN_APPLICATION = ("platform_kit.errors", "platform_kit.auth")
OTHER_SERVICES = ("core_api",)


def _imports(path: Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _starts(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name == p or name.startswith(p + ".") for p in prefixes)


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_module_has_layers(module: Path) -> None:
    for layer in ("domain", "application/ports", "application/use_cases", "infrastructure/persistence"):
        assert (module / layer).is_dir(), f"{module.name} is missing {layer}/"


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_domain_is_framework_free(module: Path) -> None:
    for path in (module / "domain").rglob("*.py"):
        for name in _imports(path):
            assert not _starts(name, FORBIDDEN_IN_DOMAIN), f"{path.relative_to(APP_DIR)} imports {name}"
            assert not name.startswith("app.modules.") or ".domain" in name, f"{path} imports {name}"
            if name.startswith("platform_kit"):
                assert _starts(name, ALLOWED_PLATFORM_IN_DOMAIN), f"{path} imports {name}"


@pytest.mark.parametrize("module", MODULES, ids=lambda p: p.name)
def test_application_does_not_depend_on_infrastructure(module: Path) -> None:
    for path in (module / "application").rglob("*.py"):
        for name in _imports(path):
            assert not _starts(name, FORBIDDEN_IN_APPLICATION), f"{path.relative_to(APP_DIR)} imports {name}"
            assert ".infrastructure" not in name, f"{path.relative_to(APP_DIR)} imports {name}"
            if name.startswith("platform_kit"):
                assert _starts(name, ALLOWED_PLATFORM_IN_APPLICATION), f"{path} imports {name}"


def test_no_imports_from_other_services() -> None:
    for path in APP_DIR.rglob("*.py"):
        for name in _imports(path):
            assert not _starts(name, OTHER_SERVICES), f"{path.relative_to(APP_DIR)} imports {name}"
