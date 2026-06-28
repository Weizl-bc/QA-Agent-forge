"""Top-level API router."""

from fastapi import APIRouter

from backend.app.api.routes.business_endpoint import router as business_router
from backend.app.api.routes.company_endpoint import router as company_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.page_endpoint import router as page_router
from backend.app.api.routes.platform_endpoint import router as platform_router
from backend.app.api.routes.system_endpoint import router as system_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(company_router)
api_router.include_router(business_router)
api_router.include_router(platform_router)
api_router.include_router(system_router)
api_router.include_router(page_router)
