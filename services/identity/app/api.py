"""
API router registry: every module router is mounted here under its API version.

Versioning policy (see docs/adr/0003-api-versioning.md): a version prefix only changes for
breaking changes; additive changes ship in place. Deprecated routes keep working until their
announced sunset date and advertise it via `Deprecation`/`Sunset` headers.
"""

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.users.router import admin_router as users_admin_router
from app.modules.users.router import router as users_router

# [scaffold:router-imports]

api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(auth_router)

api_v2 = APIRouter(prefix="/v2")
api_v2.include_router(users_router)
api_v2.include_router(users_admin_router)
api_v2.include_router(audit_router)
# [scaffold:router-includes]

API_ROUTERS = [api_v1, api_v2]
