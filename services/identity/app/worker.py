"""
Background worker (ARQ on Redis). Run with:  uv run arq app.worker.WorkerSettings

- Relays the transactional outbox every few seconds (emails and other side effects).
- Runs scheduled maintenance (expired auth tokens, delivered outbox events).
- Executes jobs enqueued with `TaskQueue.enqueue("<function name>", ...)`; register them in `functions`.

Jobs are retried up to `max_tries`; raise `arq.Retry(defer=seconds)` for backoff. Every job opens its
own unit of work (`db.session_scope()`), never sharing a transaction with a request.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import delete, or_

from app import models as _models  # noqa: F401  (registers every module's ORM models)
from app.container import Container
from app.core.config import config
from app.core.logging import logger, setup_logging
from app.modules.audit.infrastructure.persistence.models import AuditLogs
from app.modules.auth.infrastructure.persistence.models import OneTimeTokens, RefreshTokens
from app.shared.idempotency import IdempotencyKeys
from app.shared.outbox import STATUS_DONE, OutboxEvents, OutboxRelay

setup_logging()

OUTBOX_RETENTION = timedelta(days=7)
TOKEN_RETENTION = timedelta(days=7)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["container"] = Container()
    logger.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    container: Container = ctx["container"]
    await container.autosend_client().aclose()
    await container.db().close()
    logger.info("worker_stopped")


async def relay_outbox(ctx: dict[str, Any]) -> int:
    """Delivers due outbox events; loops while full batches keep coming."""
    relay: OutboxRelay = ctx["container"].outbox_relay()
    total = 0
    while (processed := await relay.run_once()) == config.OUTBOX_BATCH_SIZE:
        total += processed
    return total + processed


async def purge_expired_records(ctx: dict[str, Any]) -> None:
    """Applies retention: delivered outbox events, idempotency keys, auth tokens and old audit entries."""
    db = ctx["container"].db()
    now = datetime.now(UTC)
    async with db.session_scope() as session:
        await session.execute(
            delete(OutboxEvents).where(
                OutboxEvents.status == STATUS_DONE, OutboxEvents.processed_at < now - OUTBOX_RETENTION
            )
        )
        await session.execute(delete(IdempotencyKeys).where(IdempotencyKeys.expires_at < now))
        await session.execute(
            delete(AuditLogs).where(AuditLogs.created_at < now - timedelta(days=config.AUDIT_LOG_RETENTION_DAYS))
        )
        await session.execute(
            delete(RefreshTokens).where(
                or_(RefreshTokens.expires_at < now, RefreshTokens.revoked_at < now - TOKEN_RETENTION)
            )
        )
        await session.execute(
            delete(OneTimeTokens).where(
                or_(OneTimeTokens.expires_at < now - TOKEN_RETENTION, OneTimeTokens.used_at < now - TOKEN_RETENTION)
            )
        )
    logger.info("expired_records_purged")


class WorkerSettings:
    functions: list[Any] = []  # Jobs enqueued via TaskQueue.enqueue(...)
    cron_jobs = [
        cron(relay_outbox, second=set(range(0, 60, 5)), unique=True, run_at_startup=True),
        cron(purge_expired_records, hour={3}, minute={15}, unique=True),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL or "redis://localhost:6379/0")
    max_tries = 5
    job_timeout = 300
    keep_result = 3600
    health_check_interval = 30
