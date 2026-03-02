"""
Base analyzer protocol.

Defines the interface all analyzers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AnalyzerResult:
    """
    Result from an analyzer.

    Attributes:
        analyzer_name: Name of the analyzer that produced this result
        success: Whether analysis succeeded
        data: Analysis results (analyzer-specific)
        error: Error message if failed
    """
    analyzer_name: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class BaseAnalyzer(ABC):
    """
    Abstract base class for all analyzers.

    Analyzers extract specific information from assets.
    All analyzers must implement the analyze method.

    Example:
        class MyAnalyzer(BaseAnalyzer):
            name = "my_analyzer"
            supported_types = ["image", "video"]

            async def analyze(self, file_path: Path, asset_type: str) -> AnalyzerResult:
                # ... implementation
    """

    # Override in subclasses
    name: str = "base"
    supported_types: list[str] = []  # ["image", "video", "3d"]

    def supports(self, asset_type: str) -> bool:
        """Check if analyzer supports this asset type."""
        return asset_type in self.supported_types

    @abstractmethod
    async def analyze(self, file_path: Path, asset_type: str, **kwargs) -> AnalyzerResult:
        """
        Analyze an asset file.

        Args:
            file_path: Path to the file to analyze
            asset_type: Type of asset (image, video, 3d)
            **kwargs: Additional analyzer-specific arguments

        Returns:
            AnalyzerResult: Analysis results
        """
        pass