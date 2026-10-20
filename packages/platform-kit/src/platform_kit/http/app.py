"""Builds a domain service's FastAPI app with the shared cross-cutting setup."""

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from platform_kit.database import Database
from platform_kit.http.health import health_router
from platform_kit.http.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from platform_kit.http.problems import exception_handlers
from platform_kit.logging import logger
from platform_kit.settings import ServiceSettings


def create_service_app(
    *,
    settings: ServiceSettings,
    db: Database,
    routers: Sequence[APIRouter],
    title: str,
    description: str = "",
) -> FastAPI:
    """Wires middleware, RFC 9457 handlers, health probes and the service's versioned routers."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("service_started", environment=settings.ENVIRONMENT)
        yield
        await db.close()
        logger.info("service_stopped")

    app = FastAPI(
        title=title,
        description=description,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        # Interactive docs only outside production; the OpenAPI contract is exported to a file.
        docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
        redoc_url=None,
    )
    for exc_type, handler in exception_handlers(settings.PROBLEM_TYPE_BASE_URI).items():
        app.add_exception_handler(exc_type, handler)
    app.add_middleware(
        RequestContextMiddleware,
        db=db,
        max_body_bytes=settings.MAX_REQUEST_BODY_BYTES,
        problem_base_uri=settings.PROBLEM_TYPE_BASE_URI,
    )
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "If-Match", REQUEST_ID_HEADER],
            expose_headers=["ETag", REQUEST_ID_HEADER],
        )
    app.include_router(health_router(db))
    for router in routers:
        app.include_router(router)
    return app
