"""
Lineage tracking models - INTERFACE ONLY for v1.

Defines the data structures for tracking asset relationships:
- Source → Generated relationships
- Training data provenance
- Transformation chains

Implementation is deferred to a future version.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LineageType(str, Enum):
    """Types of lineage relationships."""

    # Asset was used as input to generate another asset
    SOURCE_OF = "source_of"

    # Asset was generated from other assets
    DERIVED_FROM = "derived_from"

    # Asset was used in training data
    TRAINED_ON = "trained_on"

    # Asset is a transformation of another (crop, resize, etc.)
    TRANSFORMED_FROM = "transformed_from"

    # Asset is a frame extracted from video
    EXTRACTED_FROM = "extracted_from"


class LineageRecord(BaseModel):
    """
    Record of a lineage relationship between assets.

    NOTE: This is an interface definition for future implementation.
    The lineage tracking system is not yet functional in v1.
    """

    id: UUID = Field(default_factory=uuid4)

    # Relationship
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: LineageType

    # Context
    description: str | None = None
    metadata: dict = Field(default_factory=dict)  # Additional context

    # E.g., for training: model name, epoch, etc.
    # E.g., for generation: prompt used, model, parameters

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None  # User or system that created the record


# Future: LineageGraph class for traversing relationships
# Future: LineageQuery class for searching lineage
