"""
API Routes module.

Combines all route modules into a single router.
"""

from fastapi import APIRouter

from ingest_core.api.routes.analysis import router as analysis_router
from ingest_core.api.routes.assets import router as assets_router
from ingest_core.api.routes.health import router as health_router
from ingest_core.api.routes.lineage import router as lineage_router
from ingest_core.api.routes.prompts import router as prompts_router
from ingest_core.api.routes.search import router as search_router

# Main router that combines all sub-routers
router = APIRouter()

# Mount sub-routers
router.include_router(health_router)
router.include_router(assets_router)
router.include_router(analysis_router)
router.include_router(lineage_router)
router.include_router(search_router)
router.include_router(prompts_router)

__all__ = ["router"]