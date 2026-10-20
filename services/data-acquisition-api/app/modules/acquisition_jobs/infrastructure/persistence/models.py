from datetime import datetime
from uuid import UUID

from platform_kit.persistence import AuditColumnsMixin
from sqlalchemy import BigInteger, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AcquisitionJobs(AuditColumnsMixin, Base):
    """Row shape of the AcquisitionJob aggregate. Only the repository uses this class."""

    __tablename__ = "acquisition_jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0 AND attempts <= max_attempts", name="attempts_within_limit"),
        CheckConstraint("records_collected >= 0", name="records_not_negative"),
        Index("ix_acquisition_jobs_owner_status", "owner_id", "status"),
    )

    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)  # core-api user ID, no FK
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    records_collected: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
