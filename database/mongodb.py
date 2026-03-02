"""
MongoDB client wrapper.
"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from structlog import get_logger

from config import MongoDBSettings

logger = get_logger()


class MongoDBClient:
    """
    MongoDB client wrapper for asynchronous document storage.
    """

    def __init__(self, settings: MongoDBSettings):
        """
        Initialize MongoDB client.

        Args:
            settings: MongoDB configuration
        """
        self.settings = settings
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """
        Connect to MongoDB.
        """
        if self._client:
            return

        try:
            logger.info("Connecting to MongoDB", uri=self.settings.mongodb_uri)
            self._client = AsyncIOMotorClient(self.settings.mongodb_uri)
            self._db = self._client[self.settings.mongodb_database]

            # Verify connection
            await self._client.admin.command("ping")
            logger.info("Connected to MongoDB", database=self.settings.mongodb_database)

        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise

    async def disconnect(self) -> None:
        """
        Close MongoDB connection.
        """
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Disconnected from MongoDB")

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance.

        Returns:
            AsyncIOMotorDatabase: The database instance

        Raises:
            RuntimeError: If client is not connected
        """
        if self._db is None:
            raise RuntimeError("MongoDB client not connected")
        return self._db

    @property
    def assets(self):
        """Get assets collection."""
        return self.db.assets

    @property
    def lineage(self):
        """Get lineage collection."""
        return self.db.lineage
