"""
FastAPI application factory.

Inspired by production patterns from Diffusers and other ML libraries:
- Lifespan management for clean startup/shutdown
- Structured logging
- CORS configuration
- OpenAPI documentation
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog import get_logger

from ingest_core.api.routes import router
from ingest_core.container import get_container

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles:
    - Database connections
    - Vector DB initialization
    - Analyzer loading
    - Graceful shutdown
    """
    logger.info("Starting ingest-core...")

    # Startup
    container = get_container()
    await container.startup()

    logger.info(
        "ingest-core ready",
        database=container.settings.database_backend,
        vector_db=container.settings.vector_database_backend,
        storage=container.settings.storage.storage_backend,
        analyzers=list(container.analyzers.keys()),
    )

    yield

    # Shutdown
    logger.info("Shutting down ingest-core...")
    await container.shutdown()
    logger.info("ingest-core stopped")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance

    Example:
        >>> app = create_app()
        >>> # Run with uvicorn
        >>> import uvicorn
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    app = FastAPI(
        title="ingest-core",
        description="""
# Foundation Data Layer for Generative AI

**ingest-core** provides infrastructure for tracking and managing media assets
across generative AI workflows.

## Key Features

- **Asset Management**: Upload, store, and retrieve images, videos, and 3D assets
- **Analysis Pipeline**: Extract metadata, generate embeddings, detect objects
- **Lineage Tracking**: Track relationships between source materials and generated outputs
- **Similarity Search**: Find visually similar assets using embeddings
- **Multi-Backend**: Supports local/GCS storage, MongoDB/SQLite, Qdrant/FAISS

## Workflow

1. **Ingest** source materials (reference images, style guides)
2. **Analyze** to extract features and generate embeddings
3. **Generate** content using external tools (Flux, Runway, etc.)
4. **Track** lineage between inputs and outputs
5. **Evaluate** results and iterate

## API Structure

- `/api/v1/assets` - Asset CRUD operations
- `/api/v1/assets/{id}/analyze` - Trigger analysis pipeline
- `/api/v1/assets/{id}/lineage` - Query lineage relationships
- `/api/v1/search` - Search by text, similarity, or filters
- `/api/v1/lineage` - Create lineage records
        """,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "assets",
                "description": "Asset management operations",
            },
            {
                "name": "analysis",
                "description": "Analysis pipeline operations",
            },
            {
                "name": "lineage",
                "description": "Lineage tracking operations",
            },
            {
                "name": "search",
                "description": "Search and discovery operations",
            },
        ],
    )

    # CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API router
    app.include_router(router, prefix="/api/v1")

    # Root health check (outside versioned API)
    @app.get("/health", tags=["health"])
    async def health_check():
        """
        Basic health check endpoint.

        For detailed health status, use `/api/v1/health`.
        """
        return {"status": "healthy", "service": "ingest-core"}

    @app.get("/", tags=["health"])
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "ingest-core",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        }

    return app


# Application instance for uvicorn
app = create_app()
