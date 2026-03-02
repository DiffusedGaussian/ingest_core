"""
FastAPI REST API module.

Provides HTTP endpoints for:
- File ingestion
- Asset queries
- Health checks
"""

from ingest_core.api.app import create_app
from ingest_core.api.routes import router

__all__ = ["create_app", "router"]