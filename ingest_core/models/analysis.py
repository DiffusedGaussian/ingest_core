"""
Analysis result models.

Contains models for all analyzer outputs:
- VLM descriptions
- Perceptual hashes
- Object detection results
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VLMDescription(BaseModel):
    """VLM-generated description of an asset."""

    asset_id: UUID
    provider: str  # "gemini" or "llava"
    model: str  # Specific model used

    # Generated content
    description: str
    tags: list[str] = Field(default_factory=list)
    detected_objects: list[str] = Field(default_factory=list)
    detected_text: str | None = None  # OCR if present
    style_descriptors: list[str] = Field(default_factory=list)  # "photorealistic", "cartoon", etc.

    # Metadata
    prompt_used: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float | None = None


class PerceptualHash(BaseModel):
    """Perceptual hash for duplicate/similarity detection."""

    asset_id: UUID

    # Multiple hash types for robust matching
    phash: str  # Perceptual hash
    dhash: str | None = None  # Difference hash
    ahash: str | None = None  # Average hash
    whash: str | None = None  # Wavelet hash

    # For video: hash of representative frame
    frame_index: int | None = None  # If from video keyframe

    computed_at: datetime = Field(default_factory=datetime.utcnow)


class DetectedObject(BaseModel):
    """Single detected object in an image."""

    label: str
    confidence: float
    bounding_box: dict | None = None  # {x, y, width, height} normalized


class ObjectDetection(BaseModel):
    """Object detection results for an asset."""

    asset_id: UUID
    detector: str  # Model used (e.g., "yolov8", "gemini-vision")

    objects: list[DetectedObject] = Field(default_factory=list)

    # Summary
    object_counts: dict[str, int] = Field(default_factory=dict)  # {label: count}
    primary_subject: str | None = None  # Most prominent object

    detected_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisResult(BaseModel):
    """
    Aggregated analysis results for an asset.

    Container for all analyzer outputs associated with an asset.
    """

    asset_id: UUID

    vlm_description: VLMDescription | None = None
    perceptual_hash: PerceptualHash | None = None
    object_detection: ObjectDetection | None = None

    # Extensible for future analyzers
    custom_analyses: dict[str, dict] = Field(default_factory=dict)

    completed_at: datetime = Field(default_factory=datetime.utcnow)
