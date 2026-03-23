"""
Kling Video Model Adapter.

Compiles StructuredPrompt to Kling's preferred prompt format.
All configuration is read from settings.adapters.kling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingest_core.config.settings import Settings, KlingAdapterSettings

from ingest_core.adapters.base import BaseModelAdapter
from ingest_core.models.prompt_schema import StructuredPrompt


class KlingAdapter(BaseModelAdapter):
    """
    Adapter for Kling video generation model.
    
    Kling works best with:
    - Natural language descriptions
    - Explicit camera movement keywords
    - Clear subject-first structure
    """
    
    name = "kling"
    
    def _get_adapter_config(self) -> "KlingAdapterSettings":
        """Get Kling config from settings."""
        return self.settings.adapters.kling
    
    def compile(self, prompt: StructuredPrompt) -> str:
        """
        Compile to Kling-optimized prompt string.
        
        Structure: [Subject + Appearance]. [Environment + Lighting]. 
                   [Camera + Motion]. [Style + Mood]. [Technical].
        """
        parts = []
        
        # 1. Subject block
        subject_parts = []
        if prompt.subject and prompt.subject.value:
            subject_parts.append(prompt.subject.value)
        if prompt.appearance and prompt.appearance.value:
            subject_parts.append(prompt.appearance.value)
        if subject_parts:
            parts.append(", ".join(subject_parts))
        
        # 2. Environment block
        env_parts = []
        if prompt.environment and prompt.environment.value:
            env_parts.append(f"in {prompt.environment.value}")
        if prompt.lighting and prompt.lighting.value:
            lighting = self.get_lighting_term(prompt.lighting.value)
            env_parts.append(lighting)
        if env_parts:
            parts.append(", ".join(env_parts))
        
        # 3. Camera + Motion block
        motion_parts = []
        if prompt.camera and prompt.camera.value:
            camera = self.get_camera_term(prompt.camera.value)
            motion_parts.append(camera)
        if prompt.motion and prompt.motion.value:
            motion_parts.append(prompt.motion.value)
        if motion_parts:
            parts.append(", ".join(motion_parts))
        
        # 4. Style + Mood block
        style_parts = []
        if prompt.mood and prompt.mood.value:
            style_parts.append(f"{prompt.mood.value} atmosphere")
        if prompt.style and prompt.style.value:
            style_parts.append(prompt.style.value)
        if style_parts:
            parts.append(", ".join(style_parts))
        
        # 5. Technical block
        if prompt.technical and prompt.technical.value:
            parts.append(prompt.technical.value)
        
        # 6. Product (if present)
        if prompt.product and prompt.product.value:
            parts.insert(1, f"featuring {prompt.product.value}")
        
        # Join with separator from settings
        result = self.separator.join(p for p in parts if p)
        
        return result
    
    def compile_with_negative(self, prompt: StructuredPrompt) -> tuple[str, str]:
        """
        Compile prompt with negative prompt.
        
        Returns:
            Tuple of (positive_prompt, negative_prompt)
        """
        positive = self.compile(prompt)
        negative = self.get_negative_prompt()
        return positive, negative
