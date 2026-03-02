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

from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.exif import EXIFAnalyzer
from analyzers.phash import PerceptualHashAnalyzer
from analyzers.objects import ObjectDetectionAnalyzer
from analyzers.vlm import VLMAnalyzer

__all__ = [
    "BaseAnalyzer",
    "AnalyzerResult",
    "EXIFAnalyzer",
    "PerceptualHashAnalyzer",
    "ObjectDetectionAnalyzer",
    "VLMAnalyzer",
]