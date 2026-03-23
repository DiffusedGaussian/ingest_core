"""
Ingestion orchestration service.
"""

from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO
from uuid import uuid4

from structlog import get_logger

from ingest_core.models.asset import Asset, AssetStatus, AssetType

if TYPE_CHECKING:
    from ingest_core.container.container import Container

logger = get_logger()


class IngestionService:
    """
    Orchestrates the ingestion pipeline:
    Upload -> Store -> Process -> Analyze -> Index
    """

    def __init__(self, container: "Container"):
        self.container = container

    def _detect_asset_type(self, mime_type: str) -> AssetType:
        """Determine asset type from MIME type."""
        if mime_type.startswith("image/"):
            return AssetType.IMAGE
        elif mime_type.startswith("video/"):
            return AssetType.VIDEO
        elif mime_type.startswith("model/") or mime_type in ["application/octet-stream"]:
            # Basic fallback, might need better 3D detection
            return AssetType.ASSET_3D
        else:
            # Default to image if unsure, or raise error?
            # For now, let's assume image if unknown
            return AssetType.IMAGE

    async def ingest_file(self, file_obj: BinaryIO, filename: str, content_type: str) -> Asset:
        """
        Ingest a file into the system.

        Args:
            file_obj: File-like object
            filename: Original filename
            content_type: MIME type

        Returns:
            Created Asset
        """
        # 1. Generate ID and paths
        asset_id = uuid4()
        extension = Path(filename).suffix.lower()
        storage_path = f"assets/{asset_id}{extension}"

        # 2. Save to storage
        logger.info("Saving file to storage", path=storage_path)
        # Check if file_obj is async or sync, StorageBackend handles it
        saved_path = await self.container.storage.save(file_obj, storage_path, content_type)

        # 3. Create initial asset record
        asset_type = self._detect_asset_type(content_type)

        # Get file size if possible
        file_size = 0
        if hasattr(file_obj, "seek") and hasattr(file_obj, "tell"):
            file_obj.seek(0, 2)
            file_size = file_obj.tell()
            file_obj.seek(0)

        asset = Asset(
            id=asset_id,
            asset_type=asset_type,
            status=AssetStatus.PENDING,
            original_filename=filename,
            file_extension=extension,
            file_size_bytes=file_size,
            mime_type=content_type,
            storage_path=saved_path,
        )

        await self.container.asset_service.create(asset)

        # 4. Trigger processing (could be background task)
        # For now, run inline
        await self.process_asset(asset)

        return asset

    async def process_asset(self, asset: Asset) -> None:
        """
        Run processing pipeline for an asset.
        """
        try:
            await self.container.asset_service.update_status(asset.id, AssetStatus.PROCESSING)

            # TODO: Get appropriate processor based on asset type
            # For now, hardcode ImageProcessor if image
            if asset.asset_type == AssetType.IMAGE:
                # We need a local file path for processing (libraries like PIL/OpenCV need it)
                # If using GCS, we might need to download to temp.
                # If using LocalStorage, we can get the path.

                # Check if storage supports direct path access (LocalStorage)
                # Or if we need to stream to temp

                # For this implementation, assume we can get a stream and save to temp
                # or if using LocalStorage, get absolute path.

                # Let's use a temp file approach to be safe for all storage backends
                temp_path = self.container.settings.paths.temp_dir / f"{asset.id}{asset.file_extension}"

                # Download to temp
                async for chunk in self.container.storage.get(asset.storage_path):
                     with open(temp_path, "ab") as f:
                         f.write(chunk)

                try:
                    # Let's import directly for now or fix container.
                    from ingest_core.processors.image import ImageProcessor
                    processor = ImageProcessor()

                    # Validate
                    is_valid, error = await processor.validate(temp_path)
                    if not is_valid:
                        raise ValueError(f"Validation failed: {error}")

                    # Extract Metadata
                    metadata = await processor.extract_metadata(temp_path)
                    asset.extra_metadata.update(metadata)

                    # Generate Thumbnail
                    thumb_path = self.container.settings.paths.processed_dir / f"{asset.id}_thumb.jpg"
                    if await processor.generate_thumbnail(temp_path, thumb_path):
                        # Upload thumbnail to storage?
                        # For now, keep local or upload.
                        # Ideally, thumbnails live in storage too.
                        pass

                    # Save updates
                    # We need to update the asset object locally and in DB
                    # Since update_status only updates status, we need a general update method in AssetService
                    # Or just use update_status for success.
                    # But we want to save metadata.

                    # Quick fix: direct DB update for metadata
                    await self.container.mongodb.assets.update_one(
                        {"_id": str(asset.id)},
                        {"$set": {"extra_metadata": asset.extra_metadata}}
                    )

                finally:
                    # Cleanup temp
                    if temp_path.exists():
                        temp_path.unlink()

            await self.container.asset_service.update_status(asset.id, AssetStatus.COMPLETED)

        except Exception as e:
            logger.error("Processing failed", id=str(asset.id), error=str(e))
            await self.container.asset_service.update_status(asset.id, AssetStatus.FAILED, str(e))
