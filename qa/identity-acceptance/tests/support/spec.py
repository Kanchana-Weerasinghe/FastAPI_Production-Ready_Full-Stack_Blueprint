"""Reads the shared business-rule specs (specs/<service>/<entity>.rules.yaml)."""

from pathlib import Path
from typing import Any

import yaml

SPEC_SUFFIX = ".rules.yaml"


def spec_files(spec_dir: Path) -> list[Path]:
    return sorted(spec_dir.glob(f"*{SPEC_SUFFIX}"))


def entity_of(spec_file: Path) -> str:
    """`users.rules.yaml` -> `users`; its acceptance tests live in `tests/test_users_acceptance.py`."""
    return spec_file.name.removesuffix(SPEC_SUFFIX)


def acceptance_cases(spec_file: Path) -> set[tuple[str, str]]:
    document: dict[str, Any] = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
    return {
        (rule["id"], case["id"])
        for rule in document["rules"]
        for case in rule["cases"]
        if case["layer"] == "acceptance"
    }
