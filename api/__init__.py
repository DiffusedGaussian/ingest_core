"""
FastAPI REST API module.

Provides HTTP endpoints for:
- File ingestion
- Asset queries
- Health checks
"""

from api.app import create_app
from api.routes import router

__all__ = ["create_app", "router"]