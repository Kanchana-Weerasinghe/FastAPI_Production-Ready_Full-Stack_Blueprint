"""
Traceability for the QA-owned layer: every `acceptance` case in specs/identity/users.rules.yaml has exactly
one test here, and every `@pytest.mark.br(...)` points to an acceptance case. Needs no running service.
"""

import ast
from pathlib import Path

from tests.support.settings import load_settings
from tests.support.spec import acceptance_cases

SUITE_DIR = Path(__file__).parent


def _tagged_cases() -> list[tuple[str, str, str]]:
    found = []
    for path in sorted(SUITE_DIR.glob("test_*_acceptance.py")):
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


def test_every_acceptance_case_in_the_spec_has_exactly_one_test() -> None:
    expected = acceptance_cases(load_settings().spec_path)
    tagged = _tagged_cases()
    counts = {key: sum(1 for rule, case, _ in tagged if (rule, case) == key) for key in expected}
    missing = sorted(key for key, n in counts.items() if n == 0)
    duplicated = sorted(key for key, n in counts.items() if n > 1)
    assert not missing, f"Acceptance cases without a test: {missing}"
    assert not duplicated, f"Acceptance cases with more than one test: {duplicated}"


def test_every_br_tag_points_to_an_acceptance_case() -> None:
    expected = acceptance_cases(load_settings().spec_path)
    wrong = [(rule, case, where) for rule, case, where in _tagged_cases() if (rule, case) not in expected]
    assert not wrong, f"Tests tagged with unknown or developer-owned cases: {wrong}"
