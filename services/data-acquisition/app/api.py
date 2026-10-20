"""Router registry: every module router is mounted here under its API version."""

from fastapi import APIRouter

from app.modules.acquisition_jobs.router import router as acquisition_jobs_router

api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(acquisition_jobs_router)

API_ROUTERS = [api_v1]
