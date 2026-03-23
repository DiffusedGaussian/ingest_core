"""
Structured Prompt Schema.

Defines a modular, category-based prompt structure that enables:
- Ablation testing (change one category, observe effect)
- Model-agnostic representation (compile to any generator)
- Version tracking per category
- Human overrides with locked fields

The StructuredPrompt maps from VideoPromptAnalysis (VLM extraction)
and compiles down to model-specific prompt strings.
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CategoryName(str, Enum):
    """All available prompt categories."""
    
    SUBJECT = "subject"
    APPEARANCE = "appearance"
    ENVIRONMENT = "environment"
    LIGHTING = "lighting"
    CAMERA = "camera"
    MOTION = "motion"
    PRODUCT = "product"
    MOOD = "mood"
    STYLE = "style"
    TECHNICAL = "technical"


class PromptCategory(BaseModel):
    """
    A single prompt category with version tracking.
    
    Each category is independently modifiable for ablation testing.
    When locked=True, the value won't be overwritten by VLM extraction.
    """
    
    name: CategoryName
    value: str
    version: str = "1.0"
    weight: float = Field(default=1.0, ge=0.0, le=2.0)  # Importance multiplier
    locked: bool = False  # If True, preserve during re-analysis
    source: Literal["vlm", "manual", "template", "default"] = "vlm"
    
    class Config:
        use_enum_values = True


class StructuredPrompt(BaseModel):
    """
    The ablation-friendly structured prompt.
    
    Each category can be independently modified and versioned.
    The same StructuredPrompt can compile to different model-specific
    prompt strings via adapters (Kling, Runway, Midjourney, etc.)
    """
    
    id: UUID = Field(default_factory=uuid4)
    asset_id: UUID
    
    # Subject cluster - WHO/WHAT is in frame
    subject: PromptCategory
    appearance: PromptCategory  # Clothing, styling, physical details
    
    # Environment cluster - WHERE
    environment: PromptCategory
    lighting: PromptCategory
    
    # Motion cluster - HOW it moves
    camera: PromptCategory
    motion: PromptCategory  # Subject and environmental motion
    
    # Context cluster - FEEL and STYLE
    product: PromptCategory | None = None  # Optional: for product shots
    mood: PromptCategory
    style: PromptCategory
    technical: PromptCategory  # Resolution, aspect ratio, quality terms
    
    # Metadata
    source_analysis_id: UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_from: Literal["vlm", "manual", "template"] = "vlm"
    
    # Compilation cache (populated after compile)
    _compiled_prompts: dict[str, str] = {}  # model_name -> prompt_string
    
    class Config:
        from_attributes = True
    
    def get_category(self, name: CategoryName | str) -> PromptCategory | None:
        """Get a category by name."""
        name_str = name.value if isinstance(name, CategoryName) else name
        return getattr(self, name_str, None)
    
    def set_category(self, name: CategoryName | str, value: str, lock: bool = False) -> None:
        """Update a category value (for ablation experiments)."""
        name_str = name.value if isinstance(name, CategoryName) else name
        cat = getattr(self, name_str, None)
        if cat and isinstance(cat, PromptCategory):
            cat.value = value
            cat.source = "manual"
            if lock:
                cat.locked = True
    
    def to_category_dict(self) -> dict[str, str]:
        """Export all categories as a simple dict for templating."""
        result = {}
        for name in CategoryName:
            cat = self.get_category(name)
            if cat:
                result[name.value] = cat.value
        return result
    
    def clone_with_override(self, category: str, new_value: str) -> "StructuredPrompt":
        """Create a copy with one category changed (for A/B testing)."""
        data = self.model_dump()
        data["id"] = uuid4()
        data["created_at"] = datetime.utcnow()
        if category in data and data[category]:
            data[category]["value"] = new_value
            data[category]["source"] = "manual"
        return StructuredPrompt.model_validate(data)


# =============================================================================
# Factory functions to create StructuredPrompt from various sources
# =============================================================================

def create_default_category(
    name: CategoryName, 
    value: str = "",
    source: str = "default"
) -> PromptCategory:
    """Create a category with default settings."""
    return PromptCategory(
        name=name,
        value=value,
        source=source,
    )


def create_empty_structured_prompt(asset_id: UUID) -> StructuredPrompt:
    """Create an empty StructuredPrompt with all categories initialized."""
    return StructuredPrompt(
        asset_id=asset_id,
        subject=create_default_category(CategoryName.SUBJECT, "Main subject"),
        appearance=create_default_category(CategoryName.APPEARANCE, ""),
        environment=create_default_category(CategoryName.ENVIRONMENT, "Scene"),
        lighting=create_default_category(CategoryName.LIGHTING, "Natural lighting"),
        camera=create_default_category(CategoryName.CAMERA, "Static shot"),
        motion=create_default_category(CategoryName.MOTION, "Subtle movement"),
        mood=create_default_category(CategoryName.MOOD, "Neutral"),
        style=create_default_category(CategoryName.STYLE, "Photorealistic"),
        technical=create_default_category(CategoryName.TECHNICAL, "High quality, 4K"),
        created_from="manual",
    )
