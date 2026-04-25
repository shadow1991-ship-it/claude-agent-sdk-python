from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.assets import router as assets_router
from app.api.v1.scans import router as scans_router
from app.api.v1.reports import router as reports_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router)
v1_router.include_router(assets_router)
v1_router.include_router(scans_router)
v1_router.include_router(reports_router)
