"""
FastAPI application factory.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ingest_core.api.routes import router
from ingest_core.container import get_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    container = get_container()
    await container.startup()

    yield

    # Shutdown
    await container.shutdown()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application
    """
    app = FastAPI(
        title="ingest-core",
        description="Foundation data layer for generative AI",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app