"""rename attachments.file_url to storage_key

Files are no longer served from a public static mount, so the column now holds a private
storage key relative to the upload root (e.g. `<user_id>/<uuid>.pdf`) instead of a URL.

Revision ID: 3f1a9c2b7d10
Revises: 107c27411623
Create Date: 2026-10-16 09:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f1a9c2b7d10"
down_revision: str | Sequence[str] | None = "107c27411623"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("attachments", "file_url", new_column_name="storage_key")
    # Old values were '/<upload_dir>/<user_id>/<file_name>'; strip the leading upload dir segment.
    op.execute("UPDATE attachments SET storage_key = regexp_replace(storage_key, '^/[^/]+/', '')")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE attachments SET storage_key = '/uploads/' || storage_key")
    op.alter_column("attachments", "storage_key", new_column_name="file_url")
