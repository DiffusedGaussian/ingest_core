"""
Lineage tracking service.

Handles relationships between assets:
- Source → Generated relationships
- Multi-input generation tracking
- Graph traversal (ancestors, descendants)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from structlog import get_logger

from ingest_core.models.asset import Asset
from ingest_core.models.lineage import LineageRecord, LineageType

if TYPE_CHECKING:
    from ingest_core.container.container import Container

logger = get_logger()


class LineageService:
    """Service for tracking asset relationships and generation history."""

    def __init__(self, container: "Container"):
        self.container = container

    async def record_generation(
        self,
        source_ids: list[UUID],
        output_id: UUID,
        generator: str,
        generator_config: dict[str, Any] | None = None,
        description: str | None = None,
        created_by: str | None = None,
    ) -> list[LineageRecord]:
        """
        Record a generation event: multiple inputs → one output.

        Args:
            source_ids: Input asset IDs (reference images, etc.)
            output_id: Generated asset ID
            generator: Generator name (e.g., "flux-pro", "runway-gen3")
            generator_config: Generation parameters
            description: Human-readable description
            created_by: User or system that triggered generation

        Returns:
            List of created LineageRecords
        """
        records = []
        generation_id = str(uuid4())

        metadata = {
            "generation_id": generation_id,
            "generator": generator,
            "generator_config": generator_config or {},
            "generated_at": datetime.utcnow().isoformat(),
        }

        for source_id in source_ids:
            record = LineageRecord(
                source_asset_id=source_id,
                target_asset_id=output_id,
                relationship_type=LineageType.SOURCE_OF,
                description=description,
                metadata=metadata,
                created_by=created_by,
            )

            await self._save_record(record)
            records.append(record)

            logger.info(
                "Recorded lineage",
                source=str(source_id),
                target=str(output_id),
                generator=generator,
            )

        return records

    async def record_transformation(
        self,
        source_id: UUID,
        output_id: UUID,
        transformation: str,
        params: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> LineageRecord:
        """Record a transformation: one input → one output."""
        record = LineageRecord(
            source_asset_id=source_id,
            target_asset_id=output_id,
            relationship_type=LineageType.TRANSFORMED_FROM,
            description=f"Transformed via {transformation}",
            metadata={
                "transformation": transformation,
                "params": params or {},
                "transformed_at": datetime.utcnow().isoformat(),
            },
            created_by=created_by,
        )

        await self._save_record(record)
        return record

    async def get_sources(self, asset_id: UUID) -> list[Asset]:
        """Get all source assets that contributed to this asset."""
        records = await self._get_records_by_target(asset_id)

        sources = []
        for record in records:
            asset = await self.container.asset_service.get(record.source_asset_id)
            if asset:
                sources.append(asset)

        return sources

    async def get_outputs(self, asset_id: UUID) -> list[Asset]:
        """Get all assets generated from this asset."""
        records = await self._get_records_by_source(asset_id)

        outputs = []
        for record in records:
            asset = await self.container.asset_service.get(record.target_asset_id)
            if asset:
                outputs.append(asset)

        return outputs

    async def get_lineage_records(
        self,
        asset_id: UUID,
        direction: str = "both",
    ) -> list[LineageRecord]:
        """Get raw lineage records for an asset."""
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            query: dict[str, Any] = {}
            if direction == "sources":
                query["target_asset_id"] = str(asset_id)
            elif direction == "outputs":
                query["source_asset_id"] = str(asset_id)
            else:
                query["$or"] = [
                    {"source_asset_id": str(asset_id)},
                    {"target_asset_id": str(asset_id)},
                ]

            cursor = db.lineage.find(query)
            return [LineageRecord.model_validate(doc) async for doc in cursor]

        return await db.get_lineage(asset_id, direction)

    async def get_full_lineage(
        self,
        asset_id: UUID,
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """Get complete lineage tree for an asset."""
        ancestors = await self._traverse_ancestors(asset_id, max_depth)
        descendants = await self._traverse_descendants(asset_id, max_depth)

        return {
            "asset_id": str(asset_id),
            "ancestors": ancestors,
            "descendants": descendants,
        }

    async def _save_record(self, record: LineageRecord) -> None:
        """Save a lineage record to the database."""
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            await db.lineage.insert_one(record.model_dump(mode="json"))
        else:
            await db.create_lineage(record)

    async def _get_records_by_source(self, source_id: UUID) -> list[LineageRecord]:
        """Get all records where this asset is the source."""
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            cursor = db.lineage.find({"source_asset_id": str(source_id)})
            return [LineageRecord.model_validate(doc) async for doc in cursor]

        return await db.get_lineage(source_id, "outputs")

    async def _get_records_by_target(self, target_id: UUID) -> list[LineageRecord]:
        """Get all records where this asset is the target."""
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            cursor = db.lineage.find({"target_asset_id": str(target_id)})
            return [LineageRecord.model_validate(doc) async for doc in cursor]

        return await db.get_lineage(target_id, "sources")

    async def _traverse_ancestors(
        self,
        asset_id: UUID,
        max_depth: int,
        visited: set[str] | None = None,
        current_depth: int = 0,
    ) -> list[dict[str, Any]]:
        """Recursively traverse ancestor tree."""
        if visited is None:
            visited = set()

        if current_depth >= max_depth:
            return []

        asset_id_str = str(asset_id)
        if asset_id_str in visited:
            return []

        visited.add(asset_id_str)

        records = await self._get_records_by_target(asset_id)
        ancestors = []

        for record in records:
            source_asset = await self.container.asset_service.get(record.source_asset_id)

            ancestor_entry = {
                "asset_id": str(record.source_asset_id),
                "asset": source_asset.model_dump(mode="json") if source_asset else None,
                "relationship": record.relationship_type.value,
                "metadata": record.metadata,
                "ancestors": await self._traverse_ancestors(
                    record.source_asset_id,
                    max_depth,
                    visited,
                    current_depth + 1,
                ),
            }
            ancestors.append(ancestor_entry)

        return ancestors

    async def _traverse_descendants(
        self,
        asset_id: UUID,
        max_depth: int,
        visited: set[str] | None = None,
        current_depth: int = 0,
    ) -> list[dict[str, Any]]:
        """Recursively traverse descendant tree."""
        if visited is None:
            visited = set()

        if current_depth >= max_depth:
            return []

        asset_id_str = str(asset_id)
        if asset_id_str in visited:
            return []

        visited.add(asset_id_str)

        records = await self._get_records_by_source(asset_id)
        descendants = []

        for record in records:
            target_asset = await self.container.asset_service.get(record.target_asset_id)

            descendant_entry = {
                "asset_id": str(record.target_asset_id),
                "asset": target_asset.model_dump(mode="json") if target_asset else None,
                "relationship": record.relationship_type.value,
                "metadata": record.metadata,
                "descendants": await self._traverse_descendants(
                    record.target_asset_id,
                    max_depth,
                    visited,
                    current_depth + 1,
                ),
            }
            descendants.append(descendant_entry)

        return descendants
