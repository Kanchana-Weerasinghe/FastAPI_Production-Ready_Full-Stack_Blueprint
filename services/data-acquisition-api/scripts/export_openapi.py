"""
Exports this service's OpenAPI contract to `services/data-acquisition-api/openapi.json`.

    uv run python scripts/export_openapi.py            # write
    uv run python scripts/export_openapi.py --check    # exit 1 if the committed file is stale
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

TARGET = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> int:
    document = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != document:
            print("openapi.json is out of date: run `uv run task openapi` and commit it.")
            return 1
        return 0
    TARGET.write_text(document, encoding="utf-8")
    print(f"Wrote {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
