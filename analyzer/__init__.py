"""
Pluggable analyzers module.

Analyzers extract information from assets:
- EXIFAnalyzer: Technical metadata from images
- PerceptualHashAnalyzer: Hashes for duplicate detection
- ObjectDetectionAnalyzer: Detect objects/subjects
- VLMAnalyzer: AI-generated descriptions

All analyzers implement the BaseAnalyzer protocol.
New analyzers can be registered with the DI container.
"""

from ingest_core.analyzers.base import BaseAnalyzer, AnalyzerResult
from ingest_core.analyzers.exif import EXIFAnalyzer
from ingest_core.analyzers.phash import PerceptualHashAnalyzer
from ingest_core.analyzers.objects import ObjectDetectionAnalyzer
from ingest_core.analyzers.vlm import VLMAnalyzer

__all__ = [
    "BaseAnalyzer",
    "AnalyzerResult",
    "EXIFAnalyzer",
    "PerceptualHashAnalyzer",
    "ObjectDetectionAnalyzer",
    "VLMAnalyzer",
]