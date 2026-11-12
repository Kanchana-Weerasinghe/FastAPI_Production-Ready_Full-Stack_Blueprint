"""
Creates a new, EMPTY domain service ready for the generate-test-suite / generate-source-code skills.

    python scripts/new_service.py <service-name>             # e.g. billing, lab-monitoring
    python scripts/new_service.py <service-name> --dry-run   # show what would be written

No business module is created: the skills build each module from its specs. The service already has
everything they rely on (same names as the identity service):

- app/core/config.py, errors.py, security.py (`rate_limit`), logging.py;
- app/modules/auth/dependencies.py (`CurrentUserDep`, `get_access_subject`, `roles_of`);
- app/main.py on central access control (`install_access`), app/api.py, container.py, models.py, db.py;
- Alembic for the service's own schema; Dockerfile, .env.example, README;
- tests/conftest.py (`client`, `grant_access`, `deny_access`, `db_session`, `fake_uow`),
  tests/integrations/conftest.py (`isolated_app_transaction`), tests/business_rules/ (+ `task test-br`),
  tests/mocks/uow.py, architecture tests (layers, access control).

It also adds deploy/db/roles-<name>.sql, deploy/helm/domain-service/values-<name>.yaml, the
docker-compose services and the pre-commit hooks, then runs uv lock/sync, ruff and the OpenAPI export.
For a service WITH a working example module (to learn the architecture), use new_service_demo.py.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from service_generator.engine import Names, Writer, next_free_port, run_tooling, stage_service, validate_service_name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="service name in kebab-case, e.g. billing or lab-monitoring")
    parser.add_argument("--port", type=int, help="local/dev port (default: next free from 8010)")
    parser.add_argument("--skip-sync", action="store_true", help="do not run uv lock/sync, ruff and the OpenAPI export")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be written")
    args = parser.parse_args()

    service_dir = validate_service_name(args.name, new=True)
    names = Names(service=args.name, port=args.port or next_free_port())
    writer = Writer(dry_run=args.dry_run)
    stage_service(writer, names)
    writer.flush()
    if args.dry_run:
        return 0

    ok = args.skip_sync or run_tooling(service_dir, lock=True)
    s = args.name
    print(
        f"\nService {s!r} created in services/{s} (port {names.port}, schema {names.service_snake!r}).\n\n"
        "Next:\n"
        f"  1. Put the specs in place:\n"
        f"       specs/{s}/<module>/service.yaml, <module>.rules.yaml and <module>.domain.yaml\n"
        "  2. Run the skills:\n"
        f"       /generate-test-suite   specs/{s}/<module>\n"
        f"       /generate-source-code  specs/{s}/<module> core\n"
        f"       /generate-source-code  specs/{s}/<module> api\n"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
