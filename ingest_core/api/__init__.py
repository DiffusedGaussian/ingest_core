"""
FastAPI REST API module.

Provides HTTP endpoints for:
- Asset management (CRUD)
- Analysis pipeline
- Lineage tracking
- Search and discovery

Structure:
- app.py: Application factory
- dependencies.py: DI setup
- schemas.py: Request/response models
- routes/: Endpoint handlers
"""

from ingest_core.api.app import app, create_app
from ingest_core.api.routes import router

__all__ = ["create_app", "app", "router"]
