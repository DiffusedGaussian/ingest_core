"""
Media processors module.

Processors handle format-specific operations:
- ImageProcessor: Image loading, validation, thumbnail generation
- VideoProcessor: Keyframe extraction, audio extraction, transcription
- Asset3DProcessor: 3D file parsing (stub for future)

Processors are not analyzers - they prepare files for analysis.
"""

from processors.base import BaseProcessor
from processors.image import ImageProcessor
from processors.video import VideoProcessor
from processors.asset_3d import Asset3DProcessor

__all__ = [
    "BaseProcessor",
    "ImageProcessor",
    "VideoProcessor",
    "Asset3DProcessor",
]