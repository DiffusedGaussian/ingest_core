"""
Video prompt generation models.

Structured schemas for extracting image data and generating
optimized prompts for video generation (Flux, Runway, etc.)
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ShotType(str, Enum):
    """Standard cinematographic shot types."""

    EXTREME_CLOSE_UP = "extreme_close_up"
    CLOSE_UP = "close_up"
    MEDIUM_CLOSE_UP = "medium_close_up"
    MEDIUM_SHOT = "medium_shot"
    MEDIUM_WIDE = "medium_wide"
    WIDE_SHOT = "wide_shot"
    EXTREME_WIDE = "extreme_wide"
    ESTABLISHING = "establishing"


class CameraMovement(str, Enum):
    """Camera movement types for video generation."""

    STATIC = "static"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    TRACK_LEFT = "track_left"
    TRACK_RIGHT = "track_right"
    CRANE_UP = "crane_up"
    CRANE_DOWN = "crane_down"
    ORBIT_LEFT = "orbit_left"
    ORBIT_RIGHT = "orbit_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PUSH_IN = "push_in"
    PULL_OUT = "pull_out"
    HANDHELD = "handheld"
    FPV_DRONE = "fpv_drone"


class MovementSpeed(str, Enum):
    """Speed/pacing of movement."""

    VERY_SLOW = "very_slow"
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"
    VERY_FAST = "very_fast"


class TimeOfDay(str, Enum):
    """Time of day for lighting context."""

    DAWN = "dawn"
    GOLDEN_HOUR_MORNING = "golden_hour_morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    GOLDEN_HOUR_EVENING = "golden_hour_evening"
    SUNSET = "sunset"
    DUSK = "dusk"
    BLUE_HOUR = "blue_hour"
    NIGHT = "night"
    ARTIFICIAL = "artificial"
    MIXED = "mixed"


class MoodTone(str, Enum):
    """Emotional tone/mood of the scene."""

    PEACEFUL = "peaceful"
    CONTEMPLATIVE = "contemplative"
    MELANCHOLIC = "melancholic"
    DRAMATIC = "dramatic"
    TENSE = "tense"
    JOYFUL = "joyful"
    ENERGETIC = "energetic"
    ROMANTIC = "romantic"
    MYSTERIOUS = "mysterious"
    EPIC = "epic"
    INTIMATE = "intimate"
    NEUTRAL = "neutral"


class SubjectInfo(BaseModel):
    """Information about the main subject."""

    description: str = Field(default="Main subject")
    position_in_frame: str = Field(default="center")
    pose_or_state: str | None = None
    clothing_or_appearance: str | None = None
    movable_elements: list[str] = Field(default_factory=list)


class SceneInfo(BaseModel):
    """Information about the scene/environment."""

    location: str = Field(default="Scene")
    setting_type: str = Field(default="outdoor")
    time_of_day: TimeOfDay | None = None
    weather: str | None = None
    season: str | None = None


class CompositionInfo(BaseModel):
    """Scene composition layers."""

    foreground: str | None = None
    midground: str | None = None
    background: str | None = None
    depth_cues: list[str] = Field(default_factory=list)


class LightingInfo(BaseModel):
    """Lighting analysis."""

    primary_source: str = Field(default="natural")
    direction: str = Field(default="front")
    quality: str = Field(default="soft")
    color_temperature: str = Field(default="neutral")
    special_effects: list[str] = Field(default_factory=list)


class StyleInfo(BaseModel):
    """Visual style analysis."""

    medium: str = Field(default="photorealistic")
    aesthetic: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    lens_characteristics: str | None = None
    film_reference: str | None = None


class MotionSuggestions(BaseModel):
    """Suggested motions for video generation."""

    subject_motions: list[str] = Field(default_factory=list)
    environmental_motions: list[str] = Field(default_factory=list)
    camera_suggestions: list[CameraMovement] = Field(default_factory=list)
    recommended_speed: MovementSpeed = Field(default=MovementSpeed.SLOW)


class VideoPromptAnalysis(BaseModel):
    """Complete structured analysis of an image for video generation."""

    id: UUID = Field(default_factory=uuid4)
    asset_id: UUID

    subject: SubjectInfo = Field(default_factory=SubjectInfo)
    scene: SceneInfo = Field(default_factory=SceneInfo)
    composition: CompositionInfo = Field(default_factory=CompositionInfo)
    lighting: LightingInfo = Field(default_factory=LightingInfo)
    style: StyleInfo = Field(default_factory=StyleInfo)

    shot_type: ShotType = Field(default=ShotType.MEDIUM_SHOT)
    aspect_ratio: str = Field(default="16:9")

    mood: MoodTone = Field(default=MoodTone.NEUTRAL)
    mood_descriptors: list[str] = Field(default_factory=list)

    motion: MotionSuggestions = Field(default_factory=MotionSuggestions)

    raw_description: str | None = None
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analyzer_model: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)

    class Config:
        from_attributes = True


class GeneratedVideoPrompt(BaseModel):
    """Generated video prompt ready for use with Flux/Runway/etc."""

    id: UUID = Field(default_factory=uuid4)
    asset_id: UUID
    analysis_id: UUID | None = None

    prompt: str
    prompt_components: dict[str, str] = Field(default_factory=dict)
    negative_prompt: str | None = None

    recommended_duration: int = Field(default=5)
    recommended_camera: CameraMovement | None = None
    recommended_speed: MovementSpeed = Field(default=MovementSpeed.SLOW)

    target_generator: str = Field(default="flux")
    variations: list[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
