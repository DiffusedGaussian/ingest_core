"""
Base processor protocol.

Defines the interface for media processors.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseProcessor(ABC):
    """
    Abstract base class for media processors.

    Processors handle format-specific operations like:
    - Validation
    - Metadata extraction
    - Thumbnail/preview generation
    - Format conversion
    """

    name: str = "base"
    supported_extensions: list[str] = []

    def supports(self, file_path: Path) -> bool:
        """Check if processor supports this file type."""
        return file_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    async def validate(self, file_path: Path) -> tuple[bool, str | None]:
        """
        Validate a file.

        Args:
            file_path: Path to file

        Returns:
            tuple[bool, str | None]: (is_valid, error_message)
        """
        pass

    @abstractmethod
    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """
        Extract basic metadata from file.

        Args:
            file_path: Path to file

        Returns:
            dict: Extracted metadata
        """
        pass

    @abstractmethod
    async def generate_thumbnail(self, file_path: Path, output_path: Path, size: tuple[int, int] = (256, 256)) -> Path | None:
        """
        Generate thumbnail/preview.

        Args:
            file_path: Source file path
            output_path: Where to save thumbnail
            size: Thumbnail dimensions

        Returns:
            Path | None: Path to thumbnail or None if failed
        """
        pass
