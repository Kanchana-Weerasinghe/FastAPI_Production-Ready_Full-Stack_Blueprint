"""
Traceability: every business rule and test case in the catalogue has exactly one test, and every
`@pytest.mark.br(...)` in this folder points to a rule and case that exist.

Runs on the source files (not on the collected tests), so it also holds when you run a subset.
"""

import ast
from pathlib import Path

from tests.business_rules.users_catalogue import USER_RULES

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


def test_every_test_case_in_the_catalogue_has_exactly_one_test() -> None:
    tagged = _tagged_cases()
    expected = {(rule.id, case.id) for rule in USER_RULES for case in rule.cases}
    counts = {key: sum(1 for rule, case, _ in tagged if (rule, case) == key) for key in expected}
    missing = sorted(key for key, n in counts.items() if n == 0)
    duplicated = sorted(key for key, n in counts.items() if n > 1)
    assert not missing, f"Test cases without a test: {missing}"
    assert not duplicated, f"Test cases with more than one test: {duplicated}"


def test_every_br_tag_points_to_a_known_rule_and_case() -> None:
    known = {(rule.id, case.id) for rule in USER_RULES for case in rule.cases}
    unknown = [(rule, case, where) for rule, case, where in _tagged_cases() if (rule, case) not in known]
    assert not unknown, f"Tests tagged with unknown rule/case IDs: {unknown}"


def test_test_case_ids_belong_to_their_rule() -> None:
    for rule in USER_RULES:
        for case in rule.cases:
            assert case.id.startswith("TC-" + rule.id.removeprefix("BR-") + "-"), (rule.id, case.id)
            assert case.layer in {"domain", "use_case", "repository", "api"}, (case.id, case.layer)
