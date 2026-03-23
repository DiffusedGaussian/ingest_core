"""
Flux Adapter Settings - Add this to your config/settings.py

Insert this class after the MidjourneyAdapterSettings class,
then add 'flux: FluxAdapterSettings = Field(default_factory=FluxAdapterSettings)'
to the PromptAdapterSettings class.
"""

# =============================================================================
# Add this import at the top of settings.py (if not already present):
# =============================================================================
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Add this class after MidjourneyAdapterSettings:
# =============================================================================

class FluxAdapterSettings(BaseSettings):
    """
    Flux image-to-image adapter configuration.
    
    Optimized for transforming technical drawings (CAD, blueprints,
    schematics) into photorealistic 3D visualizations.
    """

    model_config = SettingsConfigDict(env_prefix="FLUX_")

    version: str = Field(default="1.1")
    max_prompt_length: int = Field(default=700)
    default_separator: str = Field(default=", ")
    
    # Category order optimized for img2img technical rendering
    category_order: list[str] = Field(
        default=["transformation", "subject", "materials", "perspective",
                 "environment", "lighting", "style", "technical"]
    )
    
    # Transformation prefixes for different drawing types
    transformation_prefixes: dict[str, str] = Field(default_factory=lambda: {
        "technical": "A professional 3D CAD visualization transforming this technical line drawing into a photorealistic engineering render",
        "architectural": "A photorealistic architectural visualization transforming this blueprint into a detailed 3D render",
        "mechanical": "A detailed mechanical engineering render transforming this CAD drawing into a photorealistic assembly visualization",
        "schematic": "A 3D visualization transforming this schematic diagram into a realistic technical illustration",
        "construction": "A professional construction visualization transforming this structural drawing into a photorealistic 3D render",
    })
    
    # Perspective vocabulary mapping
    perspective_vocabulary: dict[str, str] = Field(default_factory=lambda: {
        "isometric": "isometric perspective, 30-degree angle",
        "front": "front orthographic view, straight-on perspective",
        "side": "side profile view, perpendicular angle",
        "top": "top-down orthographic view, bird's eye perspective",
        "three_quarter": "three-quarter view, 45-degree angle",
        "exploded": "exploded view showing component separation",
        "cutaway": "cutaway section view revealing internal structure",
        "closeup": "detailed close-up view",
        "wide": "wide establishing shot showing full context",
    })
    
    # Default perspective for technical subjects
    default_perspective: str = Field(default="isometric perspective")
    
    # Material expansion vocabulary - generic to detailed
    material_vocabulary: dict[str, str] = Field(default_factory=lambda: {
        "metal": "brushed industrial steel with subtle reflections",
        "steel": "polished stainless steel with metallic sheen",
        "iron": "cast iron with matte gray finish",
        "aluminum": "anodized aluminum with satin finish",
        "copper": "polished copper with warm metallic tones",
        "brass": "brushed brass with golden highlights",
        "chrome": "mirror-finish chrome plating",
        "plastic": "injection-molded ABS plastic with slight texture",
        "rubber": "vulcanized rubber with matte black finish",
        "glass": "tempered glass with subtle reflections and refractions",
        "concrete": "poured concrete with aggregate texture",
        "wood": "finished hardwood with visible grain pattern",
        "carbon fiber": "woven carbon fiber with glossy clear coat",
        "titanium": "aerospace-grade titanium with brushed finish",
        "ceramic": "industrial ceramic with smooth matte surface",
    })
    
    # Lighting vocabulary mapping
    lighting_vocabulary: dict[str, str] = Field(default_factory=lambda: {
        "studio": "professional three-point studio lighting with soft shadows",
        "soft": "soft diffused lighting with minimal shadows",
        "dramatic": "dramatic rim lighting with strong shadows",
        "natural": "natural daylight from large windows",
        "industrial": "overhead industrial lighting with fluorescent tones",
        "hdri": "HDRI environment lighting with realistic reflections",
        "product": "product photography lighting with gradient background",
        "technical": "even technical illustration lighting, no harsh shadows",
        "ambient": "ambient occlusion lighting emphasizing depth and form",
    })
    
    # Default lighting for technical renders
    default_lighting: str = Field(
        default="professional studio lighting with soft shadows and ambient occlusion"
    )
    
    # Default environment
    default_environment: str = Field(
        default="clean white/light gray studio background with subtle gradient"
    )
    
    # Default render style
    default_render_style: str = Field(default="octane render, photorealistic")
    
    # Quality boosters
    quality_boosters: list[str] = Field(
        default=["8k resolution", "high detail", "sharp focus", 
                 "professional quality", "photorealistic"]
    )
    
    # Structure adherence keywords for img2img
    structure_keywords: list[str] = Field(
        default=["preserving original geometry", "accurate proportions",
                 "structural fidelity", "precise details"]
    )
    
    # Negative prompt for technical renders
    negative_prompt: str = Field(
        default="blurry, distorted, low quality, watermark, text overlay, "
                "logo, oversaturated, underexposed, grainy, compression artifacts, "
                "cartoon, anime, sketch, illustration style, flat shading, "
                "incorrect proportions, floating parts, disconnected elements, "
                "unrealistic materials, plastic look, toy-like, miniature"
    )
    
    # img2img specific parameters
    default_strength: float = Field(
        default=0.75,
        description="How much to transform (0=no change, 1=complete reimagining)"
    )
    default_guidance_scale: float = Field(
        default=7.5,
        description="How closely to follow the prompt"
    )
    default_steps: int = Field(
        default=50,
        description="Number of denoising steps"
    )


# =============================================================================
# Update PromptAdapterSettings to include Flux:
# =============================================================================

# Change the PromptAdapterSettings class to:
"""
class PromptAdapterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INGEST_")

    # Which adapter to use by default
    default_adapter: Literal["kling", "runway", "midjourney", "flux"] = Field(default="kling")
    
    # Per-model settings
    kling: KlingAdapterSettings = Field(default_factory=KlingAdapterSettings)
    runway: RunwayAdapterSettings = Field(default_factory=RunwayAdapterSettings)
    midjourney: MidjourneyAdapterSettings = Field(default_factory=MidjourneyAdapterSettings)
    flux: FluxAdapterSettings = Field(default_factory=FluxAdapterSettings)
"""
