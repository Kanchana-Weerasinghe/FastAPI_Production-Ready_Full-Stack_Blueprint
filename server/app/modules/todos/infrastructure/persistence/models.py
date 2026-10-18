from uuid import UUID

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import BaseModel


class Todos(BaseModel):
    """Database model representing a single task (todo) item."""

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["Users"] = relationship("Users", back_populates="todos", lazy="selectin")
    attachments: Mapped[list["Attachments"]] = relationship(
        "Attachments", back_populates="todo", cascade="save-update, merge, refresh-expire, expunge"
    )

    eagers = ["user", "attachments"]
