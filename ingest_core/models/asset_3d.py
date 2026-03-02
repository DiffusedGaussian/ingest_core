"""
3D asset model - STUB for future implementation.

This module is a placeholder for 3D asset support (GLB, FBX).
The interface is defined but implementation is deferred.
"""

from pydantic import BaseModel, Field

from ingest_core.models.asset import Asset, AssetType


class Asset3DMetadata(BaseModel):
    """
    3D asset metadata - STUB.

    Future implementation will include:
    - Vertex/polygon counts
    - Texture information
    - Material definitions
    - Bounding box dimensions
    - Animation data
    """

    # Basic info (to be expanded)
    vertex_count: int | None = None
    polygon_count: int | None = None
    has_textures: bool = False
    has_animations: bool = False

    # Bounding box
    bbox_width: float | None = None
    bbox_height: float | None = None
    bbox_depth: float | None = None

    # Format-specific
    format_version: str | None = None
    material_count: int | None = None
    texture_paths: list[str] = Field(default_factory=list)


class Asset3D(Asset):
    """
    3D asset - STUB for future implementation.

    Planned support: GLB/GLTF, FBX
    """
    asset_type: AssetType = AssetType.ASSET_3D
    metadata: Asset3DMetadata | None = None