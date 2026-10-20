from datetime import timedelta
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings


class TaskQueue:
    """
    Enqueues background jobs on the ARQ worker (`app/worker.py`), for slow work that must not run in
    the request: reports, exports, bulk operations, webhooks.

    Jobs are retried by the worker (`max_tries`, raise `arq.Retry(defer=...)` for backoff). For side
    effects that must happen exactly when a transaction commits, publish an outbox event instead.
    Pass a deterministic `job_id` to deduplicate.
    """

    def __init__(self, redis_url: str | None) -> None:
        self._redis_url = redis_url
        self._pool: ArqRedis | None = None

    async def enqueue(
        self, function: str, *args: Any, job_id: str | None = None, defer_by: timedelta | None = None, **kwargs: Any
    ) -> str | None:
        if not self._redis_url:
            raise RuntimeError("REDIS_URL must be configured to enqueue background jobs")
        if self._pool is None:
            self._pool = await create_pool(RedisSettings.from_dsn(self._redis_url))
        job = await self._pool.enqueue_job(function, *args, _job_id=job_id, _defer_by=defer_by, **kwargs)
        return job.job_id if job else None

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
