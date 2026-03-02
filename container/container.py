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

from config import Settings, get_settings

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
            from storage.factory import get_storage_backend
            self._instances["storage"] = get_storage_backend(self._settings)
        return self._instances["storage"]

    # -------------------------------------------------------------------------
    # Databases
    # -------------------------------------------------------------------------

    @property
    def db(self):
        """
        Get the primary document database client based on configuration.
        """
        if "db" not in self._instances:
            if self._settings.database_backend == "mongodb":
                from database.mongodb import MongoDBClient
                self._instances["db"] = MongoDBClient(self._settings.mongodb)
            else:
                from database.sqlite import SQLiteClient
                self._instances["db"] = SQLiteClient(self._settings.sqlite)
        return self._instances["db"]

    @property
    def vector_db(self):
        """
        Get the vector database client based on configuration.
        """
        if "vector_db" not in self._instances:
            if self._settings.vector_database_backend == "qdrant":
                from database.qdrant import QdrantRepository
                self._instances["vector_db"] = QdrantRepository(self._settings.qdrant)
            else:
                from database.faiss_db import FaissRepository
                self._instances["vector_db"] = FaissRepository(
                    data_dir=self._settings.paths.data_dir / "faiss",
                    dimension=1536 # Default for many embedding models
                )
        return self._instances["vector_db"]

    @property
    def mongodb(self):
        """Deprecated: Use .db instead for backend-agnostic code."""
        return self.db

    @property
    def qdrant(self):
        """Deprecated: Use .vector_db instead for backend-agnostic code."""
        return self.vector_db

    @property
    def sqlite(self):
        """Deprecated: Use .db instead for backend-agnostic code."""
        return self.db

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
        from analyzers import (
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
            from services.ingestion import IngestionService
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
            from services.asset import AssetService
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
        if self._settings.database_backend == "mongodb":
            await self.db.connect()
        else:
            await self.db.initialize()

        await self.vector_db.initialize()

    async def shutdown(self) -> None:
        """
        Clean up all dependencies.

        Called on application shutdown.
        """
        if "db" in self._instances:
            if self._settings.database_backend == "mongodb":
                await self.db.disconnect()
            else:
                await self.db.close()

        if "vector_db" in self._instances:
            await self.vector_db.close()


@lru_cache
def get_container() -> Container:
    """
    Get the singleton container instance.

    Returns:
        Container: Application dependency container
    """
    return Container()