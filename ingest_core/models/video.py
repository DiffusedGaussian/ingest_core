"""
Video asset model with video-specific metadata and keyframes.
"""

from pydantic import BaseModel, Field

from ingest_core.models.asset import Asset, AssetType


class KeyFrame(BaseModel):
    """Extracted keyframe from video."""

    frame_number: int
    timestamp_seconds: float
    storage_path: str  # Path to extracted frame image
    is_scene_change: bool = False


class VideoMetadata(BaseModel):
    """Video-specific technical metadata."""

    # Dimensions
    width: int
    height: int
    aspect_ratio: float

    # Duration & timing
    duration_seconds: float
    frame_rate: float
    total_frames: int

    # Codec info
    video_codec: str | None = None
    audio_codec: str | None = None
    bitrate_kbps: int | None = None

    # Audio
    has_audio: bool = False
    audio_channels: int | None = None
    audio_sample_rate: int | None = None

    # Extracted content
    keyframes: list[KeyFrame] = Field(default_factory=list)
    transcript: str | None = None  # From Whisper
    transcript_segments: list[dict] = Field(default_factory=list)  # Timestamped segments


class VideoAsset(Asset):
    """
    Video asset with video-specific metadata.

    Supports: MP4, MOV, AVI, WebM, MKV
    Max duration: 30 seconds (configurable)
    """
    asset_type: AssetType = AssetType.VIDEO
    metadata: VideoMetadata | None = None