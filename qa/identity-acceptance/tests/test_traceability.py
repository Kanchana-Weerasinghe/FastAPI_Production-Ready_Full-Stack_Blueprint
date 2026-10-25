"""
Traceability for the QA-owned layer: every `acceptance` case in specs/<service>/<entity>.rules.yaml has exactly one
test in tests/test_<entity>_acceptance.py, and every `@pytest.mark.br(...)` there points to an acceptance case of that
spec. Needs no running service.
"""

import ast
from pathlib import Path

import pytest

from tests.support.settings import load_settings
from tests.support.spec import acceptance_cases, entity_of, spec_files

SUITE_DIR = Path(__file__).parent
SPECS = spec_files(load_settings().spec_dir)


def _test_file(spec_file: Path) -> Path:
    return SUITE_DIR / f"test_{entity_of(spec_file)}_acceptance.py"


def _tagged_cases(path: Path) -> list[tuple[str, str, str]]:
    if not path.exists():
        return []
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "br"
                and len(decorator.args) == 2
            ):
                rule, case = (arg.value for arg in decorator.args)  # type: ignore[attr-defined]
                found.append((str(rule), str(case), f"{path.name}::{node.name}"))
    return found


def test_specs_are_found() -> None:
    assert SPECS, f"No *.rules.yaml in {load_settings().spec_dir} (set QA_SPEC_DIR)"


@pytest.mark.parametrize("spec_file", SPECS, ids=entity_of)
def test_every_acceptance_case_in_the_spec_has_exactly_one_test(spec_file: Path) -> None:
    expected = acceptance_cases(spec_file)
    tagged = _tagged_cases(_test_file(spec_file))
    counts = {key: sum(1 for rule, case, _ in tagged if (rule, case) == key) for key in expected}
    missing = sorted(key for key, n in counts.items() if n == 0)
    duplicated = sorted(key for key, n in counts.items() if n > 1)
    assert not missing, f"Acceptance cases without a test in {_test_file(spec_file).name}: {missing}"
    assert not duplicated, f"Acceptance cases with more than one test: {duplicated}"


@pytest.mark.parametrize("spec_file", SPECS, ids=entity_of)
def test_every_br_tag_points_to_an_acceptance_case(spec_file: Path) -> None:
    expected = acceptance_cases(spec_file)
    tagged = _tagged_cases(_test_file(spec_file))
    wrong = [(rule, case, where) for rule, case, where in tagged if (rule, case) not in expected]
    assert not wrong, f"Tests tagged with unknown or developer-owned cases: {wrong}"


def test_every_acceptance_file_has_a_spec() -> None:
    entities = {entity_of(spec) for spec in SPECS}
    orphans = [p.name for p in SUITE_DIR.glob("test_*_acceptance.py") if p.stem[5:-11] not in entities]
    assert not orphans, f"Acceptance test files without a matching *.rules.yaml: {orphans}"
