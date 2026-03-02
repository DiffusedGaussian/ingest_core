"""
SQLite client wrapper.
"""

import aiosqlite
from structlog import get_logger

from ingest_core.config import SQLiteSettings

logger = get_logger()


class SQLiteClient:
    """
    SQLite client wrapper for lightweight local storage.
    """

    def __init__(self, settings: SQLiteSettings):
        """
        Initialize SQLite client.

        Args:
            settings: SQLite configuration
        """
        self.settings = settings
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """
        Initialize SQLite connection.
        """
        if self._conn:
            return

        try:
            # Ensure directory exists
            self.settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info("Connecting to SQLite", path=str(self.settings.sqlite_path))
            self._conn = await aiosqlite.connect(self.settings.sqlite_path)

            # Enable WAL mode for better concurrency
            await self._conn.execute("PRAGMA journal_mode=WAL;")

        except Exception as e:
            logger.error("Failed to connect to SQLite", error=str(e))
            raise

    async def close(self) -> None:
        """Close SQLite connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Disconnected from SQLite")

    async def execute(self, sql: str, parameters: tuple = ()) -> aiosqlite.Cursor:
        """Execute a query."""
        if not self._conn:
            raise RuntimeError("SQLite client not connected")
        return await self._conn.execute(sql, parameters)

    async def commit(self) -> None:
        """Commit transaction."""
        if not self._conn:
            raise RuntimeError("SQLite client not connected")
        await self._conn.commit()
