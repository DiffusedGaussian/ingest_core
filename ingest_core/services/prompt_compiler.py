"""
Prompt Compiler Service.

Bridges VideoPromptAnalysis (VLM extraction) to StructuredPrompt (category schema)
and compiles to model-specific prompt strings.

Workflow:
1. VideoPromptAnalysis (from VLM) → StructuredPrompt (categories)
2. StructuredPrompt → ModelAdapter → Final prompt string
"""

from typing import TYPE_CHECKING
from uuid import UUID

from structlog import get_logger

from ingest_core.adapters import get_adapter
from ingest_core.models.prompt_schema import (
    StructuredPrompt,
    PromptCategory,
    CategoryName
)
from ingest_core.models.video_prompt import VideoPromptAnalysis

if TYPE_CHECKING:
    from ingest_core.container.container import Container

logger = get_logger()


class PromptCompilerService:
    """
    Compiles structured prompts from VLM analysis.
    
    This service:
    1. Maps VideoPromptAnalysis → StructuredPrompt
    2. Applies category overrides (for ablation)
    3. Compiles to model-specific strings via adapters
    """
    
    def __init__(self, container: "Container"):
        self.container = container
    
    async def create_structured_prompt(
        self,
        asset_id: UUID,
        overrides: dict[str, str] | None = None,
        force_reanalyze: bool = False,
    ) -> StructuredPrompt:
        """
        Create StructuredPrompt from asset's VLM analysis.
        
        Args:
            asset_id: Asset to create prompt for
            overrides: Category overrides (e.g., {"lighting": "studio lighting"})
            force_reanalyze: Force new VLM analysis even if cached
            
        Returns:
            StructuredPrompt with all categories populated
        """
        # Get or create VLM analysis
        analysis = await self.container.prompt_generator.analyze_image(
            asset_id, force=force_reanalyze
        )
        
        # Map analysis to structured prompt
        structured = self._map_analysis_to_structured(asset_id, analysis)
        
        # Apply overrides
        if overrides:
            for category_name, value in overrides.items():
                structured.set_category(category_name, value, lock=True)
        
        # Save to asset metadata
        await self._save_structured_prompt(asset_id, structured)
        
        return structured
    
    def _map_analysis_to_structured(
        self, 
        asset_id: UUID, 
        analysis: VideoPromptAnalysis
    ) -> StructuredPrompt:
        """Map VideoPromptAnalysis fields to StructuredPrompt categories."""
        
        # Subject category
        subject_parts = [analysis.subject.description]
        if analysis.subject.pose_or_state:
            subject_parts.append(analysis.subject.pose_or_state)
        subject_value = ", ".join(p for p in subject_parts if p)
        
        # Appearance category
        appearance_parts = []
        if analysis.subject.clothing_or_appearance:
            appearance_parts.append(analysis.subject.clothing_or_appearance)
        if analysis.subject.movable_elements:
            appearance_parts.extend(analysis.subject.movable_elements[:2])
        appearance_value = ", ".join(appearance_parts)
        
        # Environment category
        env_parts = [analysis.scene.location]
        if analysis.scene.setting_type and analysis.scene.setting_type != "outdoor":
            env_parts.append(analysis.scene.setting_type)
        if analysis.scene.weather:
            env_parts.append(analysis.scene.weather)
        environment_value = ", ".join(p for p in env_parts if p and p != "Scene")
        
        # Lighting category
        lighting_parts = [analysis.lighting.quality]
        if analysis.lighting.color_temperature and analysis.lighting.color_temperature != "neutral":
            lighting_parts.append(analysis.lighting.color_temperature)
        if analysis.scene.time_of_day:
            lighting_parts.append(analysis.scene.time_of_day.value.replace("_", " "))
        lighting_value = " ".join(p for p in lighting_parts if p)
        
        # Camera category
        if analysis.motion.camera_suggestions:
            camera_value = analysis.motion.camera_suggestions[0].value
        else:
            camera_value = "dolly_in"
        
        # Motion category
        motion_parts = analysis.motion.subject_motions[:2] + analysis.motion.environmental_motions[:1]
        motion_value = ", ".join(motion_parts) if motion_parts else "subtle movement"
        
        # Mood category
        mood_value = analysis.mood.value if analysis.mood else "neutral"
        if analysis.mood_descriptors:
            mood_value = f"{mood_value}, {', '.join(analysis.mood_descriptors[:2])}"
        
        # Style category
        style_parts = [analysis.style.medium]
        if analysis.style.aesthetic:
            style_parts.append(analysis.style.aesthetic)
        if analysis.style.lens_characteristics:
            style_parts.append(analysis.style.lens_characteristics)
        style_value = ", ".join(p for p in style_parts if p)
        
        # Technical category
        tech_parts = ["high quality", "4K"]
        if analysis.aspect_ratio:
            tech_parts.append(analysis.aspect_ratio)
        if analysis.shot_type:
            tech_parts.append(analysis.shot_type.value.replace("_", " "))
        technical_value = ", ".join(tech_parts)
        
        return StructuredPrompt(
            asset_id=asset_id,
            source_analysis_id=analysis.id,
            created_from="vlm",
            subject=PromptCategory(name=CategoryName.SUBJECT, value=subject_value, source="vlm"),
            appearance=PromptCategory(name=CategoryName.APPEARANCE, value=appearance_value, source="vlm"),
            environment=PromptCategory(name=CategoryName.ENVIRONMENT, value=environment_value or "scene", source="vlm"),
            lighting=PromptCategory(name=CategoryName.LIGHTING, value=lighting_value or "natural lighting", source="vlm"),
            camera=PromptCategory(name=CategoryName.CAMERA, value=camera_value, source="vlm"),
            motion=PromptCategory(name=CategoryName.MOTION, value=motion_value, source="vlm"),
            mood=PromptCategory(name=CategoryName.MOOD, value=mood_value, source="vlm"),
            style=PromptCategory(name=CategoryName.STYLE, value=style_value or "photorealistic", source="vlm"),
            technical=PromptCategory(name=CategoryName.TECHNICAL, value=technical_value, source="vlm"),
        )
    
    def compile_prompt(
        self,
        structured: StructuredPrompt,
        target_model: str = "kling",
    ) -> str:
        """
        Compile StructuredPrompt to model-specific string.
        
        Args:
            structured: The structured prompt
            target_model: Target model name (e.g., "kling", "runway")
            
        Returns:
            Final prompt string optimized for the target model
        """
        adapter = get_adapter(target_model)
        return adapter.compile(structured)
    
    def compile_with_negative(
        self,
        structured: StructuredPrompt,
        target_model: str = "kling",
    ) -> tuple[str, str]:
        """
        Compile with negative prompt.
        
        Returns:
            Tuple of (positive_prompt, negative_prompt)
        """
        adapter = get_adapter(target_model)
        
        if hasattr(adapter, "compile_with_negative"):
            return adapter.compile_with_negative(structured)
        
        # Fallback: just compile positive
        return adapter.compile(structured), ""
    
    async def create_and_compile(
        self,
        asset_id: UUID,
        target_model: str = "kling",
        overrides: dict[str, str] | None = None,
    ) -> tuple[StructuredPrompt, str]:
        """
        Full workflow: analyze → structure → compile.
        
        Args:
            asset_id: Asset to process
            target_model: Target model name
            overrides: Category overrides
            
        Returns:
            Tuple of (StructuredPrompt, compiled_string)
        """
        structured = await self.create_structured_prompt(asset_id, overrides)
        compiled = self.compile_prompt(structured, target_model)
        return structured, compiled
    
    async def _save_structured_prompt(
        self, 
        asset_id: UUID, 
        prompt: StructuredPrompt
    ) -> None:
        """Save structured prompt to asset metadata."""
        asset = await self.container.asset_service.get(asset_id)
        if asset:
            asset.extra_metadata["structured_prompt"] = prompt.model_dump(mode="json")
            db = self.container.db
            if self.container.settings.database_backend == "mongodb":
                await db.assets.update_one(
                    {"_id": str(asset_id)}, 
                    {"$set": {"extra_metadata": asset.extra_metadata}}
                )
            else:
                await db.update_asset_metadata(asset_id, asset.extra_metadata)
