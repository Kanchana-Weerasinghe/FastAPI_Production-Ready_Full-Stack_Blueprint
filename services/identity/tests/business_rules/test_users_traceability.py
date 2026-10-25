"""
Traceability for the developer-owned layers of the shared spec (specs/identity/users.rules.yaml):
every domain / use_case / repository / integration case has exactly one test here, and every
`@pytest.mark.br(...)` points to a case of those layers. Acceptance cases are owned and checked by
the QA suite (qa/identity-acceptance).

Runs on the source files (not on the collected tests), so it also holds when you run a subset.
"""

import ast
from pathlib import Path

from tests.business_rules.users_catalogue import ALL_LAYERS, DEV_LAYERS, USER_RULES

SUITE_DIR = Path(__file__).parent


def _tagged_cases() -> list[tuple[str, str, str]]:
    """(rule_id, case_id, 'file::test') for every `@pytest.mark.br(rule, case)` decorator."""
    found = []
    for path in sorted(SUITE_DIR.glob("test_users_*.py")):
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


def _dev_cases() -> set[tuple[str, str]]:
    return {(rule.id, case.id) for rule in USER_RULES for case in rule.cases if case.layer in DEV_LAYERS}


def test_every_developer_case_in_the_spec_has_exactly_one_test() -> None:
    tagged = _tagged_cases()
    counts = {key: sum(1 for rule, case, _ in tagged if (rule, case) == key) for key in _dev_cases()}
    missing = sorted(key for key, n in counts.items() if n == 0)
    duplicated = sorted(key for key, n in counts.items() if n > 1)
    assert not missing, f"Developer test cases without a test: {missing}"
    assert not duplicated, f"Test cases with more than one test: {duplicated}"


def test_every_br_tag_points_to_a_developer_case() -> None:
    wrong = [(rule, case, where) for rule, case, where in _tagged_cases() if (rule, case) not in _dev_cases()]
    assert not wrong, f"Tests tagged with unknown or QA-owned (acceptance) cases: {wrong}"


def test_spec_is_well_formed() -> None:
    seen: set[str] = set()
    for rule in USER_RULES:
        assert rule.visibility in {"api", "internal", "both"}, (rule.id, rule.visibility)
        for case in rule.cases:
            assert case.id.startswith("TC-" + rule.id.removeprefix("BR-") + "-"), (rule.id, case.id)
            assert case.layer in ALL_LAYERS, (case.id, case.layer)
            assert case.id not in seen, f"duplicate case id {case.id}"
            seen.add(case.id)
