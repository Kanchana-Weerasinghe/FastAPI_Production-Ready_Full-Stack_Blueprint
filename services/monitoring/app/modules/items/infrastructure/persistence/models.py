"""
DATABASE TABLE (SQLAlchemy model): how a Item is stored. Only the repository uses this class.

`AuditColumnsMixin` adds the columns `id`, `created_at`, `updated_at` and `version`. The table lives in
this service's own database schema (see app/db.py).

After changing this class: `uv run alembic revision --autogenerate -m "..."`, review it, `uv run task upgrade`.
"""

from platform_kit.persistence import AuditColumnsMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ItemModel(AuditColumnsMixin, Base):
    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # the database also keeps it unique
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
