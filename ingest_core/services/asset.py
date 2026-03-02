"""
Asset management service.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from structlog import get_logger

from ingest_core.models.asset import Asset, AssetStatus

if TYPE_CHECKING:
    from ingest_core.container.container import Container

logger = get_logger()


class AssetService:
    """
    Service for managing asset metadata and lifecycle.
    """

    def __init__(self, container: "Container"):
        """
        Initialize asset service.

        Args:
            container: Dependency container
        """
        self.container = container

    @property
    def collection(self):
        """Get MongoDB assets collection."""
        return self.container.mongodb.assets

    async def create(self, asset: Asset) -> Asset:
        """
        Create a new asset record.

        Args:
            asset: Asset model instance

        Returns:
            Created asset
        """
        asset_dict = asset.model_dump(mode="json")
        # Ensure ID is string for MongoDB _id
        asset_dict["_id"] = str(asset.id)

        await self.collection.insert_one(asset_dict)
        logger.info("Created asset", id=str(asset.id), type=asset.asset_type)
        return asset

    async def get(self, asset_id: UUID | str) -> Asset | None:
        """
        Get an asset by ID.

        Args:
            asset_id: Asset UUID

        Returns:
            Asset instance or None
        """
        doc = await self.collection.find_one({"_id": str(asset_id)})
        if not doc:
            return None

        return Asset.model_validate(doc)

    async def update_status(self, asset_id: UUID | str, status: AssetStatus, error: str | None = None) -> None:
        """
        Update asset status.

        Args:
            asset_id: Asset UUID
            status: New status
            error: Optional error message
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        if status == AssetStatus.COMPLETED:
            update_data["processed_at"] = datetime.utcnow().isoformat()
        if error:
            update_data["error_message"] = error

        await self.collection.update_one(
            {"_id": str(asset_id)},
            {"$set": update_data}
        )
        logger.info("Updated asset status", id=str(asset_id), status=status)

    async def delete(self, asset_id: UUID | str) -> bool:
        """
        Delete an asset and its resources.

        Args:
            asset_id: Asset UUID

        Returns:
            True if deleted
        """
        asset = await self.get(asset_id)
        if not asset:
            return False

        # Delete from ingest_core.storage
        if asset.storage_path:
            await self.container.storage.delete(asset.storage_path)

        # Delete from vector DB
        # TODO: Implement Qdrant delete when supported

        # Delete from MongoDB
        await self.collection.delete_one({"_id": str(asset_id)})
        logger.info("Deleted asset", id=str(asset_id))
        return True
