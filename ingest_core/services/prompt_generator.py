"""
Prompt Generator Service.

Analyzes images using VLM and generates optimized video prompts.
"""

import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from structlog import get_logger

from ingest_core.models.prompt_template import TEMPLATES
from ingest_core.models.video_prompt import (
    CameraMovement,
    CompositionInfo,
    GeneratedVideoPrompt,
    LightingInfo,
    MoodTone,
    MotionSuggestions,
    MovementSpeed,
    SceneInfo,
    ShotType,
    StyleInfo,
    SubjectInfo,
    TimeOfDay,
    VideoPromptAnalysis,
)

if TYPE_CHECKING:
    from ingest_core.container.container import Container

logger = get_logger()


EXTRACTION_PROMPT = '''Analyze this image for video generation. Return JSON only:
{
    "subject": {"description": "...", "position_in_frame": "center", "movable_elements": []},
    "scene": {"location": "...", "setting_type": "outdoor", "time_of_day": "golden_hour_evening"},
    "composition": {"foreground": "...", "midground": "...", "background": "..."},
    "lighting": {"primary_source": "...", "quality": "soft", "color_temperature": "warm"},
    "style": {"medium": "photorealistic", "color_palette": []},
    "shot_type": "medium_shot",
    "mood": "peaceful",
    "motion_suggestions": {"subject_motions": [], "environmental_motions": [], "camera_suggestions": ["dolly_in"], "recommended_speed": "slow"}
}'''


