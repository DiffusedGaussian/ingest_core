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

from ingest_core.config.settings import (
    APISettings,
    GeminiSettings,
    LocalVLMSettings,
    LoggingSettings,
    MongoDBSettings,
    PathSettings,
    PluginSettings,
    ProcessingSettings,
    QdrantSettings,
    Settings,
    SQLiteSettings,
    StorageSettings,
    WhisperSettings,
    get_settings,
)

__all__ = [
    "Settings",
    "get_settings",
    "PathSettings",
    "StorageSettings",
    "MongoDBSettings",
    "QdrantSettings",
    "SQLiteSettings",
    "GeminiSettings",
    "LocalVLMSettings",
    "WhisperSettings",
    "ProcessingSettings",
    "APISettings",
    "LoggingSettings",
    "PluginSettings",
]
