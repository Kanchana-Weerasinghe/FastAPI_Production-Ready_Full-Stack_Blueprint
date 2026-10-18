from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime

from fastapi import FastAPI, Request, Response
from sqlalchemy import func, select, text
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import models as _models  # noqa: F401  (registers every module's ORM models)
from app.api import API_ROUTERS
from app.container import Container
from app.core.config import config
from app.core.csrf import CSRFMiddleware
from app.core.database import Database
from app.core.error_handlers import EXCEPTION_HANDLERS
from app.core.errors import AuthenticationError, ServiceUnavailableError
from app.core.logging import logger, setup_logging
from app.core.metrics import (
    DB_POOL_IN_USE,
    DB_POOL_SIZE,
    OUTBOX_DEAD,
    OUTBOX_OLDEST_PENDING,
    OUTBOX_PENDING,
    render_latest,
)
from app.core.middleware import CoreMiddleware
from app.core.security import limiter, tokens_match
from app.core.telemetry import setup_sentry, setup_tracing
from app.core.versioning import deprecated
from app.shared.idempotency import IdempotencyMiddleware
from app.shared.outbox import STATUS_DEAD, STATUS_PENDING, OutboxEvents
from app.shared.utils.singleton import singleton

setup_logging()
setup_sentry()


@singleton
class AppCreator:
    """
    Application factory class responsible for initializing the FastAPI application.

    Wires together the DI container, database connections, middleware, and routes.
    """

    container: Container
    app: FastAPI
    db: Database

    def __init__(self) -> None:
        self.container = Container()
        self.db = self.container.db()

        self.app = FastAPI(
            title=config.PROJECT_NAME,
            openapi_url=f"{config.API}/openapi.json" if config.ENVIRONMENT == "development" else None,
            docs_url="/docs" if config.ENVIRONMENT == "development" else None,
            redoc_url="/redoc" if config.ENVIRONMENT == "development" else None,
            version="0.0.1",
            lifespan=self.lifespan,
            exception_handlers=EXCEPTION_HANDLERS,
        )
        self.app.state.limiter = limiter
        logger.info(
            "fastapi_app_initializing",
            project_name=config.PROJECT_NAME,
            environment=config.ENVIRONMENT,
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.app.add_middleware(
            TrustedHostMiddleware, allowed_hosts=[config.APP_DOMAIN, "*.localhost", "localhost", "127.0.0.1"]
        )
        # Added last = outermost: CoreMiddleware (request id, transaction) wraps CSRFMiddleware.
        self.app.add_middleware(CSRFMiddleware)
        self.app.add_middleware(CoreMiddleware, db=self.db)
        # Outermost: records a response only after CoreMiddleware committed the request's transaction.
        self.app.add_middleware(IdempotencyMiddleware, db=self.db)

        self.app.state.shutting_down = False

        @self.app.get("/health/live", summary="Liveness Probe", tags=["health"])
        async def liveness() -> dict[str, str]:
            """The process is up and the event loop responds. Never checks dependencies (avoids restart storms)."""
            return {"status": "alive"}

        @self.app.get("/health/ready", summary="Readiness Probe", tags=["health"])
        async def readiness() -> dict[str, str]:
            """Ready to take traffic: dependencies reachable and not shutting down. Failing removes the pod from rotation."""
            return await self.check_readiness()

        @self.app.get(
            "/health",
            summary="Health Check (alias of /health/ready)",
            tags=["health"],
            deprecated=True,
            dependencies=[deprecated(sunset=date(2027, 6, 30))],
        )
        async def health() -> dict[str, str]:
            """Backward-compatible alias of the readiness probe."""
            return await self.check_readiness()

        if config.METRICS_ENABLED:

            @self.app.get("/metrics", include_in_schema=False)
            async def metrics(request: Request) -> Response:
                """Prometheus scrape endpoint. Protect with METRICS_TOKEN or network policy; never expose publicly."""
                if config.METRICS_TOKEN is not None:
                    expected = f"Bearer {config.METRICS_TOKEN.get_secret_value()}"
                    if not tokens_match(request.headers.get("authorization", ""), expected):
                        raise AuthenticationError("Invalid metrics token", code="invalid_token")
                await self.refresh_gauges()
                body, content_type = render_latest()
                return Response(body, media_type=content_type)

        for router in API_ROUTERS:
            self.app.include_router(router)
        setup_tracing(self.app, self.db.engine)

    async def refresh_gauges(self) -> None:
        """Updates saturation/backlog gauges at scrape time."""
        pool = self.db.engine.pool
        DB_POOL_IN_USE.set(getattr(pool, "checkedout", lambda: 0)())
        DB_POOL_SIZE.set(getattr(pool, "size", lambda: 0)())
        try:
            async with self.db.session_scope() as session:
                rows = await session.execute(
                    select(OutboxEvents.status, func.count(), func.min(OutboxEvents.created_at))
                    .where(OutboxEvents.status.in_([STATUS_PENDING, STATUS_DEAD]))
                    .group_by(OutboxEvents.status)
                )
                stats = {status: (count, oldest) for status, count, oldest in rows}
        except Exception as e:
            logger.warning("metrics_outbox_query_failed", error=str(e))
            return
        pending_count, oldest = stats.get(STATUS_PENDING, (0, None))
        OUTBOX_PENDING.set(pending_count)
        OUTBOX_DEAD.set(stats.get(STATUS_DEAD, (0, None))[0])
        OUTBOX_OLDEST_PENDING.set((datetime.now(UTC) - oldest).total_seconds() if oldest else 0)

    async def check_readiness(self) -> dict[str, str]:
        if self.app.state.shutting_down:
            raise ServiceUnavailableError(detail="Shutting down", code="shutting_down")
        checks = {"database": "ok"}
        try:
            async with self.db.session_scope() as session:
                await session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error("health_check_failed", dependency="database", error=str(e))
            raise ServiceUnavailableError(detail="Database connection failed") from None
        redis = self.container.redis()
        if redis is not None:
            try:
                await redis.ping()
                checks["redis"] = "ok"
            except Exception as e:
                logger.error("health_check_failed", dependency="redis", error=str(e))
                raise ServiceUnavailableError(detail="Redis connection failed") from None
        return {"status": "ready", **checks}

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """
        Startup/shutdown lifecycle. On SIGTERM the server stops accepting connections and finishes
        in-flight requests (gunicorn --graceful-timeout); readiness flips to 503 first so the load
        balancer drains this instance, then pooled resources are closed.
        """
        yield
        app.state.shutting_down = True
        logger.info("app_shutting_down")
        await self.container.autosend_client().aclose()
        await self.container.task_queue().aclose()
        redis = self.container.redis()
        if redis is not None:
            await redis.aclose()
        await self.db.close()


app_creator: AppCreator = AppCreator()
logger.info("app_creator_initialized")

app = app_creator.app
db = app_creator.db
container = app_creator.container
