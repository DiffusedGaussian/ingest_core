"""
SQLite client wrapper.

Provides a MongoDB-compatible API for local development and lightweight deployments.
Uses JSON storage for flexible document structure while maintaining SQL queryability.
"""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import aiosqlite
from structlog import get_logger

from ingest_core.config import SQLiteSettings
from ingest_core.models.asset import Asset
from ingest_core.models.lineage import LineageRecord

logger = get_logger()


class SQLiteClient:
    """
    SQLite client wrapper for lightweight local storage.

    Acts as a document store with MongoDB-like API for compatibility.
    Stores documents as JSON with indexed fields for efficient queries.

    Tables:
    - assets: Media asset metadata
    - lineage: Relationship records between assets
    - embeddings: Vector references (actual vectors in FAISS)
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
        Initialize SQLite connection and create tables.
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

            # Create tables
            await self._conn.executescript("""
                -- Assets table with indexed fields for common queries
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    asset_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    original_filename TEXT,
                    mime_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data TEXT NOT NULL  -- Full JSON document
                );

                CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
                CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
                CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at);

                -- Full-text search on filenames and metadata
                CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
                    id,
                    original_filename,
                    tags,
                    description,
                    content='assets',
                    content_rowid='rowid'
                );

                -- Lineage records
                CREATE TABLE IF NOT EXISTS lineage (
                    id TEXT PRIMARY KEY,
                    source_asset_id TEXT NOT NULL,
                    target_asset_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL,  -- Full JSON document
                    FOREIGN KEY (source_asset_id) REFERENCES assets(id),
                    FOREIGN KEY (target_asset_id) REFERENCES assets(id)
                );

                CREATE INDEX IF NOT EXISTS idx_lineage_source ON lineage(source_asset_id);
                CREATE INDEX IF NOT EXISTS idx_lineage_target ON lineage(target_asset_id);

                -- Trigger to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS assets_ai AFTER INSERT ON assets BEGIN
                    INSERT INTO assets_fts(id, original_filename, tags, description)
                    VALUES (
                        new.id,
                        new.original_filename,
                        json_extract(new.data, '$.extra_metadata.tags'),
                        json_extract(new.data, '$.extra_metadata.vlm.description')
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS assets_ad AFTER DELETE ON assets BEGIN
                    DELETE FROM assets_fts WHERE id = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS assets_au AFTER UPDATE ON assets BEGIN
                    DELETE FROM assets_fts WHERE id = old.id;
                    INSERT INTO assets_fts(id, original_filename, tags, description)
                    VALUES (
                        new.id,
                        new.original_filename,
                        json_extract(new.data, '$.extra_metadata.tags'),
                        json_extract(new.data, '$.extra_metadata.vlm.description')
                    );
                END;
            """)
            await self._conn.commit()

            logger.info("SQLite initialized", tables=["assets", "lineage", "assets_fts"])

        except Exception as e:
            logger.error("Failed to initialize SQLite", error=str(e))
            raise

    async def close(self) -> None:
        """Close SQLite connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Disconnected from SQLite")

    # =========================================================================
    # MongoDB-compatible Collection API
    # =========================================================================

    @property
    def assets(self) -> "AssetsCollection":
        """Get assets collection (MongoDB-compatible API)."""
        return AssetsCollection(self._conn)

    @property
    def lineage(self) -> "LineageCollection":
        """Get lineage collection (MongoDB-compatible API)."""
        return LineageCollection(self._conn)

    # =========================================================================
    # Asset Operations (Direct API)
    # =========================================================================

    async def list_assets(
        self,
        query: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Asset], int]:
        """
        List assets with filtering and pagination.

        Args:
            query: Filter conditions
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (assets, total_count)
        """
        query = query or {}

        # Build WHERE clause
        conditions = []
        params = []

        if "asset_type" in query:
            conditions.append("asset_type = ?")
            params.append(query["asset_type"])
        if "asset_types" in query:
            placeholders = ",".join("?" * len(query["asset_types"]))
            conditions.append(f"asset_type IN ({placeholders})")
            params.extend([t.value if hasattr(t, 'value') else t for t in query["asset_types"]])
        if "status" in query:
            conditions.append("status = ?")
            params.append(query["status"].value if hasattr(query["status"], 'value') else query["status"])
        if "created_after" in query:
            conditions.append("created_at >= ?")
            params.append(query["created_after"].isoformat() if hasattr(query["created_after"], 'isoformat') else query["created_after"])
        if "created_before" in query:
            conditions.append("created_at <= ?")
            params.append(query["created_before"].isoformat() if hasattr(query["created_before"], 'isoformat') else query["created_before"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        async with self._conn.execute(
            f"SELECT COUNT(*) FROM assets WHERE {where_clause}",
            params
        ) as cursor:
            row = await cursor.fetchone()
            total = row[0]

        # Get paginated results
        async with self._conn.execute(
            f"SELECT data FROM assets WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, skip]
        ) as cursor:
            rows = await cursor.fetchall()
            assets = [Asset.model_validate(json.loads(row[0])) for row in rows]

        return assets, total

    async def update_asset_metadata(
        self,
        asset_id: UUID | str,
        metadata: dict[str, Any],
    ) -> None:
        """
        Update asset's extra_metadata field.

        Args:
            asset_id: Asset ID
            metadata: New metadata to merge
        """
        # Get current document
        async with self._conn.execute(
            "SELECT data FROM assets WHERE id = ?",
            (str(asset_id),)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return

            doc = json.loads(row[0])

        # Update metadata
        doc["extra_metadata"] = metadata
        doc["updated_at"] = datetime.utcnow().isoformat()

        # Save back
        await self._conn.execute(
            "UPDATE assets SET data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(doc), doc["updated_at"], str(asset_id))
        )
        await self._conn.commit()

    async def text_search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Asset], int]:
        """
        Full-text search on assets.

        Args:
            query: Search query
            filters: Additional filters
            skip: Number to skip
            limit: Maximum to return

        Returns:
            Tuple of (assets, total_count)
        """
        filters = filters or {}

        # Build query with FTS and optional filters
        # Join FTS results with assets table for filtering
        sql = """
            SELECT a.data, bm25(assets_fts) as score
            FROM assets_fts f
            JOIN assets a ON f.id = a.id
            WHERE assets_fts MATCH ?
        """
        params = [query]

        if filters.get("asset_types"):
            placeholders = ",".join("?" * len(filters["asset_types"]))
            sql += f" AND a.asset_type IN ({placeholders})"
            params.extend([t.value if hasattr(t, 'value') else t for t in filters["asset_types"]])

        if filters.get("status"):
            sql += " AND a.status = ?"
            params.append(filters["status"].value if hasattr(filters["status"], 'value') else filters["status"])

        # Count total
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        async with self._conn.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            total = row[0]

        # Get results
        sql += " ORDER BY score LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            assets = [Asset.model_validate(json.loads(row[0])) for row in rows]

        return assets, total

    # =========================================================================
    # Lineage Operations
    # =========================================================================

    async def create_lineage(self, record: LineageRecord) -> None:
        """
        Create a lineage record.

        Args:
            record: Lineage record to create
        """
        await self._conn.execute(
            """INSERT INTO lineage (id, source_asset_id, target_asset_id, relationship_type, created_at, data)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(record.id),
                str(record.source_asset_id),
                str(record.target_asset_id),
                record.relationship_type.value,
                record.created_at.isoformat(),
                json.dumps(record.model_dump(mode="json")),
            )
        )
        await self._conn.commit()

    async def get_lineage(
        self,
        asset_id: UUID | str,
        direction: str = "both",
    ) -> list[LineageRecord]:
        """
        Get lineage records for an asset.

        Args:
            asset_id: Asset ID
            direction: "sources", "outputs", or "both"

        Returns:
            List of lineage records
        """
        asset_id_str = str(asset_id)

        if direction == "sources":
            sql = "SELECT data FROM lineage WHERE target_asset_id = ?"
            params = [asset_id_str]
        elif direction == "outputs":
            sql = "SELECT data FROM lineage WHERE source_asset_id = ?"
            params = [asset_id_str]
        else:
            sql = "SELECT data FROM lineage WHERE source_asset_id = ? OR target_asset_id = ?"
            params = [asset_id_str, asset_id_str]

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [LineageRecord.model_validate(json.loads(row[0])) for row in rows]


class AssetsCollection:
    """
    MongoDB-compatible collection interface for assets.

    Allows code to work with both MongoDB and SQLite backends
    using the same API.
    """

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def insert_one(self, document: dict[str, Any]) -> None:
        """Insert a single document."""
        doc_id = document.get("_id") or document.get("id")

        # Extract indexed fields
        asset_type = document.get("asset_type", "")
        status = document.get("status", "")
        original_filename = document.get("original_filename", "")
        mime_type = document.get("mime_type", "")
        created_at = document.get("created_at", datetime.utcnow().isoformat())
        updated_at = document.get("updated_at", datetime.utcnow().isoformat())

        await self._conn.execute(
            """INSERT INTO assets 
               (id, asset_type, status, original_filename, mime_type, created_at, updated_at, data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(doc_id),
                asset_type.value if hasattr(asset_type, 'value') else asset_type,
                status.value if hasattr(status, 'value') else status,
                original_filename,
                mime_type,
                created_at if isinstance(created_at, str) else created_at.isoformat(),
                updated_at if isinstance(updated_at, str) else updated_at.isoformat(),
                json.dumps(document, default=str),
            )
        )
        await self._conn.commit()

    async def find_one(self, filter_dict: dict[str, Any]) -> dict[str, Any] | None:
        """Find a single document."""
        if "_id" in filter_dict:
            async with self._conn.execute(
                "SELECT data FROM assets WHERE id = ?",
                (str(filter_dict["_id"]),)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None

    def find(self, filter_dict: dict[str, Any] | None = None) -> "AsyncCursor":
        """Find documents matching filter."""
        return AsyncCursor(self._conn, "assets", filter_dict or {})

    async def update_one(
        self,
        filter_dict: dict[str, Any],
        update: dict[str, Any],
    ) -> None:
        """Update a single document."""
        if "_id" not in filter_dict:
            return

        doc_id = str(filter_dict["_id"])

        if "$set" in update:
            # Get current document
            async with self._conn.execute(
                "SELECT data FROM assets WHERE id = ?",
                (doc_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return
                doc = json.loads(row[0])

            # Apply updates
            doc.update(update["$set"])

            # Update indexed fields if changed
            asset_type = doc.get("asset_type", "")
            status = doc.get("status", "")
            updated_at = doc.get("updated_at", datetime.utcnow().isoformat())

            await self._conn.execute(
                """UPDATE assets 
                   SET asset_type = ?, status = ?, updated_at = ?, data = ?
                   WHERE id = ?""",
                (
                    asset_type.value if hasattr(asset_type, 'value') else asset_type,
                    status.value if hasattr(status, 'value') else status,
                    updated_at if isinstance(updated_at, str) else updated_at.isoformat(),
                    json.dumps(doc, default=str),
                    doc_id,
                )
            )
            await self._conn.commit()

    async def delete_one(self, filter_dict: dict[str, Any]) -> None:
        """Delete a single document."""
        if "_id" in filter_dict:
            await self._conn.execute(
                "DELETE FROM assets WHERE id = ?",
                (str(filter_dict["_id"]),)
            )
            await self._conn.commit()

    async def count_documents(self, filter_dict: dict[str, Any] | None = None) -> int:
        """Count documents matching filter."""
        filter_dict = filter_dict or {}

        conditions = []
        params = []

        if "asset_type" in filter_dict:
            if isinstance(filter_dict["asset_type"], dict) and "$in" in filter_dict["asset_type"]:
                placeholders = ",".join("?" * len(filter_dict["asset_type"]["$in"]))
                conditions.append(f"asset_type IN ({placeholders})")
                params.extend(filter_dict["asset_type"]["$in"])
            else:
                conditions.append("asset_type = ?")
                params.append(filter_dict["asset_type"])

        if "status" in filter_dict:
            conditions.append("status = ?")
            params.append(filter_dict["status"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        async with self._conn.execute(
            f"SELECT COUNT(*) FROM assets WHERE {where_clause}",
            params
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


class LineageCollection:
    """MongoDB-compatible collection interface for lineage."""

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def insert_one(self, document: dict[str, Any]) -> None:
        """Insert a lineage record."""
        doc_id = document.get("id") or document.get("_id")

        await self._conn.execute(
            """INSERT INTO lineage 
               (id, source_asset_id, target_asset_id, relationship_type, created_at, data)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(doc_id),
                str(document["source_asset_id"]),
                str(document["target_asset_id"]),
                document["relationship_type"],
                document.get("created_at", datetime.utcnow().isoformat()),
                json.dumps(document, default=str),
            )
        )
        await self._conn.commit()

    def find(self, filter_dict: dict[str, Any] | None = None) -> "AsyncCursor":
        """Find lineage records."""
        return AsyncCursor(self._conn, "lineage", filter_dict or {})


class AsyncCursor:
    """
    Async cursor for MongoDB-compatible iteration.

    Supports:
    - Async iteration
    - skip() and limit() chaining
    """

    def __init__(
        self,
        conn: aiosqlite.Connection,
        table: str,
        filter_dict: dict[str, Any],
    ):
        self._conn = conn
        self._table = table
        self._filter = filter_dict
        self._skip = 0
        self._limit: int | None = None

    def skip(self, n: int) -> "AsyncCursor":
        """Skip n documents."""
        self._skip = n
        return self

    def limit(self, n: int) -> "AsyncCursor":
        """Limit to n documents."""
        self._limit = n
        return self

    def __aiter__(self):
        return self

    async def __anext__(self) -> dict[str, Any]:
        # This is a simplified implementation
        # In production, you'd want proper cursor state management
        if not hasattr(self, '_results'):
            self._results = await self._execute()
            self._index = 0

        if self._index >= len(self._results):
            raise StopAsyncIteration

        result = self._results[self._index]
        self._index += 1
        return result

    async def _execute(self) -> list[dict[str, Any]]:
        """Execute the query and return results."""
        conditions = []
        params = []

        # Handle $or queries (for lineage)
        if "$or" in self._filter:
            or_conditions = []
            for condition in self._filter["$or"]:
                for key, value in condition.items():
                    if key == "source_asset_id":
                        or_conditions.append("source_asset_id = ?")
                    elif key == "target_asset_id":
                        or_conditions.append("target_asset_id = ?")
                    params.append(str(value))
            if or_conditions:
                conditions.append(f"({' OR '.join(or_conditions)})")

        # Handle direct field matches
        for key, value in self._filter.items():
            if key.startswith("$"):
                continue
            if key in ("source_asset_id", "target_asset_id"):
                conditions.append(f"{key} = ?")
                params.append(str(value))
            elif key == "asset_type":
                if isinstance(value, dict) and "$in" in value:
                    placeholders = ",".join("?" * len(value["$in"]))
                    conditions.append(f"asset_type IN ({placeholders})")
                    params.extend(value["$in"])
                else:
                    conditions.append("asset_type = ?")
                    params.append(value)
            elif key == "status":
                conditions.append("status = ?")
                params.append(value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"SELECT data FROM {self._table} WHERE {where_clause}"

        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._skip > 0:
            sql += f" OFFSET {self._skip}"

        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [json.loads(row[0]) for row in rows]