from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attachments.infrastructure.persistence.repository import AttachmentRepository
from tests.factories import create_attachment, create_user


async def test_create_attachment_success(
    attachment_repository: AttachmentRepository,
    db_session: AsyncSession,
) -> None:
    """Test that AttachmentRepository successfully persists an Attachment model linked to a user in the database."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    attachment_data = {
        "user_id": user.id,
        "file_name": "repo_test.pdf",
        "storage_key": f"{user.id}/repo_test.pdf",
        "file_size": 100,
        "file_type": "application/pdf",
        "created_by": "system",
        "updated_by": "system",
    }
    db_attachment = await attachment_repository.create(attachment_data)
    assert db_attachment.id is not None
    assert db_attachment.user_id == user.id


async def test_read_attachment_by_id_success(
    attachment_repository: AttachmentRepository,
    db_session: AsyncSession,
) -> None:
    """Test that AttachmentRepository successfully retrieves a persisted Attachment by its primary key UUID."""
    user = create_user()
    db_session.add(user)
    await db_session.flush()
    attachment_data = create_attachment(user_id=user.id, count=1)[0]
    db_session.add(attachment_data)
    await db_session.flush()
    db_attachment = await attachment_repository.read_by_id(attachment_data.id)
    assert db_attachment.file_name == attachment_data.file_name
