"""create acquisition jobs

Revision ID: a1c4e7d2b905
Revises:
Create Date: 2026-10-20 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.config import config

# revision identifiers, used by Alembic.
revision: str = "a1c4e7d2b905"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = config.DB_SCHEMA


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "acquisition_jobs",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("records_collected", sa.BigInteger(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "attempts >= 0 AND attempts <= max_attempts", name=op.f("ck_acquisition_jobs_attempts_within_limit")
        ),
        sa.CheckConstraint("records_collected >= 0", name=op.f("ck_acquisition_jobs_records_not_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_jobs")),
        schema=SCHEMA,
    )
    op.create_index("ix_acquisition_jobs_owner_status", "acquisition_jobs", ["owner_id", "status"], schema=SCHEMA)
    op.create_index(op.f("ix_acquisition_jobs_status"), "acquisition_jobs", ["status"], schema=SCHEMA)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_acquisition_jobs_status"), table_name="acquisition_jobs", schema=SCHEMA)
    op.drop_index("ix_acquisition_jobs_owner_status", table_name="acquisition_jobs", schema=SCHEMA)
    op.drop_table("acquisition_jobs", schema=SCHEMA)
