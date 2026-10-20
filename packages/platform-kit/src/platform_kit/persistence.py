"""
SQLAlchemy base for a service's own schema.

Each service declares one `Base(DeclarativeBase)` with `metadata = schema_metadata(schema)` so every
table lives in that service's schema (e.g. `data_acquisition.acquisition_jobs`). Never reference
another service's schema: store other aggregates' IDs as plain columns without foreign keys.
"""

import uuid
from datetime import datetime

from sqlalchemy import MetaData, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

NAMING_CONVENTION = {
    # Not %(column_0_label)s: with a schema it would prefix the schema name to every index.
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def schema_metadata(schema: str) -> MetaData:
    """Metadata whose tables belong to `schema`, with stable constraint names for migrations."""
    return MetaData(schema=schema, naming_convention=NAMING_CONVENTION)


class AuditColumnsMixin:
    """Identity, timestamps and optimistic-locking version shared by every aggregate table."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(default=1, nullable=False)
