"""Kubernetes probes: liveness never touches dependencies; readiness checks the database."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from platform_kit.database import Database
from platform_kit.logging import logger


def health_router(db: Database) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", summary="Liveness Probe")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready", summary="Readiness Probe")
    async def ready() -> JSONResponse:
        try:
            async with db.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning("readiness_check_failed", dependency="database", error=str(e))
            return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
        return JSONResponse(content={"status": "ok", "database": "up"})

    return router
