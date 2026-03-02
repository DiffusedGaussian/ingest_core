"""
Domain models module.

Contains all Pydantic models representing domain entities:
- Asset: Base class for all media assets
- ImageAsset, VideoAsset, Asset3D: Specific asset types
- Metadata models for each asset type
- Lineage models (interface only for v1)
"""

from models.asset import Asset, AssetStatus, AssetType
from models.image import ImageAsset, ImageMetadata
from models.video import VideoAsset, VideoMetadata, KeyFrame
from models.asset_3d import Asset3D, Asset3DMetadata
from models.analysis import AnalysisResult, VLMDescription, PerceptualHash, ObjectDetection
from models.lineage import LineageRecord, LineageType

__all__ = [
    "Asset", "AssetStatus", "AssetType",
    "ImageAsset", "ImageMetadata",
    "VideoAsset", "VideoMetadata", "KeyFrame",
    "Asset3D", "Asset3DMetadata",
    "AnalysisResult", "VLMDescription", "PerceptualHash", "ObjectDetection",
    "LineageRecord", "LineageType",
]