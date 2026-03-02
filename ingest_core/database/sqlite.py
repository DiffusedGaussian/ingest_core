"""
SQLite client wrapper.
"""

import json
from typing import Any, Dict, List, Optional

import aiosqlite
from structlog import get_logger

from ingest_core.config import SQLiteSettings

logger = get_logger()


class SQLiteClient:
    """
    SQLite client wrapper for lightweight local storage.
    Acts as a minimal document store to mimic MongoDB API where needed.
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
        Initialize SQLite connection and tables.
        """
        if self._conn:
            return

        try:
            # Ensure directory exists
            self.settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info("Connecting to SQLite", path=str(self.settings.sqlite_path))
            self._conn = await aiosqlite.connect(self.settings.sqlite_path)
            self._conn.row_factory = aiosqlite.Row

            # Enable WAL mode for better concurrency
            await self._conn.execute("PRAGMA journal_mode=WAL;")

            # Create a generic assets table
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    data TEXT
                )
            """)
            await self._conn.commit()

        except Exception as e:
            logger.error("Failed to connect to SQLite", error=str(e))
            raise

    async def close(self) -> None:
        """Close SQLite connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Disconnected from SQLite")

    # Minimal MongoDB-like API for Assets

    async def insert_one(self, document: Dict[str, Any]) -> None:
        """Mimic MongoDB insert_one."""
        doc_id = document.get("_id") or document.get("id")
        await self._conn.execute(
            "INSERT INTO assets (id, data) VALUES (?, ?)",
            (str(doc_id), json.dumps(document))
        )
        await self._conn.commit()

    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mimic MongoDB find_one."""
        if "_id" in filter:
            async with self._conn.execute(
                "SELECT data FROM assets WHERE id = ?", (str(filter["_id"]),)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Mimic MongoDB update_one (supports $set only)."""
        if "_id" in filter and "$set" in update:
            doc = await self.find_one(filter)
            if doc:
                doc.update(update["$set"])
                await self._conn.execute(
                    "UPDATE assets SET data = ? WHERE id = ?",
                    (json.dumps(doc), str(filter["_id"]))
                )
                await self._conn.commit()

    async def delete_one(self, filter: Dict[str, Any]) -> None:
        """Mimic MongoDB delete_one."""
        if "_id" in filter:
            await self._conn.execute(
                "DELETE FROM assets WHERE id = ?", (str(filter["_id"]),)
            )
            await self._conn.commit()

    @property
    def assets(self):
        """Allow .assets access to itself to mimic collection access."""
        return self
