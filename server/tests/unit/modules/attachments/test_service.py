import uuid
from io import BytesIO
from pathlib import Path

import pytest

from app.core.config import config
from app.core.errors import BadRequestError, NotFoundError, PayloadTooLargeError
from app.modules.attachments.service import AttachmentService
from app.modules.users.infrastructure.persistence.models import Users
from tests.mocks.attachment_repository import MockAttachmentRepository
from tests.mocks.uow import FakeUnitOfWork


def _user() -> Users:
    return Users(
        id=uuid.uuid4(),
        email="test_user@example.com",
        username="testuser",
        _password="hashed_password",
        created_by="system",
        updated_by="system",
    )


async def _upload(service: AttachmentService, content: bytes, filename: str, owner: Users | None = None):  # type: ignore[no-untyped-def]
    return await service.add_attachment(BytesIO(content), filename, None, owner or _user())


async def test_add_attachment_success(
    attachment_service: AttachmentService,
    mock_attachment_repository: MockAttachmentRepository,
) -> None:
    """Test that uploading an allowed file stores it under a server-generated key in private storage and registers it."""
    owner = _user()
    attachment = await _upload(attachment_service, b"fake pdf bytes", "avatar.pdf", owner)
    assert len(mock_attachment_repository.attachments_db) == 1
    assert attachment.file_name == "avatar.pdf"
    assert attachment.user_id == owner.id
    assert attachment.file_type == "application/pdf"
    assert attachment.file_size == len(b"fake pdf bytes")
    assert attachment.storage_key.startswith(f"{owner.id}/")
    assert attachment.storage_key.endswith(".pdf")
    assert "avatar" not in attachment.storage_key
    assert (Path(config.UPLOAD_DIR).resolve() / attachment.storage_key).read_bytes() == b"fake pdf bytes"


async def test_add_attachment_same_name_does_not_overwrite(attachment_service: AttachmentService) -> None:
    """Test that two uploads with the same file name are stored as separate files instead of overwriting each other."""
    owner = _user()
    first = await _upload(attachment_service, b"one", "a.pdf", owner)
    second = await _upload(attachment_service, b"two", "a.pdf", owner)
    assert first.storage_key != second.storage_key
    assert (await attachment_service.get_file_path(first)).read_bytes() == b"one"
    assert (await attachment_service.get_file_path(second)).read_bytes() == b"two"


async def test_add_attachment_strips_path_from_filename(attachment_service: AttachmentService) -> None:
    """Test that a client-supplied file name containing directory traversal is reduced to its base name."""
    attachment = await _upload(attachment_service, b"content", "../../etc/evil.pdf")
    assert attachment.file_name == "evil.pdf"
    assert (await attachment_service.get_file_path(attachment)).is_relative_to(Path(config.UPLOAD_DIR).resolve())


async def test_add_attachment_too_large(
    attachment_service: AttachmentService,
    mock_attachment_repository: MockAttachmentRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a file above MAX_UPLOAD_SIZE_BYTES raises 413 and leaves neither a file nor a database record behind."""
    monkeypatch.setattr(config, "MAX_UPLOAD_SIZE_BYTES", 4)
    owner = _user()
    with pytest.raises(PayloadTooLargeError):
        await _upload(attachment_service, b"too many bytes", "big.pdf", owner)
    assert mock_attachment_repository.attachments_db == []
    user_dir = Path(config.UPLOAD_DIR) / str(owner.id)
    assert not user_dir.exists() or not any(user_dir.iterdir())


async def test_add_attachment_db_failure_removes_file(
    attachment_service: AttachmentService,
    mock_attachment_repository: MockAttachmentRepository,
) -> None:
    """Test that the stored file is deleted again when persisting the attachment record fails."""
    mock_attachment_repository.create.side_effect = RuntimeError("db down")
    owner = _user()
    with pytest.raises(RuntimeError):
        await _upload(attachment_service, b"x", "a.pdf", owner)
    assert not any((Path(config.UPLOAD_DIR) / str(owner.id)).iterdir())


async def test_add_attachment_missing_filename(attachment_service: AttachmentService) -> None:
    """Test that attempting to upload a file with an empty filename raises a BadRequestError."""
    with pytest.raises(BadRequestError) as exc_info:
        await _upload(attachment_service, b"content", "")
    assert exc_info.value.code == "file_name_missing"


async def test_add_attachment_invalid_extension(attachment_service: AttachmentService) -> None:
    """Test that attempting to upload a file with an unapproved extension (like .exe) raises a BadRequestError."""
    with pytest.raises(BadRequestError) as exc_info:
        await _upload(attachment_service, b"content", "malicious.exe")
    assert exc_info.value.code == "file_type_not_allowed"


async def test_remove_attachment_deletes_file_only_after_commit(
    attachment_service: AttachmentService,
    mock_attachment_repository: MockAttachmentRepository,
    fake_uow: FakeUnitOfWork,
) -> None:
    """Test that remove deletes the record immediately but the stored file only once the transaction commits."""
    attachment = await _upload(attachment_service, b"pdf contents", "report.pdf")
    file_path = await attachment_service.get_file_path(attachment)
    await attachment_service.remove(attachment)
    assert mock_attachment_repository.attachments_db == []
    assert file_path.exists()
    await fake_uow.commit()
    assert not file_path.exists()


async def test_link_to_todo_rejects_other_owner(
    attachment_service: AttachmentService,
) -> None:
    """Test that only the attachment owner's todos can link it; others get a not-found error."""
    attachment = await _upload(attachment_service, b"x", "a.pdf")
    with pytest.raises(NotFoundError) as exc_info:
        await attachment_service.link_to_todo([attachment.id], uuid.uuid4(), uuid.uuid4())
    assert exc_info.value.code == "attachment_not_found"
    assert attachment.todo_id is None


async def test_link_to_todo_success(attachment_service: AttachmentService) -> None:
    """Test that an owner's attachment is linked to the given todo."""
    owner = _user()
    attachment = await _upload(attachment_service, b"x", "a.pdf", owner)
    todo_id = uuid.uuid4()
    await attachment_service.link_to_todo([attachment.id], todo_id, owner.id)
    assert (await attachment_service.get_by_id(attachment.id)).todo_id == todo_id


async def test_get_file_path_missing_on_disk(
    attachment_service: AttachmentService,
    mock_attachment_repository: MockAttachmentRepository,
) -> None:
    """Test that resolving an attachment whose file is missing on disk raises NotFoundError."""
    attachment = mock_attachment_repository._mock_create(
        {
            "user_id": uuid.uuid4(),
            "file_name": "missing.pdf",
            "storage_key": f"{uuid.uuid4()}/missing.pdf",
            "file_size": 12,
            "file_type": "application/pdf",
        }
    )
    with pytest.raises(NotFoundError, match="File not found on disk"):
        await attachment_service.get_file_path(await attachment_service.get_by_id(attachment.id))