class PromptGeneratorService:
    """Analyzes images and generates video prompts."""

    def __init__(self, container: "Container"):
        self.container = container

    async def analyze_image(self, asset_id: UUID, force: bool = False) -> VideoPromptAnalysis:
        """Analyze image and extract structured data."""
        asset = await self.container.asset_service.get(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        existing = asset.extra_metadata.get("video_prompt_analysis")
        if existing and not force:
            return VideoPromptAnalysis.model_validate(existing)

        temp_path = await self._download_to_temp(asset)

        try:
            extraction = await self._extract_with_vlm(temp_path)
            analysis = self._build_analysis(asset_id, extraction)
            await self._save_analysis(asset_id, analysis)
            return analysis
        finally:
            if temp_path.exists():
                temp_path.unlink()

    async def generate_prompt(
        self,
        asset_id: UUID,
        camera_movement: CameraMovement | None = None,
        movement_speed: MovementSpeed | None = None,
        duration: int = 5,
        target_generator: str = "flux",
    ) -> GeneratedVideoPrompt:
        """Generate optimized video prompt."""
        analysis = await self.analyze_image(asset_id)
        camera = camera_movement or self._suggest_camera(analysis)
        speed = movement_speed or analysis.motion.recommended_speed

        # Use Flux adapter if requested
        if target_generator.lower() == "flux":
            from ingest_core.adapters.flux import FluxAdapter
            from ingest_core.models.prompt_schema import StructuredPrompt, PromptCategory, CategoryName
            
            adapter = FluxAdapter(self.container.settings)
            
            structured = StructuredPrompt(
                asset_id=asset_id,
                subject=PromptCategory(name=CategoryName.SUBJECT, value=analysis.subject.description),
                appearance=PromptCategory(name=CategoryName.APPEARANCE, value=", ".join(analysis.style.color_palette) if analysis.style.color_palette else ""),
                environment=PromptCategory(name=CategoryName.ENVIRONMENT, value=analysis.scene.location),
                lighting=PromptCategory(name=CategoryName.LIGHTING, value=analysis.lighting.quality or "natural"),
                camera=PromptCategory(name=CategoryName.CAMERA, value="isometric"),
                motion=PromptCategory(name=CategoryName.MOTION, value="static"),
                mood=PromptCategory(name=CategoryName.MOOD, value=str(analysis.mood) if analysis.mood else "neutral"),
                style=PromptCategory(name=CategoryName.STYLE, value=analysis.style.medium or "photorealistic"),
                technical=PromptCategory(name=CategoryName.TECHNICAL, value="8k, high detail"),
            )
            
            full_prompt = adapter.compile(structured)
        else:
            # Original video prompt logic
            subject_prompt = self._compose_subject_prompt(analysis)
            camera_prompt = self._compose_camera_prompt(camera, speed)
            environment_prompt = self._compose_environment_prompt(analysis)
            full_prompt = f"{subject_prompt}. {camera_prompt}. {environment_prompt}".strip()

        result = GeneratedVideoPrompt(
            asset_id=asset_id,
            analysis_id=analysis.id,
            prompt=full_prompt,
            prompt_components={"subject": analysis.subject.description, "style": analysis.style.medium},
            recommended_duration=duration,
            recommended_camera=camera,
            recommended_speed=speed,
            target_generator=target_generator,
        )
        await self._save_prompt(asset_id, result)
        return result

    async def generate_prompt_with_template(
        self,
        asset_id: UUID,
        template_id: str = "default",
        overrides: dict[str, str] | None = None,
        duration: int = 5,
        target_generator: str = "flux",
    ) -> GeneratedVideoPrompt:
        """Generate prompt using a custom template."""
        # Get analysis
        analysis = await self.analyze_image(asset_id)

        # Get template
        template = TEMPLATES.get(template_id)
        if not template:
            # Fall back to default generation
            return await self.generate_prompt(asset_id, duration=duration, target_generator=target_generator)

        # Build context from analysis
        camera = self._suggest_camera(analysis)
        speed = analysis.motion.recommended_speed

        context = {
            "subject": analysis.subject.description,
            "location": analysis.scene.location,
            "background": analysis.composition.background or "clean background",
            "camera": self._compose_camera_prompt(camera, speed),
            "motion": ". ".join(analysis.motion.subject_motions[:2]) if analysis.motion.subject_motions else "subtle movement",
            "lighting": f"{analysis.lighting.quality} {analysis.lighting.color_temperature or ''} lighting".strip(),
            "style": analysis.style.medium or "photorealistic",
            "environment": self._compose_environment_prompt(analysis),
            "clothing": ", ".join(analysis.subject.movable_elements[:2]) if analysis.subject.movable_elements else "clothing",
        }

        # Apply template defaults
        for key, value in template.defaults.items():
            if not context.get(key) or context[key] == "":
                context[key] = value

        # Apply user overrides
        if overrides:
            context.update(overrides)

        # Format template - handle missing keys gracefully
        try:
            prompt = template.template.format(**context)
        except KeyError as e:
            logger.warning(f"Template missing key: {e}, using default generation")
            return await self.generate_prompt(asset_id, duration=duration, target_generator=target_generator)

        result = GeneratedVideoPrompt(
            asset_id=asset_id,
            analysis_id=analysis.id,
            prompt=prompt,
            prompt_components=context,
            recommended_duration=duration,
            recommended_camera=camera,
            recommended_speed=speed,
            target_generator=target_generator,
        )

        await self._save_prompt(asset_id, result)
        return result

    async def _extract_with_vlm(self, file_path: Path) -> dict[str, Any]:
        """Run VLM extraction."""
        try:
            import google.generativeai as genai
            from PIL import Image

            api_key = self.container.settings.gemini.api_key
            if not api_key:
                return self._fallback_extraction(file_path)

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.container.settings.gemini.model)
            image = Image.open(file_path)
            response = model.generate_content([EXTRACTION_PROMPT, image])

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            logger.warning("VLM extraction failed", error=str(e))
            return self._fallback_extraction(file_path)

    def _fallback_extraction(self, file_path: Path) -> dict[str, Any]:
        """Basic extraction without VLM."""
        from PIL import Image
        img = Image.open(file_path)
        w, h = img.size
        shot = "wide_shot" if w/h > 2 else "close_up" if w/h < 0.7 else "medium_shot"
        return {
            "subject": {"description": "Main subject", "position_in_frame": "center", "movable_elements": []},
            "scene": {"location": "Scene", "setting_type": "outdoor"},
            "lighting": {"primary_source": "natural", "quality": "soft"},
            "style": {"medium": "photorealistic"},
            "shot_type": shot,
            "mood": "neutral",
            "motion_suggestions": {"camera_suggestions": ["dolly_in"], "recommended_speed": "slow"},
        }

    def _build_analysis(self, asset_id: UUID, ext: dict) -> VideoPromptAnalysis:
        """Build VideoPromptAnalysis from extraction."""
        subj = ext.get("subject", {})
        subject = SubjectInfo(
            description=subj.get("description", "Subject"),
            position_in_frame=subj.get("position_in_frame", "center"),
            movable_elements=subj.get("movable_elements", []),
        )

        sc = ext.get("scene", {})
        tod = None
        if sc.get("time_of_day"):
            with contextlib.suppress(Exception):
                tod = TimeOfDay(sc["time_of_day"])
        scene = SceneInfo(location=sc.get("location", "Scene"), setting_type=sc.get("setting_type", "outdoor"), time_of_day=tod)

        comp = ext.get("composition", {})
        composition = CompositionInfo(foreground=comp.get("foreground"), midground=comp.get("midground"), background=comp.get("background"))

        lt = ext.get("lighting", {})
        lighting = LightingInfo(primary_source=lt.get("primary_source", "natural"), quality=lt.get("quality", "soft"))

        st = ext.get("style", {})
        style = StyleInfo(medium=st.get("medium", "photorealistic"), color_palette=st.get("color_palette", []))

        mot = ext.get("motion_suggestions", {})
        cams = []
        for c in mot.get("camera_suggestions", []):
            with contextlib.suppress(Exception):
                cams.append(CameraMovement(c))
        try:
            spd = MovementSpeed(mot.get("recommended_speed", "slow"))
        except Exception:
            spd = MovementSpeed.SLOW
        motion = MotionSuggestions(
            subject_motions=mot.get("subject_motions", []),
            environmental_motions=mot.get("environmental_motions", []),
            camera_suggestions=cams,
            recommended_speed=spd,
        )

        try:
            shot_type = ShotType(ext.get("shot_type", "medium_shot"))
        except Exception:
            shot_type = ShotType.MEDIUM_SHOT
        try:
            mood = MoodTone(ext.get("mood", "neutral"))
        except Exception:
            mood = MoodTone.NEUTRAL

        return VideoPromptAnalysis(
            asset_id=asset_id, subject=subject, scene=scene, composition=composition,
            lighting=lighting, style=style, shot_type=shot_type, mood=mood, motion=motion,
        )

    def _suggest_camera(self, analysis: VideoPromptAnalysis) -> CameraMovement:
        if analysis.motion.camera_suggestions:
            return analysis.motion.camera_suggestions[0]
        return CameraMovement.DOLLY_IN

    def _compose_subject_prompt(self, analysis: VideoPromptAnalysis) -> str:
        parts = [analysis.subject.description]
        if analysis.scene.location != "Scene":
            parts.append(f"in {analysis.scene.location}")
        return " ".join(parts)

    def _compose_camera_prompt(self, camera: CameraMovement, speed: MovementSpeed) -> str:
        speed_map = {MovementSpeed.VERY_SLOW: "Very slow", MovementSpeed.SLOW: "Slow", MovementSpeed.MODERATE: "Steady", MovementSpeed.FAST: "Dynamic"}
        cam_map = {
            CameraMovement.DOLLY_IN: "camera pushes in toward subject",
            CameraMovement.DOLLY_OUT: "camera pulls back",
            CameraMovement.PAN_LEFT: "camera pans left",
            CameraMovement.PAN_RIGHT: "camera pans right",
            CameraMovement.ORBIT_LEFT: "camera orbits left around subject",
            CameraMovement.ORBIT_RIGHT: "camera orbits right around subject",
            CameraMovement.CRANE_UP: "camera rises upward",
            CameraMovement.STATIC: "camera holds steady",
        }
        return f"{speed_map.get(speed, 'Slow')} {cam_map.get(camera, 'camera moves')}"

    def _compose_environment_prompt(self, analysis: VideoPromptAnalysis) -> str:
        parts = analysis.motion.subject_motions[:2] + analysis.motion.environmental_motions[:2]
        if analysis.lighting.quality:
            parts.append(f"{analysis.lighting.quality} lighting")
        return ". ".join(parts) if parts else ""

    async def _download_to_temp(self, asset) -> Path:
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / f"{asset.id}{asset.file_extension}"
        async for chunk in self.container.storage.get(asset.storage_path):
            with open(temp_path, "ab") as f:
                f.write(chunk)
        return temp_path

    async def _save_analysis(self, asset_id: UUID, analysis: VideoPromptAnalysis) -> None:
        asset = await self.container.asset_service.get(asset_id)
        if asset:
            asset.extra_metadata["video_prompt_analysis"] = analysis.model_dump(mode="json")
            db = self.container.db
            if self.container.settings.database_backend == "mongodb":
                await db.assets.update_one({"_id": str(asset_id)}, {"$set": {"extra_metadata": asset.extra_metadata}})
            else:
                await db.update_asset_metadata(asset_id, asset.extra_metadata)

    async def _save_prompt(self, asset_id: UUID, prompt: GeneratedVideoPrompt) -> None:
        asset = await self.container.asset_service.get(asset_id)
        if asset:
            asset.extra_metadata["video_prompt_latest"] = prompt.model_dump(mode="json")
            db = self.container.db
            if self.container.settings.database_backend == "mongodb":
                await db.assets.update_one({"_id": str(asset_id)}, {"$set": {"extra_metadata": asset.extra_metadata}})
            else:
                await db.update_asset_metadata(asset_id, asset.extra_metadata)
