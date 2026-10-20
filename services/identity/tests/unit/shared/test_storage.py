import uuid
from io import BytesIO
from pathlib import Path

import pytest

from app.shared.storage import LocalFileStorage


def test_path_rejects_keys_escaping_root(tmp_path: Path) -> None:
    """Test that storage keys resolving outside the storage root are refused."""
    storage = LocalFileStorage(root=str(tmp_path))
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.path("../outside.pdf")


async def test_save_and_delete_owner(tmp_path: Path) -> None:
    """Test that delete_owner removes every file stored for that owner and nothing else."""
    storage = LocalFileStorage(root=str(tmp_path))
    owner, other = uuid.uuid4(), uuid.uuid4()
    owner_key, size = await storage.save(BytesIO(b"abc"), owner, ".pdf", max_bytes=10)
    other_key, _ = await storage.save(BytesIO(b"xyz"), other, ".pdf", max_bytes=10)
    assert size == 3
    await storage.delete_owner(owner)
    assert not await storage.exists(owner_key)
    assert await storage.exists(other_key)
