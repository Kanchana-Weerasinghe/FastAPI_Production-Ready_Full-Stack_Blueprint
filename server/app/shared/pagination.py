"""
Opaque cursors for keyset ("cursor") pagination.

Offset pagination (`page`/`pageSize`) gets slower with every page (`OFFSET n` scans n rows) and skips or
repeats rows when data changes between requests. For large or append-heavy tables, list endpoints use
keyset pagination on `(created_at, id)`: constant cost per page and stable under concurrent inserts.
Cursors are opaque to clients (base64url JSON) so the encoding can change without an API change.
"""

import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from app.core.errors import BadRequestError


def encode_cursor(created_at: datetime, row_id: UUID) -> str:
    raw = json.dumps({"c": created_at.isoformat(), "i": str(row_id)}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        return datetime.fromisoformat(data["c"]), UUID(data["i"])
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeDecodeError) as e:
        raise BadRequestError("Invalid pagination cursor", code="invalid_cursor") from e
