"""
Base Asset model - parent class for all media types.

Defines common fields and behavior shared across images, videos, and 3D assets.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Supported asset types."""
    IMAGE = "image"
    VIDEO = "video"
    ASSET_3D = "3d"


class AssetStatus(str, Enum):
    """Asset processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Asset(BaseModel):
    """
    Base asset model.

    All media assets inherit from this class.
    Contains common metadata and status tracking.
    """
    id: UUID = Field(default_factory=uuid4)
    asset_type: AssetType
    status: AssetStatus = Field(default=AssetStatus.PENDING)

    # File information
    original_filename: str
    file_extension: str
    file_size_bytes: int
    mime_type: str
    storage_path: str  # Path in storage backend (local or GCS)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None

    # Processing results
    error_message: str | None = None

    # Extensible metadata (for analyzer results)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

    # Embedding reference (stored in Qdrant)
    embedding_id: str | None = None

    class Config:
        from_attributes = True

    def mark_processing(self) -> None:
        """Mark asset as currently processing."""
        self.status = AssetStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark asset as successfully processed."""
        self.status = AssetStatus.COMPLETED
        self.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """Mark asset as failed with error message."""
        self.status = AssetStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.utcnow()
