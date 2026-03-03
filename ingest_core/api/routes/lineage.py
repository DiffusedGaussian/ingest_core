"""
Lineage tracking service.

Handles relationships between assets:
- Source → Generated relationships
- Multi-input generation tracking
- Graph traversal (ancestors, descendants)
- Generation job metadata

This is the core differentiator of ingest-core.
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
    """
    Service for tracking asset relationships and generation history.

    Core operations:
    - record_generation(): Link inputs → output with metadata
    - get_sources(): What assets produced this?
    - get_outputs(): What was generated from this?
    - get_full_lineage(): Complete ancestry/descendant tree
    - get_generation_history(): All generations with params
    """

    def __init__(self, container: "Container"):
        self.container = container

    # =========================================================================
    # Core Operations
    # =========================================================================

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

        This is the primary method for tracking generations.

        Args:
            source_ids: Input asset IDs (reference images, etc.)
            output_id: Generated asset ID (the video/image/3D output)
            generator: Name of the generator (e.g., "flux-pro", "runway-gen3", "meshy")
            generator_config: Generation parameters (prompt, seed, model version, etc.)
            description: Human-readable description of the generation
            created_by: User or system that triggered the generation

        Returns:
            List of created LineageRecords (one per source)

        Example:
            >>> await lineage_service.record_generation(
            ...     source_ids=[image1_id, image2_id],
            ...     output_id=video_id,
            ...     generator="runway-gen3",
            ...     generator_config={
            ...         "prompt": "Camera slowly pushes in...",
            ...         "duration": 5,
            ...         "seed": 12345,
            ...     },
            ...     description="Product video from reference images"
            ... )
        """
        records = []
        generation_id = str(uuid4())  # Group all sources under one generation

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

            # Store in database
            await self._save_record(record)
            records.append(record)

            logger.info(
                "Recorded lineage",
                source=str(source_id),
                target=str(output_id),
                generator=generator,
                generation_id=generation_id,
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
        """
        Record a transformation: one input → one output.

        Use for: crop, resize, upscale, style transfer, etc.

        Args:
            source_id: Original asset ID
            output_id: Transformed asset ID
            transformation: Type of transformation (e.g., "upscale", "crop", "remove_bg")
            params: Transformation parameters
            created_by: User or system

        Returns:
            Created LineageRecord
        """
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

        logger.info(
            "Recorded transformation",
            source=str(source_id),
            target=str(output_id),
            transformation=transformation,
        )

        return record

    async def record_extraction(
        self,
        source_id: UUID,
        output_id: UUID,
        extraction_type: str,
        frame_index: int | None = None,
        timestamp: float | None = None,
        created_by: str | None = None,
    ) -> LineageRecord:
        """
        Record an extraction: frame from video, etc.

        Args:
            source_id: Source asset (e.g., video)
            output_id: Extracted asset (e.g., frame image)
            extraction_type: Type (e.g., "keyframe", "frame", "audio")
            frame_index: Frame number if applicable
            timestamp: Timestamp in seconds if applicable
            created_by: User or system

        Returns:
            Created LineageRecord
        """
        record = LineageRecord(
            source_asset_id=source_id,
            target_asset_id=output_id,
            relationship_type=LineageType.EXTRACTED_FROM,
            description=f"Extracted {extraction_type}",
            metadata={
                "extraction_type": extraction_type,
                "frame_index": frame_index,
                "timestamp_seconds": timestamp,
                "extracted_at": datetime.utcnow().isoformat(),
            },
            created_by=created_by,
        )

        await self._save_record(record)

        return record

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_sources(
        self,
        asset_id: UUID,
        relationship_types: list[LineageType] | None = None,
    ) -> list[Asset]:
        """
        Get all source assets that contributed to this asset.

        "What inputs produced this?"

        Args:
            asset_id: The asset to query
            relationship_types: Filter by relationship type (default: all)

        Returns:
            List of source Assets
        """
        records = await self._get_records_by_target(asset_id)

        if relationship_types:
            records = [r for r in records if r.relationship_type in relationship_types]

        # Fetch actual assets
        sources = []
        for record in records:
            asset = await self.container.asset_service.get(record.source_asset_id)
            if asset:
                sources.append(asset)

        return sources

    async def get_outputs(
        self,
        asset_id: UUID,
        relationship_types: list[LineageType] | None = None,
    ) -> list[Asset]:
        """
        Get all assets generated from this asset.

        "What was created from this?"

        Args:
            asset_id: The asset to query
            relationship_types: Filter by relationship type (default: all)

        Returns:
            List of output Assets
        """
        records = await self._get_records_by_source(asset_id)

        if relationship_types:
            records = [r for r in records if r.relationship_type in relationship_types]

        # Fetch actual assets
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
        """
        Get raw lineage records for an asset.

        Args:
            asset_id: Asset to query
            direction: "sources", "outputs", or "both"

        Returns:
            List of LineageRecords
        """
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            query = {}
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
        else:
            return await db.get_lineage(asset_id, direction)

    async def get_full_lineage(
        self,
        asset_id: UUID,
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """
        Get complete lineage tree for an asset.

        Traverses the graph to find all ancestors and descendants.

        Args:
            asset_id: Starting asset
            max_depth: Maximum traversal depth (prevent infinite loops)

        Returns:
            Dict with 'ancestors' and 'descendants' trees
        """
        ancestors = await self._traverse_ancestors(asset_id, max_depth)
        descendants = await self._traverse_descendants(asset_id, max_depth)

        return {
            "asset_id": str(asset_id),
            "ancestors": ancestors,
            "descendants": descendants,
        }

    async def get_generation_history(
        self,
        asset_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Get all generation events that produced this asset.

        Returns grouped generation metadata.

        Args:
            asset_id: The generated asset

        Returns:
            List of generation events with sources and config
        """
        records = await self._get_records_by_target(asset_id)

        # Group by generation_id
        generations: dict[str, dict[str, Any]] = {}

        for record in records:
            gen_id = record.metadata.get("generation_id", str(record.id))

            if gen_id not in generations:
                generations[gen_id] = {
                    "generation_id": gen_id,
                    "generator": record.metadata.get("generator"),
                    "generator_config": record.metadata.get("generator_config", {}),
                    "generated_at": record.metadata.get("generated_at"),
                    "description": record.description,
                    "source_ids": [],
                }

            generations[gen_id]["source_ids"].append(str(record.source_asset_id))

        return list(generations.values())

    async def find_by_generator(
        self,
        generator: str,
        limit: int = 100,
    ) -> list[LineageRecord]:
        """
        Find all lineage records from a specific generator.

        Useful for: "Show me everything generated by Flux"

        Args:
            generator: Generator name to search for
            limit: Maximum records to return

        Returns:
            List of matching LineageRecords
        """
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            cursor = db.lineage.find(
                {"metadata.generator": generator}
            ).limit(limit)
            return [LineageRecord.model_validate(doc) async for doc in cursor]
        else:
            # SQLite: query JSON field
            # For now, fetch all and filter (not optimal, but works)
            # TODO: Add JSON query support to SQLite client
            all_records = await db.get_all_lineage(limit=limit * 10)
            return [
                r for r in all_records
                if r.metadata.get("generator") == generator
            ][:limit]

    # =========================================================================
    # Private Helpers
    # =========================================================================

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
        else:
            return await db.get_lineage(source_id, "outputs")

    async def _get_records_by_target(self, target_id: UUID) -> list[LineageRecord]:
        """Get all records where this asset is the target."""
        db = self.container.db

        if self.container.settings.database_backend == "mongodb":
            cursor = db.lineage.find({"target_asset_id": str(target_id)})
            return [LineageRecord.model_validate(doc) async for doc in cursor]
        else:
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
            return []  # Prevent cycles

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
            return []  # Prevent cycles

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