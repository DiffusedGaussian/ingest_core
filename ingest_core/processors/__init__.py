"""
Media processors module.

Processors handle format-specific operations:
- ImageProcessor: Image loading, validation, thumbnail generation
- VideoProcessor: Keyframe extraction, audio extraction, transcription
- Asset3DProcessor: 3D file parsing (stub for future)

Processors are not analyzers - they prepare files for analysis.
"""

from ingest_core.processors.asset_3d import Asset3DProcessor
from ingest_core.processors.base import BaseProcessor
from ingest_core.processors.image import ImageProcessor
from ingest_core.processors.video import VideoProcessor

__all__ = [
    "BaseProcessor",
    "ImageProcessor",
    "VideoProcessor",
    "Asset3DProcessor",
]
