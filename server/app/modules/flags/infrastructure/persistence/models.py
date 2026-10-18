from typing import Any

from sqlalchemy import Boolean, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, TEXT, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import BaseModel


class FeatureFlags(BaseModel):
    """
    A runtime feature switch. Lets risky features ship dark, roll out gradually and be turned off
    without a deploy. Evaluation: disabled -> off; role in `roles` -> on; otherwise a deterministic
    percentage bucket of the user id (`rollout_percentage`).
    """

    key: Mapped[str] = mapped_column(VARCHAR(100), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(TEXT, nullable=False, server_default=text("''"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("100"))
    # Roles that always get the feature when enabled (e.g. ["admin"] for internal dogfooding).
    roles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
