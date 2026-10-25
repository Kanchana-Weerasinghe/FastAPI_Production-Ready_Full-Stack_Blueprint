"""
Model registry: imports every module's ORM models so `BaseModel.metadata` is complete.

Used by Alembic (autogenerate) and the test suite. Add new modules' models here
(`scripts/new_module.py` does it for you).
"""

from app.modules.audit.infrastructure.persistence.models import AuditLogs
from app.modules.auth.infrastructure.persistence.models import OneTimeTokens, RefreshTokens
from app.modules.users.infrastructure.persistence.models import Users

# [scaffold:model-imports]
from app.shared.idempotency import IdempotencyKeys
from app.shared.models import BaseModel
from app.shared.outbox import OutboxEvents

__all__ = [
    "BaseModel",
    "Users",
    "RefreshTokens",
    "OneTimeTokens",
    "OutboxEvents",
    "AuditLogs",
    "IdempotencyKeys",
    # [scaffold:model-exports]
]
