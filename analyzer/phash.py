"""
Perceptual hash analyzer.

Computes perceptual hashes for duplicate/similarity detection.
"""

from pathlib import Path
from PIL import Image
import imagehash

from ingest_core.analyzers.base import BaseAnalyzer, AnalyzerResult


class PerceptualHashAnalyzer(BaseAnalyzer):
    """
    Compute perceptual hashes for images.

    Computes multiple hash types:
    - pHash: Perceptual hash (DCT-based)
    - dHash: Difference hash
    - aHash: Average hash
    - wHash: Wavelet hash

    Used for duplicate detection and finding similar images.
    """

    name = "phash"
    supported_types = ["image"]

    async def analyze(self, file_path: Path, asset_type: str, **kwargs) -> AnalyzerResult:
        """Compute perceptual hashes for image."""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # Compute multiple hash types
                data = {
                    "phash": str(imagehash.phash(img)),
                    "dhash": str(imagehash.dhash(img)),
                    "ahash": str(imagehash.average_hash(img)),
                    "whash": str(imagehash.whash(img)),
                }

                return AnalyzerResult(
                    analyzer_name=self.name,
                    success=True,
                    data=data,
                )

        except Exception as e:
            return AnalyzerResult(
                analyzer_name=self.name,
                success=False,
                error=str(e),
            )

    @staticmethod
    def compute_distance(hash1: str, hash2: str) -> int:
        """
        Compute Hamming distance between two hashes.

        Lower distance = more similar.
        Distance of 0 = identical (or near-identical) images.
        Distance < 10 = very similar images.

        Args:
            hash1: First hash string
            hash2: Second hash string

        Returns:
            int: Hamming distance
        """
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2

    @staticmethod
    def are_similar(hash1: str, hash2: str, threshold: int = 10) -> bool:
        """
        Check if two hashes indicate similar images.

        Args:
            hash1: First hash string
            hash2: Second hash string
            threshold: Max distance to consider similar (default 10)

        Returns:
            bool: True if images are similar
        """
        distance = PerceptualHashAnalyzer.compute_distance(hash1, hash2)
        return distance <= threshold