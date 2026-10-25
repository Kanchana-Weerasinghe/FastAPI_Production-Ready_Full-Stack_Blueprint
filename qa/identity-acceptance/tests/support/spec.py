"""Reads the shared business-rule spec (specs/identity/users.rules.yaml)."""

from pathlib import Path
from typing import Any

import yaml


def acceptance_cases(spec_path: Path) -> set[tuple[str, str]]:
    document: dict[str, Any] = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    return {
        (rule["id"], case["id"])
        for rule in document["rules"]
        for case in rule["cases"]
        if case["layer"] == "acceptance"
    }
