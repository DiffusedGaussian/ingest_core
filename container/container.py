"""
Dependency Injection Container.

A lightweight DI container that manages the lifecycle of:
- Storage backends (local/GCS)
- Database clients (MongoDB, Qdrant, SQLite)
- Analyzers (pluggable)
- Services

Design principles:
- Lazy initialization: Dependencies created on first access
- Singleton by default: One instance per dependency type
- Pluggable: Analyzers can be registered dynamically
"""

from functools import lru_cache
from typing import Any, TypeVar, Callable

from ingest_core.config import Settings, get_settings

T = TypeVar("T")


class Container:
    """
    Dependency injection container.

    Manages application dependencies with lazy initialization.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._instances: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._analyzers: dict[str, Any] = {}

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

    # -------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------

    @property
    def storage(self):
        """
        Get storage backend (local or GCS based on environment).

        Returns:
            StorageBackend: Abstract storage interface
        """
        if "storage" not in self._instances:
            from ingest_core.storage import get_storage_backend
            self._instances["storage"] = get_storage_backend(self._settings)
        return self._instances["storage"]

    # -------------------------------------------------------------------------
    # Databases
    # -------------------------------------------------------------------------

    @property
    def mongodb(self):
        """
        Get MongoDB client.

        Returns:
            MongoDBClient: MongoDB database client
        """
        if "mongodb" not in self._instances:
            from ingest_core.database.mongodb import MongoDBClient
            self._instances["mongodb"] = MongoDBClient(self._settings.mongodb)
        return self._instances["mongodb"]

    @property
    def qdrant(self):
        """
        Get Qdrant vector database client.

        Returns:
            QdrantClient: Qdrant client for embeddings
        """
        if "qdrant" not in self._instances:
            from ingest_core.database.qdrant import QdrantRepository
            self._instances["qdrant"] = QdrantRepository(self._settings.qdrant)
        return self._instances["qdrant"]

    @property
    def sqlite(self):
        """
        Get SQLite client for lightweight local storage.

        Returns:
            SQLiteClient: SQLite database client
        """
        if "sqlite" not in self._instances:
            from ingest_core.database.sqlite import SQLiteClient
            self._instances["sqlite"] = SQLiteClient(self._settings.sqlite)
        return self._instances["sqlite"]

    # -------------------------------------------------------------------------
    # Analyzers (Pluggable)
    # -------------------------------------------------------------------------

    def register_analyzer(self, name: str, analyzer: Any) -> None:
        """
        Register an analyzer plugin.

        Args:
            name: Unique name for the analyzer
            analyzer: Analyzer instance implementing BaseAnalyzer protocol
        """
        self._analyzers[name] = analyzer

    def get_analyzer(self, name: str) -> Any:
        """
        Get a registered analyzer by name.

        Args:
            name: Analyzer name

        Returns:
            Analyzer instance

        Raises:
            KeyError: If analyzer not registered
        """
        if name not in self._analyzers:
            raise KeyError(f"Analyzer '{name}' not registered")
        return self._analyzers[name]

    @property
    def analyzers(self) -> dict[str, Any]:
        """Get all registered analyzers."""
        return self._analyzers.copy()

    def load_default_analyzers(self) -> None:
        """Load the default set of analyzers."""
        from ingest_core.analyzers import (
            EXIFAnalyzer,
            PerceptualHashAnalyzer,
            ObjectDetectionAnalyzer,
            VLMAnalyzer,
        )

        self.register_analyzer("exif", EXIFAnalyzer())
        self.register_analyzer("phash", PerceptualHashAnalyzer())
        self.register_analyzer("objects", ObjectDetectionAnalyzer(self._settings))
        self.register_analyzer("vlm", VLMAnalyzer(self._settings))

    # -------------------------------------------------------------------------
    # Services
    # -------------------------------------------------------------------------

    @property
    def ingestion_service(self):
        """
        Get the main ingestion service.

        Returns:
            IngestionService: Orchestrates the ingestion pipeline
        """
        if "ingestion_service" not in self._instances:
            from ingest_core.services.ingestion import IngestionService
            self._instances["ingestion_service"] = IngestionService(self)
        return self._instances["ingestion_service"]

    @property
    def asset_service(self):
        """
        Get the asset management service.

        Returns:
            AssetService: CRUD operations for assets
        """
        if "asset_service" not in self._instances:
            from ingest_core.services.asset import AssetService
            self._instances["asset_service"] = AssetService(self)
        return self._instances["asset_service"]

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def startup(self) -> None:
        """
        Initialize all dependencies.

        Called on application startup.
        """
        # Load default analyzers
        self.load_default_analyzers()

        # Initialize database connections
        await self.mongodb.connect()
        await self.qdrant.initialize()
        await self.sqlite.initialize()

    async def shutdown(self) -> None:
        """
        Clean up all dependencies.

        Called on application shutdown.
        """
        if "mongodb" in self._instances:
            await self.mongodb.disconnect()
        if "qdrant" in self._instances:
            await self.qdrant.close()
        if "sqlite" in self._instances:
            await self.sqlite.close()


@lru_cache
def get_container() -> Container:
    """
    Get the singleton container instance.

    Returns:
        Container: Application dependency container
    """
    return Container()