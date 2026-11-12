"""
Adds a new module to an existing domain service (created by new_service.py), filled with a simple,
commented example that shows every concept of the architecture once (then replace it with the real rules):

    A <Entity> has an id, a name, a code (e.g. "ITM-001") and a status (active / archived).
    Value objects: name and code checks.   Entity rules: an archived one cannot change; delete only archived.
    Policy: the code must be unique.       Events: <Entity>Created, <Entity>Archived (published after commit).
    Endpoints: create, list (?status=), get, update, :archive, :restore, delete.

    python scripts/new_module.py <service> <module>                    # e.g. monitoring items
    python scripts/new_module.py <service> <module> --singular <name>  # when the automatic singular is wrong
    python scripts/new_module.py <service> <module> --dry-run          # show what would be written

Every layer folder of the architecture gets its file:

    app/modules/<module>/
    ├── README.md          the example, the endpoints, one request followed through the files
    ├── domain/            entities.py, value_objects.py, policies.py, events.py, exceptions.py
    ├── application/
    │   ├── ports/         <entity>_repository.py, event_publisher.py
    │   └── use_cases/     <entity>_use_cases.py   (create, get, list, update, archive, restore, delete)
    ├── infrastructure/    logging_event_publisher.py, persistence/models.py, persistence/sqlalchemy_<entity>_repository.py
    ├── schemas.py, router.py, container.py, public.py
    tests/unit/<module>/   fakes.py, test_domain.py, test_use_cases.py
    tests/integrations/test_<module>_api.py
    migrations/versions/<rev>_create_<module>.py   (chained to the current head)

It also mounts the router (app/api.py), registers the model (app/models.py) and the container
(app/container.py), and grants the seven operations to the `user` and `admin` roles in
config/access-control.json. Then ruff + OpenAPI export.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from service_generator.engine import (
    Names,
    Writer,
    module_names,
    run_tooling,
    stage_boilerplate_module,
    validate_service_name,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("service", help="an existing service under services/, e.g. monitoring")
    parser.add_argument("module", help="module name, snake_case, e.g. accession_management or samples")
    parser.add_argument("--singular", help="singular of the module name, when the automatic one is wrong")
    parser.add_argument("--skip-sync", action="store_true", help="do not run uv sync, ruff and the OpenAPI export")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be written")
    args = parser.parse_args()

    service_dir = validate_service_name(args.service, new=False)
    module, singular = module_names(args.module, args.singular)
    if (service_dir / "app" / "modules" / module).exists():
        sys.exit(f"module {module!r} already exists in services/{args.service}")
    names = Names(service=args.service, port=0, entities=module, entity=singular)

    writer = Writer(dry_run=args.dry_run)
    stage_boilerplate_module(writer, names)
    writer.flush()
    if args.dry_run:
        return 0

    ok = args.skip_sync or run_tooling(service_dir, lock=False)
    print(
        f"\nModule {module!r} added to {args.service!r}: CRUD on /v1/{module.replace('_', '-')}/ "
        f"(read app/modules/{module}/README.md first).\n"
        f"Next, from services/{args.service}:\n"
        "  uv run task upgrade       # create the table\n"
        "  uv run task test          # unit + integration tests (needs Docker)\n"
        "  uv run task dev           # try it in /docs\n"
        f"Then replace the boilerplate in app/modules/{module}/ with the real rules."
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
