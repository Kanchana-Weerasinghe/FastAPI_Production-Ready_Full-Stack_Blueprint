"""
Loads the UserAccount business rules and test cases from the shared spec.

The spec (`specs/identity/users.rules.yaml`) is the single source of truth for both test suites:
this developer suite owns the domain, use_case, repository and integration layers; the QA suite in
`qa/identity-acceptance` owns the acceptance layer (black-box over HTTP).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).resolve().parents[4] / "specs" / "identity" / "users.rules.yaml"
DEV_LAYERS = frozenset({"domain", "use_case", "repository", "integration"})
ALL_LAYERS = DEV_LAYERS | {"acceptance"}


@dataclass(frozen=True, slots=True)
class TestCase:
    id: str
    layer: str
    given: str
    when: str
    then: str


@dataclass(frozen=True, slots=True)
class BusinessRule:
    id: str
    rule: str
    visibility: str
    cases: tuple[TestCase, ...]


def load_rules(path: Path = SPEC_PATH) -> tuple[BusinessRule, ...]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return tuple(
        BusinessRule(
            id=rule["id"],
            rule=rule["rule"],
            visibility=rule["visibility"],
            cases=tuple(TestCase(**case) for case in rule["cases"]),
        )
        for rule in document["rules"]
    )


USER_RULES = load_rules()
