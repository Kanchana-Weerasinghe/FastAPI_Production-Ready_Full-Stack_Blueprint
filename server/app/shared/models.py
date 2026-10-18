import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import TIMESTAMP, Integer, MetaData, func, text
from sqlalchemy.dialects.postgresql import BOOLEAN, VARCHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    """
    Base class for all database models.

    Includes standard audit columns (id, is_active, is_deleted, timestamps), a `version` column for
    optimistic locking and automatic table name generation.

    Optimistic locking: every ORM UPDATE runs `... WHERE id = :id AND version = :loaded_version` and
    increments `version`; if another transaction changed the row first, SQLAlchemy raises
    `StaleDataError`, which repositories map to 409 `concurrent_modification`. APIs expose the version
    as an ETag so clients can send `If-Match` (412 on mismatch).
    """

    __abstract__ = True

    AUDIT_COLUMNS = {"is_active", "is_deleted", "created_at", "updated_at", "created_by", "updated_by"}

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

    @declared_attr.directive
    def __tablename__(self: Any) -> str:
        table_name = re.sub("(?<!^)(?=[A-Z])", "_", self.__name__).lower()
        return table_name

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    is_active: Mapped[bool] = mapped_column(BOOLEAN, server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(BOOLEAN, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    updated_by: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"version_id_col": cls.__table__.c.version}
