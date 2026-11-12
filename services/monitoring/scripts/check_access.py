"""
Checks this service against the central access document (config/access-control.json):
every route has an operation_id and `require_access()`, the document names no unknown operation of
this service, and every operation is granted to at least one role.

    uv run python scripts/check_access.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from platform_kit.access import access_setup_errors, load_access_policy, route_operation_ids

from app.core.config import config
from app.main import ACCESS_EXEMPT_PATH_PREFIXES, app


def main() -> int:
    policy = load_access_policy(config.ACCESS_CONFIG_PATH, service=config.SERVICE_NAME)
    errors = access_setup_errors(app, policy=policy, exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES)
    operations = route_operation_ids(app, exempt_path_prefixes=ACCESS_EXEMPT_PATH_PREFIXES)
    errors += [
        f"operation {operation!r} is not granted to any role in {config.ACCESS_CONFIG_PATH}"
        for operation in sorted(operations - policy.operations)
    ]
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
