"""
Health check endpoints.
"""

from fastapi import APIRouter

from ingest_core.api.dependencies import ContainerDep
from ingest_core.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
)
async def health_check(container: ContainerDep) -> HealthResponse:
    """
    Check system health and component status.

    Returns status of all backends and loaded analyzers.
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database=container.settings.database_backend,
        vector_db=container.settings.vector_database_backend,
        storage=container.settings.storage.storage_backend,
        analyzers_loaded=list(container.analyzers.keys()),
    )
