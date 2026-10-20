"""drop attachments and feature flags

The attachments and feature-flags modules were removed so the template keeps a single example
business entity (todos). Upgrading drops their tables and data; downgrading recreates the empty
tables in their last schema.

Revision ID: e7b3c9a1f052
Revises: d4a8c2e1f937
Create Date: 2026-10-20 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e7b3c9a1f052"
down_revision: str | Sequence[str] | None = "d4a8c2e1f937"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.VARCHAR(length=100), nullable=False),
        sa.Column("updated_by", sa.VARCHAR(length=100), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_feature_flags_key"), table_name="feature_flags")
    op.drop_table("feature_flags")
    op.drop_index(op.f("ix_attachments_user_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_todo_id"), table_name="attachments")
    op.drop_table("attachments")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "attachments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("todo_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.TEXT(), nullable=False),
        sa.Column("storage_key", sa.TEXT(), nullable=False),
        sa.Column("file_size", sa.BIGINT(), nullable=False),
        sa.Column("file_type", sa.TEXT(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(
            ["todo_id"], ["todos.id"], name=op.f("fk_attachments_todo_id_todos"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_attachments_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
    )
    op.create_index(op.f("ix_attachments_todo_id"), "attachments", ["todo_id"], unique=False)
    op.create_index(op.f("ix_attachments_user_id"), "attachments", ["user_id"], unique=False)
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.VARCHAR(length=100), nullable=False),
        sa.Column("description", sa.TEXT(), server_default=sa.text("''"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("rollout_percentage", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column(
            "roles", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feature_flags")),
    )
    op.create_index(op.f("ix_feature_flags_key"), "feature_flags", ["key"], unique=True)
