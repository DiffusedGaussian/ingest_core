"""
Domain models module.

Contains all Pydantic models representing domain entities:
- Asset: Base class for all media assets
- ImageAsset, VideoAsset, Asset3D: Specific asset types
- Metadata models for each asset type
- Lineage models (interface only for v1)
"""

from ingest_core.models.analysis import (
    AnalysisResult,
    ObjectDetection,
    PerceptualHash,
    VLMDescription,
)
from ingest_core.models.asset import Asset, AssetStatus, AssetType
from ingest_core.models.asset_3d import Asset3D, Asset3DMetadata
from ingest_core.models.generation import (
    GenerationJob,
    GenerationJobSummary,
    GeneratorType,
    JobStatus,
)
from ingest_core.models.image import ImageAsset, ImageMetadata
from ingest_core.models.lineage import LineageRecord, LineageType
from ingest_core.models.video import KeyFrame, VideoAsset, VideoMetadata

__all__ = [
    "Asset", "AssetStatus", "AssetType",
    "ImageAsset", "ImageMetadata",
    "VideoAsset", "VideoMetadata", "KeyFrame",
    "Asset3D", "Asset3DMetadata",
    "AnalysisResult", "VLMDescription", "PerceptualHash", "ObjectDetection",
    "LineageRecord", "LineageType",
    "GenerationJob", "GenerationJobSummary", "GeneratorType", "JobStatus",
]
