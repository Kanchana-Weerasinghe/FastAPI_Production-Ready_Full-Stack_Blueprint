"""Router registry: every module router is mounted here under its API version."""

from fastapi import APIRouter
from app.modules.items.router import router as items_router

api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(items_router)

API_ROUTERS = [api_v1]
