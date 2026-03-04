"""
Pydantic v2 Settings configuration.

This module defines all configuration options for ingest-core using
Pydantic's BaseSettings for automatic environment variable loading.

Settings are organized into logical groups:
- PathSettings: All directory paths
- StorageSettings: File storage backend config
- MongoDBSettings: Document store config
- QdrantSettings: Vector store config  
- SQLiteSettings: Lightweight local DB config
- GeminiSettings: Google Gemini VLM config
- LocalVLMSettings: Local model config (LLaVA)
- WhisperSettings: Audio transcription config
- ProcessingSettings: Media processing parameters
- APISettings: FastAPI server config
- LoggingSettings: Structured logging config
- PluginSettings: Analyzer plugin system config

Usage:
    from ingest_core.config import get_settings

    settings = get_settings()
    print(settings.paths.data_dir)
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PathSettings(BaseSettings):
    """File system path configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    data_dir: Path = Field(default=Path("./data"), description="Root data directory")
    upload_dir: Path = Field(default=Path("./data/uploads"), description="Incoming files")
    processed_dir: Path = Field(default=Path("./data/processed"), description="Successfully processed")
    failed_dir: Path = Field(default=Path("./data/failed"), description="Failed processing")
    temp_dir: Path = Field(default=Path("./data/temp"), description="Temporary files")

    @field_validator("data_dir", "upload_dir", "processed_dir", "failed_dir", "temp_dir", mode="after")
    @classmethod
    def ensure_path(cls, v: Path) -> Path:
        """Ensure path is absolute and exists."""
        path = v if v.is_absolute() else Path.cwd() / v
        path.mkdir(parents=True, exist_ok=True)
        return path


class StorageSettings(BaseSettings):
    """File storage backend configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    storage_backend: Literal["local", "gcs"] = Field(default="local")
    gcs_bucket: str | None = Field(default=None, description="GCS bucket name")
    gcs_project_id: str | None = Field(default=None, description="GCP project ID")


class MongoDBSettings(BaseSettings):
    """MongoDB document store configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="ingest_core")


class QdrantSettings(BaseSettings):
    """Qdrant vector store configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="media_embeddings")
    qdrant_api_key: str | None = Field(default=None, description="Optional API key for Qdrant Cloud")


class SQLiteSettings(BaseSettings):
    """SQLite lightweight storage configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    sqlite_path: Path = Field(default=Path("./data/ingest_core.db"))


class GeminiSettings(BaseSettings):
    """Google Gemini VLM configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    api_key: str | None = Field(default=None)
    model: str = Field(default="gemini-3-flash-preview")


class LocalVLMSettings(BaseSettings):
    """Local VLM (LLaVA) configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    local_vlm_enabled: bool = Field(default=False)
    local_vlm_model: str = Field(default="llava-hf/llava-1.5-7b-hf")
    local_vlm_device: Literal["cuda", "cpu", "mps"] = Field(default="cuda")


class WhisperSettings(BaseSettings):
    """Whisper audio transcription configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    whisper_model: Literal["tiny", "base", "small", "medium", "large"] = Field(default="base")
    whisper_device: Literal["cuda", "cpu"] = Field(default="cuda")


class ProcessingSettings(BaseSettings):
    """Media processing parameters."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    max_file_size_mb: int = Field(default=500)
    video_max_duration_seconds: int = Field(default=30)
    keyframe_extraction_method: Literal["scene", "interval", "uniform"] = Field(default="scene")
    keyframe_max_count: int = Field(default=10)


class APISettings(BaseSettings):
    """FastAPI server configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)
    api_reload: bool = Field(default=True)


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")


class PluginSettings(BaseSettings):
    """Analyzer plugin system configuration."""

    model_config = SettingsConfigDict(env_prefix="INGEST_")

    plugins_dir: Path = Field(default=Path("./plugins"))
    enabled_analyzers: str = Field(
        default="exif,phash,objects,vlm",
        description="Comma-separated list of enabled analyzers"
    )

    @property
    def analyzer_list(self) -> list[str]:
        """Parse enabled analyzers into a list."""
        return [a.strip() for a in self.enabled_analyzers.split(",") if a.strip()]


class Settings(BaseSettings):
    """
    Main settings container aggregating all configuration groups.

    This is the primary interface for accessing configuration throughout
    the application. Use get_settings() to get a cached singleton instance.
    """

    model_config = SettingsConfigDict(
        env_prefix="INGEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    env: Literal["development", "staging", "production"] = Field(default="development")
    database_backend: Literal["mongodb", "sqlite"] = Field(default="mongodb")
    vector_database_backend: Literal["qdrant", "local"] = Field(default="qdrant")

    # Nested settings groups
    paths: PathSettings = Field(default_factory=PathSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    sqlite: SQLiteSettings = Field(default_factory=SQLiteSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    local_vlm: LocalVLMSettings = Field(default_factory=LocalVLMSettings)
    whisper: WhisperSettings = Field(default_factory=WhisperSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings singleton.

    Returns:
        Settings: Application configuration instance.
    """
    return Settings()