from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import BIGINT, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import BaseModel


class Attachments(BaseModel):
    """Database model representing a file attachment linked to a user or todo."""

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    todo_id: Mapped[UUID | None] = mapped_column(ForeignKey("todos.id", ondelete="SET NULL"), nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    storage_key: Mapped[str] = mapped_column(TEXT, nullable=False)
    file_size: Mapped[int] = mapped_column(BIGINT, nullable=False)
    file_type: Mapped[str] = mapped_column(TEXT, nullable=False)

    user: Mapped["Users"] = relationship("Users", back_populates="attachments")
    todo: Mapped["Todos"] = relationship("Todos", back_populates="attachments")

    eagers = ["user", "todo"]
