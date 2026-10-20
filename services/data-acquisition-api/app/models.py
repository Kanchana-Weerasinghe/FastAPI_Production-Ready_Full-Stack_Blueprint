"""Model registry for Alembic and tests: import every module's ORM models here."""

from app.db import Base
from app.modules.acquisition_jobs.infrastructure.persistence.models import AcquisitionJobs

__all__ = ["AcquisitionJobs", "Base"]
