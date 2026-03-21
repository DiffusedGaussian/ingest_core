"""
Object detection analyzer.

Detects objects and subjects in images using VLM or dedicated models.
"""

from pathlib import Path

from ingest_core.analyzers.base import AnalyzerResult, BaseAnalyzer
from ingest_core.config import Settings


class ObjectDetectionAnalyzer(BaseAnalyzer):
    """
    Detect objects and subjects in images.

    Uses Gemini Vision for object detection (can be extended
    to use dedicated models like YOLO).

    Extracts:
    - List of detected objects
    - Primary subject
    - Object counts
    """

    name = "objects"
    supported_types = ["image"]

    def __init__(self, settings: Settings):
        """
        Initialize object detection analyzer.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._client = None

    def _get_client(self):
        """Lazy-load Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini.api_key)
            self._client = genai.GenerativeModel(self.settings.gemini.model)
        return self._client

    async def analyze(self, file_path: Path, asset_type: str, **kwargs) -> AnalyzerResult:
        """Detect objects in image using Gemini Vision."""
        try:
            from PIL import Image

            # Load image
            img = Image.open(file_path)

            # Prompt for object detection
            prompt = """Analyze this image and list all objects, subjects, and elements you can identify.

Return your response in this exact format:
OBJECTS: [comma-separated list of all detected objects]
PRIMARY_SUBJECT: [the main subject or focus of the image]
SCENE_TYPE: [e.g., indoor, outdoor, portrait, landscape, product, etc.]

Be specific and comprehensive."""

            # Call Gemini
            client = self._get_client()
            response = client.generate_content([prompt, img])

            # Parse response
            text = response.text
            data = self._parse_response(text)

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

    def _parse_response(self, text: str) -> dict:
        """Parse Gemini response into structured data."""
        data = {
            "objects": [],
            "primary_subject": None,
            "scene_type": None,
            "object_counts": {},
        }

        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()

            if line.startswith("OBJECTS:"):
                objects_str = line.replace("OBJECTS:", "").strip()
                objects = [obj.strip() for obj in objects_str.split(",")]
                data["objects"] = objects

                # Count objects
                for obj in objects:
                    obj_lower = obj.lower()
                    data["object_counts"][obj_lower] = data["object_counts"].get(obj_lower, 0) + 1

            elif line.startswith("PRIMARY_SUBJECT:"):
                data["primary_subject"] = line.replace("PRIMARY_SUBJECT:", "").strip()

            elif line.startswith("SCENE_TYPE:"):
                data["scene_type"] = line.replace("SCENE_TYPE:", "").strip()

        return data
