"""
Flux Image-to-Image Adapter.

Specialized adapter for transforming technical drawings (CAD, blueprints, 
construction plans, schematics) into photorealistic 3D visualizations.

Flux excels at:
- img2img transformations with strong structural adherence
- Technical/engineering visualization
- Material and lighting specification
- High-fidelity detail preservation

This adapter is optimized for construction/engineering workflows where
the input is a line drawing and the output should be a realistic render.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingest_core.config.settings import Settings, FluxAdapterSettings

from ingest_core.adapters.base import BaseModelAdapter
from ingest_core.models.prompt_schema import StructuredPrompt


class FluxAdapter(BaseModelAdapter):
    """
    Adapter for Flux image-to-image generation.
    
    Optimized for technical drawing → photorealistic render workflows.
    
    Flux img2img works best with:
    - Explicit "transform/convert" language referencing source
    - Detailed material specifications (not just "metal" but "brushed stainless steel")
    - Render engine style keywords (octane, vray, arnold)
    - Strong lighting direction
    - Clean backgrounds for technical subjects
    """
    
    name = "flux"
    
    def _get_adapter_config(self) -> "FluxAdapterSettings":
        """Get Flux config from settings."""
        return self.settings.adapters.flux
    
    def compile(self, prompt: StructuredPrompt) -> str:
        """
        Compile to Flux img2img optimized prompt.
        
        Structure for technical drawings:
        [Transformation intent]. [Subject with materials]. [View/perspective].
        [Lighting setup]. [Render style]. [Technical quality].
        
        The key insight for Flux img2img is that we need to:
        1. Reference the source image transformation explicitly
        2. Specify materials in detail (Flux is excellent at materials)
        3. Use render engine vocabulary
        4. Keep structure adherent keywords
        """
        parts = []
        
        # 1. Transformation prefix - tells Flux this is img2img
        transformation = self._build_transformation_prefix(prompt)
        if transformation:
            parts.append(transformation)
        
        # 2. Subject with detailed materials
        subject_block = self._build_subject_block(prompt)
        if subject_block:
            parts.append(subject_block)
        
        # 3. View/Perspective (important for technical drawings)
        perspective = self._build_perspective_block(prompt)
        if perspective:
            parts.append(perspective)
        
        # 4. Environment (usually minimal for technical subjects)
        environment = self._build_environment_block(prompt)
        if environment:
            parts.append(environment)
        
        # 5. Lighting setup
        lighting = self._build_lighting_block(prompt)
        if lighting:
            parts.append(lighting)
        
        # 6. Render style
        style = self._build_style_block(prompt)
        if style:
            parts.append(style)
        
        # 7. Technical quality boosters
        quality = self._build_quality_block(prompt)
        if quality:
            parts.append(quality)
        
        # Join with appropriate separator
        result = self.separator.join(p for p in parts if p)
        
        # Enforce max length
        if len(result) > self.max_length:
            result = result[:self.max_length - 3] + "..."
        
        return result
    
    def _build_transformation_prefix(self, prompt: StructuredPrompt) -> str:
        """
        Build the transformation intent prefix.
        
        This tells Flux how to interpret the source image.
        """
        # Check if there's explicit transformation intent in technical field
        if prompt.technical and prompt.technical.value:
            tech = prompt.technical.value.lower()
            if any(kw in tech for kw in ["transform", "convert", "render", "visualize"]):
                return ""  # Already specified, don't duplicate
        
        # Default transformation prefix for technical drawings
        prefixes = self._config.transformation_prefixes
        
        # Try to detect drawing type from subject
        drawing_type = "technical"
        if prompt.subject and prompt.subject.value:
            subj = prompt.subject.value.lower()
            if any(kw in subj for kw in ["blueprint", "floor plan", "architectural"]):
                drawing_type = "architectural"
            elif any(kw in subj for kw in ["schematic", "circuit", "electronic"]):
                drawing_type = "schematic"
            elif any(kw in subj for kw in ["mechanical", "cad", "engineering", "assembly"]):
                drawing_type = "mechanical"
            elif any(kw in subj for kw in ["construction", "structural"]):
                drawing_type = "construction"
        
        return prefixes.get(drawing_type, prefixes["technical"])
    
    def _build_subject_block(self, prompt: StructuredPrompt) -> str:
        """
        Build subject description with detailed materials.
        
        Flux excels at material rendering, so we expand material descriptions.
        """
        parts = []
        
        if prompt.subject and prompt.subject.value:
            parts.append(prompt.subject.value)
        
        # Expand appearance into detailed materials
        if prompt.appearance and prompt.appearance.value:
            materials = self._expand_materials(prompt.appearance.value)
            parts.append(materials)
        
        return ", ".join(parts) if parts else ""
    
    def _expand_materials(self, appearance: str) -> str:
        """
        Expand generic material terms into detailed Flux-friendly descriptions.
        """
        material_expansions = self._config.material_vocabulary
        
        result = appearance
        for generic, detailed in material_expansions.items():
            # Case-insensitive replacement, preserve surrounding context
            import re
            pattern = rf'\b{re.escape(generic)}\b'
            result = re.sub(pattern, detailed, result, flags=re.IGNORECASE)
        
        return result
    
    def _build_perspective_block(self, prompt: StructuredPrompt) -> str:
        """
        Build perspective/view specification.
        
        For technical drawings, view angle is crucial for proper transformation.
        """
        if prompt.camera and prompt.camera.value:
            camera = prompt.camera.value.lower()
            perspective_vocab = self._config.perspective_vocabulary
            return perspective_vocab.get(camera, prompt.camera.value)
        
        # Default perspective for technical drawings
        return self._config.default_perspective
    
    def _build_environment_block(self, prompt: StructuredPrompt) -> str:
        """
        Build environment specification.
        
        Technical renders often use neutral/studio environments.
        """
        if prompt.environment and prompt.environment.value:
            return prompt.environment.value
        
        # Default to clean studio for technical subjects
        return self._config.default_environment
    
    def _build_lighting_block(self, prompt: StructuredPrompt) -> str:
        """
        Build detailed lighting setup.
        
        Good lighting is crucial for photorealistic technical renders.
        """
        if prompt.lighting and prompt.lighting.value:
            lighting_term = self.get_lighting_term(prompt.lighting.value)
            return lighting_term
        
        # Default studio lighting for technical subjects
        return self._config.default_lighting
    
    def _build_style_block(self, prompt: StructuredPrompt) -> str:
        """
        Build render style specification.
        
        Flux responds well to render engine vocabulary.
        """
        parts = []
        
        if prompt.style and prompt.style.value:
            parts.append(prompt.style.value)
        
        if prompt.mood and prompt.mood.value:
            parts.append(prompt.mood.value)
        
        # Add render engine style if not already specified
        if parts:
            combined = " ".join(parts).lower()
            if not any(engine in combined for engine in ["octane", "vray", "arnold", "cycles", "corona"]):
                parts.append(self._config.default_render_style)
        else:
            parts.append(self._config.default_render_style)
        
        return ", ".join(parts)
    
    def _build_quality_block(self, prompt: StructuredPrompt) -> str:
        """
        Build technical quality boosters.
        """
        boosters = self._config.quality_boosters.copy()
        
        # Add structure adherence keywords for img2img
        boosters.extend(self._config.structure_keywords)
        
        return ", ".join(boosters)
    
    def compile_with_negative(self, prompt: StructuredPrompt) -> tuple[str, str]:
        """
        Compile prompt with negative prompt.
        
        Returns:
            Tuple of (positive_prompt, negative_prompt)
        """
        positive = self.compile(prompt)
        negative = self.get_negative_prompt()
        return positive, negative
    
    def compile_for_drawing_type(
        self, 
        prompt: StructuredPrompt, 
        drawing_type: str = "technical"
    ) -> str:
        """
        Compile with explicit drawing type for better transformation.
        
        Args:
            prompt: The structured prompt
            drawing_type: One of "technical", "architectural", "mechanical", 
                         "schematic", "construction"
        
        Returns:
            Optimized prompt string
        """
        # Override the transformation prefix
        prefix = self._config.transformation_prefixes.get(
            drawing_type, 
            self._config.transformation_prefixes["technical"]
        )
        
        # Get the standard compilation
        standard = self.compile(prompt)
        
        # Replace the detected prefix with explicit one
        # (compile() may have auto-detected a different type)
        for p in self._config.transformation_prefixes.values():
            if standard.startswith(p):
                standard = standard[len(p):].lstrip(", .")
                break
        
        return f"{prefix}, {standard}"
    
    def get_img2img_parameters(self) -> dict:
        """
        Get recommended img2img parameters for Flux.
        
        Returns dict with strength, guidance_scale, etc.
        """
        return {
            "strength": self._config.default_strength,
            "guidance_scale": self._config.default_guidance_scale,
            "num_inference_steps": self._config.default_steps,
        }
