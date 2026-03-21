from typing import Literal

from pydantic import BaseModel


class PromptCategory(BaseModel):
    """Single category with version tracking for ablation"""
    name: str
    version: str = "1.0"
    value: str
    weight: float = 1.0  # For future: importance in final prompt
    locked: bool = False  # If True, don't override from VLM

class StructuredPrompt(BaseModel):
    """The ablation-friendly prompt structure"""
    # Subject cluster
    subject: PromptCategory
    appearance: PromptCategory

    # Environment cluster
    environment: PromptCategory
    lighting: PromptCategory

    # Motion cluster
    camera: PromptCategory
    motion: PromptCategory

    # Context cluster
    product: PromptCategory | None = None
    mood: PromptCategory
    style: PromptCategory
    technical: PromptCategory

    # Metadata
    source_asset_id: str
    created_from: Literal["vlm", "manual", "template"]
