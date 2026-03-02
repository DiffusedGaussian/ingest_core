"""
Configuration module using Pydantic v2 Settings.

Handles all environment variables and configuration for:
- Paths and directories
- Storage backends (local, GCS)
- Database connections (MongoDB, Qdrant, SQLite)
- VLM providers (Gemini, local models)
- Processing parameters
- API server settings
"""

from ingest_core.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]