"""
Image processor implementation.
"""

from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from structlog import get_logger

from ingest_core.processors.base import BaseProcessor

logger = get_logger()


class ImageProcessor(BaseProcessor):
    """
    Processor for standard image formats.
    """

    name = "image"
    supported_extensions = [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp", ".gif"]

    async def validate(self, file_path: Path) -> tuple[bool, str | None]:
        """
        Validate an image file.
        """
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True, None
        except UnidentifiedImageError:
            return False, "Invalid image format or corrupted file"
        except Exception as e:
            logger.error("Image validation failed", path=str(file_path), error=str(e))
            return False, str(e)

    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """
        Extract image metadata (dimensions, format, mode).
        """
        try:
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "animated": getattr(img, "is_animated", False),
                    "frames": getattr(img, "n_frames", 1),
                }
        except Exception as e:
            logger.error("Metadata extraction failed", path=str(file_path), error=str(e))
            return {}

    async def generate_thumbnail(
        self,
        file_path: Path,
        output_path: Path,
        size: tuple[int, int] = (256, 256)
    ) -> Path | None:
        """
        Generate a thumbnail.
        """
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary (e.g. for RGBA/P/CMYK to JPEG)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.thumbnail(size)

                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Save as JPEG for consistency
                img.save(output_path, "JPEG", quality=85)
                return output_path

        except Exception as e:
            logger.error("Thumbnail generation failed", path=str(file_path), error=str(e))
            return None
