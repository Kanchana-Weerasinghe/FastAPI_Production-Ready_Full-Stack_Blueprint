import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Protocol

from starlette.concurrency import run_in_threadpool

from app.core.config import config
from app.core.errors import PayloadTooLargeError

CHUNK_SIZE = 1024 * 1024


class FileStorage(Protocol):
    """
    Port for binary file storage. Keys are server-generated (`<owner_id>/<uuid><ext>`), never
    derived from client input. Implementations: `LocalFileStorage` (dev / single instance) and
    `S3FileStorage` (any S3-compatible service), selected with `STORAGE_BACKEND`.
    """

    async def save(self, source: BinaryIO, owner_id: uuid.UUID, extension: str, max_bytes: int) -> tuple[str, int]: ...

    async def exists(self, key: str) -> bool: ...

    async def delete(self, key: str) -> None: ...

    async def delete_owner(self, owner_id: uuid.UUID) -> None: ...

    async def download_url(self, key: str, filename: str, media_type: str) -> str | None:
        """A short-lived URL the client can download from directly, or None to stream through the API."""
        ...

    def path(self, key: str) -> Path:
        """Local filesystem path of a key (only for backends that stream through the API)."""
        ...


def new_storage_key(owner_id: uuid.UUID, extension: str) -> str:
    return f"{owner_id}/{uuid.uuid4().hex}{extension}"


class LocalFileStorage:
    """
    Stores uploaded files on local disk, outside any public/static mount.

    Files are only reachable through authenticated, ownership-checked endpoints. Storage keys are
    generated server-side (`<owner_id>/<uuid><ext>`), so client-supplied file names never become
    part of a filesystem path (no path traversal, no overwriting another upload with the same name).
    All disk I/O runs in a worker thread to keep the event loop free.
    """

    def __init__(self, root: str | None = None) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        # Resolved lazily so a changed `config.UPLOAD_DIR` (e.g. in tests) is honoured.
        return Path(self._root or config.UPLOAD_DIR).resolve()

    def path(self, key: str) -> Path:
        """Maps a storage key to an absolute path, refusing keys that escape the storage root."""
        root = self.root
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Invalid storage key")
        return path

    async def save(self, source: BinaryIO, owner_id: uuid.UUID, extension: str, max_bytes: int) -> tuple[str, int]:
        """Streams `source` to a new file and returns `(storage_key, size)`; aborts with 413 above `max_bytes`."""
        key = new_storage_key(owner_id, extension)
        size = await run_in_threadpool(self._write, source, self.path(key), max_bytes)
        return key, size

    async def exists(self, key: str) -> bool:
        return await run_in_threadpool(self.path(key).is_file)

    async def download_url(self, key: str, filename: str, media_type: str) -> str | None:  # noqa: ARG002
        # Local files are streamed through the API (see the download endpoint).
        return None

    async def delete(self, key: str) -> None:
        await run_in_threadpool(self.path(key).unlink, missing_ok=True)

    async def delete_owner(self, owner_id: uuid.UUID) -> None:
        """Removes every file belonging to an owner (used when an account is deleted)."""
        await run_in_threadpool(shutil.rmtree, self.path(str(owner_id)), ignore_errors=True)

    @staticmethod
    def _write(source: BinaryIO, destination: Path, max_bytes: int) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with destination.open("xb") as buffer:
                while chunk := source.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > max_bytes:
                        raise PayloadTooLargeError(detail=f"File exceeds the {max_bytes} byte limit")
                    buffer.write(chunk)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return size
