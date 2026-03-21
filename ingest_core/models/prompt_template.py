"""Prompt template models for custom prompt generation."""
from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Custom prompt template."""

    id: str
    name: str
    description: str | None = None

    # Template string with placeholders
    # e.g., "{subject} in {location}. {camera}. {motion}. {style}"
    template: str

    # Default values for placeholders
    defaults: dict[str, str] = Field(default_factory=dict)

    # Required fields from analysis
    required_fields: list[str] = Field(default_factory=list)


# Predefined templates
TEMPLATES: dict[str, PromptTemplate] = {
    "default": PromptTemplate(
        id="default",
        name="Default",
        description="Basic prompt with subject, camera, and environment",
        template="{subject}. {camera}. {environment}",
        defaults={},
        required_fields=["subject", "camera"],
    ),
    "fashion_editorial": PromptTemplate(
        id="fashion_editorial",
        name="Fashion Editorial",
        description="High fashion editorial style with emphasis on clothing and styling",
        template="{subject}, {clothing}. {camera}. {motion}. Soft editorial lighting, high fashion aesthetic.",
        defaults={
            "camera": "Slow dolly in",
            "motion": "hair gently moving",
            "clothing": "wearing fashionable attire",
        },
        required_fields=["subject"],
    ),
    "product_hero": PromptTemplate(
        id="product_hero",
        name="Product Hero Shot",
        description="Clean product showcase with studio lighting",
        template="{subject} against {background}. {camera}. Smooth rotation, studio lighting.",
        defaults={
            "background": "clean white background",
            "camera": "Slow orbit right around subject",
        },
        required_fields=["subject"],
    ),
    "cinematic": PromptTemplate(
        id="cinematic",
        name="Cinematic",
        description="Film-like aesthetic with dramatic camera work",
        template="{subject} in {location}. {camera}. {motion}. Cinematic color grade, film grain, anamorphic lens.",
        defaults={
            "camera": "Slow push in",
            "motion": "atmospheric particles floating",
            "location": "dramatic setting",
        },
        required_fields=["subject"],
    ),
    "minimal": PromptTemplate(
        id="minimal",
        name="Minimal/Clean",
        description="Simple, clean aesthetic with minimal movement",
        template="{subject}. {camera}. {lighting}.",
        defaults={
            "camera": "Static shot",
            "lighting": "Soft even lighting",
        },
        required_fields=["subject"],
    ),
    "lifestyle": PromptTemplate(
        id="lifestyle",
        name="Lifestyle",
        description="Natural, lifestyle photography aesthetic",
        template="{subject} in {location}. {camera}. Natural {lighting}, lifestyle aesthetic, organic movement.",
        defaults={
            "camera": "Gentle handheld movement",
            "lighting": "natural lighting",
            "location": "casual setting",
        },
        required_fields=["subject"],
    ),
}
