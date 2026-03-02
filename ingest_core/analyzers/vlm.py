"""
VLM (Vision Language Model) analyzer.

Generates rich descriptions of images using Gemini or local LLaVA.
"""

from pathlib import Path
from datetime import datetime

from ingest_core.analyzers.base import BaseAnalyzer, AnalyzerResult
from ingest_core.config import Settings


class VLMAnalyzer(BaseAnalyzer):
    """
    Generate rich descriptions using Vision Language Models.

    Supports:
    - Google Gemini (primary)
    - Local LLaVA (fallback/offline)

    Generates:
    - Detailed description
    - Tags
    - Style descriptors
    - Detected text (OCR)
    """

    name = "vlm"
    supported_types = ["image"]

    def __init__(self, settings: Settings):
        """
        Initialize VLM analyzer.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._gemini_client = None
        self._llava_model = None

    def _get_gemini_client(self):
        """Lazy-load Gemini client."""
        if self._gemini_client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini.api_key)
            self._gemini_client = genai.GenerativeModel(self.settings.gemini.model)
        return self._gemini_client

    def _get_llava_model(self):
        """Lazy-load local LLaVA model."""
        if self._llava_model is None and self.settings.local_vlm.enabled:
            # Import only when needed (heavy dependencies)
            from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
            import torch

            model_id = self.settings.local_vlm.model
            device = self.settings.local_vlm.device

            self._llava_processor = LlavaNextProcessor.from_pretrained(model_id)
            self._llava_model = LlavaNextForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map=device,
            )
        return self._llava_model

    async def analyze(self, file_path: Path, asset_type: str, **kwargs) -> AnalyzerResult:
        """Generate description using VLM."""
        use_local = kwargs.get("use_local", False)

        if use_local and self.settings.local_vlm.enabled:
            return await self._analyze_with_llava(file_path)
        else:
            return await self._analyze_with_gemini(file_path)

    async def _analyze_with_gemini(self, file_path: Path) -> AnalyzerResult:
        """Analyze image with Gemini."""
        try:
            from PIL import Image

            img = Image.open(file_path)

            prompt = """Analyze this image comprehensively and provide:

1. DESCRIPTION: A detailed description of the image (2-3 sentences)
2. TAGS: A comma-separated list of relevant tags (10-15 tags)
3. STYLE: Visual style descriptors (e.g., photorealistic, cartoon, minimalist, vintage)
4. TEXT: Any text visible in the image (or "None" if no text)
5. MOOD: The overall mood or atmosphere
6. COLORS: Dominant colors in the image

Format your response exactly as:
DESCRIPTION: [your description]
TAGS: [tag1, tag2, tag3, ...]
STYLE: [style1, style2, ...]
TEXT: [detected text or None]
MOOD: [mood description]
COLORS: [color1, color2, ...]"""

            client = self._get_gemini_client()
            response = client.generate_content([prompt, img])

            data = self._parse_response(response.text)
            data["provider"] = "gemini"
            data["model"] = self.settings.gemini.model
            data["prompt_used"] = prompt
            data["generated_at"] = datetime.utcnow().isoformat()

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

    async def _analyze_with_llava(self, file_path: Path) -> AnalyzerResult:
        """Analyze image with local LLaVA model."""
        try:
            from PIL import Image
            import torch

            model = self._get_llava_model()
            if model is None:
                return AnalyzerResult(
                    analyzer_name=self.name,
                    success=False,
                    error="Local VLM not enabled or failed to load",
                )

            img = Image.open(file_path)

            prompt = "[INST] <image>\nDescribe this image in detail. Include: what you see, the style, colors, mood, and any text visible. [/INST]"

            inputs = self._llava_processor(prompt, img, return_tensors="pt").to(model.device)

            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=300)

            response_text = self._llava_processor.decode(output[0], skip_special_tokens=True)

            data = {
                "description": response_text,
                "provider": "llava",
                "model": self.settings.local_vlm.model,
                "generated_at": datetime.utcnow().isoformat(),
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

    def _parse_response(self, text: str) -> dict:
        """Parse Gemini response into structured data."""
        data = {
            "description": "",
            "tags": [],
            "style_descriptors": [],
            "detected_text": None,
            "mood": None,
            "dominant_colors": [],
        }

        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()

            if line.startswith("DESCRIPTION:"):
                data["description"] = line.replace("DESCRIPTION:", "").strip()
            elif line.startswith("TAGS:"):
                tags_str = line.replace("TAGS:", "").strip()
                data["tags"] = [t.strip() for t in tags_str.split(",")]
            elif line.startswith("STYLE:"):
                style_str = line.replace("STYLE:", "").strip()
                data["style_descriptors"] = [s.strip() for s in style_str.split(",")]
            elif line.startswith("TEXT:"):
                text_val = line.replace("TEXT:", "").strip()
                data["detected_text"] = None if text_val.lower() == "none" else text_val
            elif line.startswith("MOOD:"):
                data["mood"] = line.replace("MOOD:", "").strip()
            elif line.startswith("COLORS:"):
                colors_str = line.replace("COLORS:", "").strip()
                data["dominant_colors"] = [c.strip() for c in colors_str.split(",")]

        return data