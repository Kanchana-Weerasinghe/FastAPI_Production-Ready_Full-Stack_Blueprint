"""Model registry for Alembic and tests: import every module's ORM models here."""

from app.db import Base
from app.modules.items.infrastructure.persistence.models import ItemModel  # noqa: F401

__all__ = ["Base"]
