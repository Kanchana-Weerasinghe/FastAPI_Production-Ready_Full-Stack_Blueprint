"""
Exports the OpenAPI document (the API contract) to `server/openapi.json`.

The file is committed: CI regenerates it and fails when it is out of date, and checks the diff against
the target branch for breaking changes (oasdiff). The web app generates its TypeScript types from it
(`pnpm gen:api`).

    uv run python scripts/export_openapi.py            # write
    uv run python scripts/export_openapi.py --check    # exit 1 if the committed file is stale
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

TARGET = ROOT / "openapi.json"


def main() -> None:
    document = json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != document:
            print("openapi.json is out of date: run `uv run python scripts/export_openapi.py` and commit it.")
            sys.exit(1)
        print("openapi.json is up to date.")
        return
    TARGET.write_text(document, encoding="utf-8", newline="\n")
    print(f"Wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
