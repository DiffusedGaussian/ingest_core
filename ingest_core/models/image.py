"""
Image asset model with image-specific metadata.
"""

from pydantic import BaseModel, Field

from ingest_core.models.asset import Asset, AssetType


class ImageMetadata(BaseModel):
    """Image-specific technical metadata (EXIF + computed)."""

    # Dimensions
    width: int
    height: int
    aspect_ratio: float

    # Color
    color_mode: str  # RGB, RGBA, L (grayscale), etc.
    bit_depth: int | None = None
    has_alpha: bool = False

    # EXIF data (optional, from camera)
    camera_make: str | None = None
    camera_model: str | None = None
    focal_length: float | None = None
    aperture: float | None = None
    iso: int | None = None
    shutter_speed: str | None = None
    date_taken: str | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None

    # Computed
    is_landscape: bool = False
    is_portrait: bool = False
    is_square: bool = False
    dominant_colors: list[str] = Field(default_factory=list)  # Hex colors


class ImageAsset(Asset):
    """
    Image asset with image-specific metadata.

    Supports: JPEG, PNG, WebP, GIF, TIFF, BMP
    """
    asset_type: AssetType = AssetType.IMAGE
    metadata: ImageMetadata | None = None
