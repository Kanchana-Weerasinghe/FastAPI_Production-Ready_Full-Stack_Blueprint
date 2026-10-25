"""drop todos

The todos example module was removed so the template ships without a sample business entity; new
entities follow the User walkthrough in docs/index.html. Upgrading drops the table and its data;
downgrading recreates the empty table in its last schema.

Revision ID: f2a9d4c7e813
Revises: e7b3c9a1f052
Create Date: 2026-10-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a9d4c7e813"
down_revision: str | Sequence[str] | None = "e7b3c9a1f052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_todos_user_id"), table_name="todos")
    op.drop_table("todos")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "todos",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("is_completed", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_deleted", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.VARCHAR(length=100), nullable=False),
        sa.Column("updated_by", sa.VARCHAR(length=100), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_todos_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_todos")),
    )
    op.create_index(op.f("ix_todos_user_id"), "todos", ["user_id"], unique=False)
