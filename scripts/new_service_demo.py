"""
Creates a new domain service WITH a working demo module, for developers learning the architecture.

    python scripts/new_service_demo.py <service-name>                    # demo module "items"
    python scripts/new_service_demo.py <service-name> --module invoices  # name the demo module
    python scripts/new_service_demo.py <service-name> --add-module notes # add a demo module to an existing service
    python scripts/new_service_demo.py <service-name> --dry-run          # show what would be written

The service is the same skeleton new_service.py creates, plus one complete module that shows every layer
end to end: value objects, entity with lifecycle and domain events, policy, domain errors, repository
port + SQLAlchemy adapter (optimistic locking), use cases, schemas, router (operation_ids, rate limits,
ETag / If-Match, pagination), DI container, public.py, a migration, its privilege in
config/access-control.json, and unit + integration tests. Start it and call /v1/<module> right away.

For a service that the generate-test-suite / generate-source-code skills will fill, use new_service.py.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from service_generator.engine import (
    Names,
    Writer,
    module_names,
    next_free_port,
    run_tooling,
    stage_demo_module,
    stage_service,
    validate_service_name,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="service name in kebab-case, e.g. billing or lab-monitoring")
    parser.add_argument("--module", default="items", help="demo module, plural snake_case (default: items)")
    parser.add_argument("--singular", help="singular of the module name, when the automatic one is wrong")
    parser.add_argument("--add-module", metavar="PLURAL", help="add a demo module to an existing generated service")
    parser.add_argument("--port", type=int, help="local/dev port (default: next free from 8010)")
    parser.add_argument("--skip-sync", action="store_true", help="do not run uv lock/sync, ruff and the OpenAPI export")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be written")
    args = parser.parse_args()

    adding = args.add_module is not None
    service_dir = validate_service_name(args.name, new=not adding)
    module, singular = module_names(args.add_module if adding else args.module, args.singular)
    if (service_dir / "app" / "modules" / module).exists():
        sys.exit(f"module {module!r} already exists in services/{args.name}")
    names = Names(
        service=args.name, port=args.port or (0 if adding else next_free_port()), entities=module, entity=singular
    )

    writer = Writer(dry_run=args.dry_run)
    if not adding:
        stage_service(writer, names)
    stage_demo_module(writer, names, initial_migration=not adding)
    writer.flush()
    if args.dry_run:
        return 0

    ok = args.skip_sync or run_tooling(service_dir, lock=not adding)
    rel = f"services/{args.name}"
    kebab = module.replace("_", "-")
    if adding:
        print(
            f"\nDemo module {module!r} added to {args.name!r}. Next, from {rel}:\n"
            f'  uv run alembic revision --autogenerate -m "create {module}"   # review it, then\n'
            "  uv run task upgrade\n"
            "  uv run task test"
        )
    else:
        print(
            f"\nService {args.name!r} created in {rel} with the demo module {module!r}.\n"
            f"Next, from {rel}:\n"
            "  cp .env.example .env     # set JWT_SECRET_KEY = the identity service's SECRET_KEY\n"
            "  uv run task upgrade      # create the schema and the demo table\n"
            "  uv run task test         # every test (needs Docker)\n"
            f"  uv run task dev          # http://localhost:{names.port}/docs  ->  /v1/{kebab}/"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
