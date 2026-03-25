"""
Technical Drawing to FLUX Prompt Schema v2

Designed for automated, general-purpose use across any technical drawing.
Key improvements over v1:
- User intent drives the output (not hard-coded museum aesthetic)
- Simpler structure following BFL's Subject + Action + Style + Context
- 30-80 word target (the sweet spot per BFL docs)
- Front-loads the object, not adjectives
- Separates "what we see" from "how to render it"
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Any
from enum import Enum


# =============================================================================
# USER INTENT - This drives everything
# =============================================================================

class RenderIntent(str, Enum):
    """What will this image be used for? This shapes the entire prompt."""
    
    PRODUCT_CATALOG = "product_catalog"          # Clean, neutral, sellable
    ENGINEERING_REVIEW = "engineering_review"    # Technical accuracy, all details visible
    MARKETING_HERO = "marketing_hero"            # Dramatic, impressive, aspirational
    DOCUMENTATION = "documentation"              # Clear, instructional, neutral background
    PROTOTYPE_SHOWCASE = "prototype_showcase"    # Workshop setting, work-in-progress feel
    ARTISTIC_RENDER = "artistic_render"          # Stylized, atmospheric, editorial
    IN_OPERATION = "in_operation"                # Shown working in its natural environment
    HISTORICAL_RECREATION = "historical_recreation"  # Period-accurate, archival feel


class ScaleType(str, Enum):
    """Is this a model/miniature or full-scale object?"""
    MINIATURE_MODEL = "miniature_model"      # Scale model, tabletop size
    FULL_SCALE = "full_scale"                # Real-world industrial/vehicle size
    UNKNOWN = "unknown"                       # Can't determine from drawing


# =============================================================================
# EXTRACTION FROM DRAWING (VLM populates this)
# =============================================================================

class ExtractedObject(BaseModel):
    """
    What the VLM sees in the technical drawing.
    Keep this PURELY descriptive - no interpretation of style or mood.
    """
    
    # Core identification
    object_name: str = Field(
        description="Simple name: 'railway bogie', 'steam valve', 'gear assembly'. No adjectives."
    )
    
    object_type: str = Field(
        description="Category: 'vehicle component', 'machinery', 'tool', 'architectural element'"
    )
    
    # Physical description (what we literally see)
    primary_components: list[str] = Field(
        description="Main visible parts: ['wheels', 'frame', 'springs', 'axles']. 3-6 items max."
    )
    
    materials_apparent: list[str] = Field(
        description="Materials visible/implied: ['cast iron', 'steel', 'brass']. Be specific."
    )
    
    construction_style: str = Field(
        description="Era/method: 'Victorian riveted construction', 'modern welded', 'precision machined'"
    )
    
    # Scale and context from drawing
    scale_info: str | None = Field(
        default=None,
        description="Scale if shown: '1:16', '5-inch gauge', 'full scale'. None if not visible."
    )
    
    scale_type: ScaleType = Field(
        description="Is this a miniature model or full-scale object?"
    )
    
    drawing_source: str | None = Field(
        default=None,
        description="Manufacturer/designer if visible on drawing"
    )


# =============================================================================
# RENDER CONFIGURATION (User or system specifies this)
# =============================================================================

class DrawingView(BaseModel):
    """Represents a single extracted view from a multi-view technical drawing."""
    
    view_type: Literal[
        "side_elevation",
        "end_view", 
        "plan_view",
        "cross_section",
        "isometric",
        "detail_view",
        "unknown"
    ] = Field(description="Type of orthographic projection")
    
    bounding_box: tuple[int, int, int, int] | None = Field(
        default=None,
        description="Pixel coordinates (x1, y1, x2, y2) for cropping this view"
    )
    
    is_primary: bool = Field(
        default=False,
        description="Is this the main/best view for understanding the object?"
    )
    
    contains_dimensions: bool = Field(
        default=True,
        description="Does this view have dimension lines that should be removed?"
    )
    
    contains_hatching: bool = Field(
        default=False,
        description="Does this view have cross-hatching (usually in sections)?"
    )
    
    description: str | None = Field(
        default=None,
        description="What this view shows: 'side profile showing suspension', 'axle cross-section'"
    )


class PreprocessingConfig(BaseModel):
    """
    Configuration for preprocessing the technical drawing before generation.
    Splitting and cleaning views significantly improves output quality.
    """
    
    # Detected views in the drawing
    detected_views: list[DrawingView] = Field(
        default_factory=list,
        description="Views detected/extracted from the technical drawing"
    )
    
    # Cleaning options
    remove_dimensions: bool = Field(
        default=True,
        description="Remove dimension lines and measurements"
    )
    
    remove_annotations: bool = Field(
        default=True, 
        description="Remove text annotations and labels"
    )
    
    remove_hatching: bool = Field(
        default=False,
        description="Remove cross-hatching from sections (usually keep for context)"
    )
    
    remove_title_block: bool = Field(
        default=True,
        description="Remove the title block / drawing border"
    )
    
    # Multi-reference strategy
    use_multi_reference: bool = Field(
        default=True,
        description="Use multiple views as Kontext references (recommended)"
    )
    
    primary_view: Literal[
        "side_elevation",
        "end_view",
        "plan_view", 
        "isometric",
        "auto"
    ] = Field(
        default="auto",
        description="Which view to use as primary reference. 'auto' selects best."
    )
    
    secondary_views: list[str] = Field(
        default_factory=lambda: ["end_view"],
        description="Additional views to include as references"
    )
    
    def get_reference_views(self) -> list[DrawingView]:
        """Get the views to use as Kontext references, in priority order."""
        if not self.detected_views:
            return []
        
        # Find primary
        primary = None
        if self.primary_view == "auto":
            # Prefer side elevation, then isometric, then end view
            priority = ["side_elevation", "isometric", "end_view", "plan_view"]
            for vtype in priority:
                for v in self.detected_views:
                    if v.view_type == vtype:
                        primary = v
                        break
                if primary:
                    break
        else:
            for v in self.detected_views:
                if v.view_type == self.primary_view:
                    primary = v
                    break
        
        result = [primary] if primary else []
        
        # Add secondaries
        for sec_type in self.secondary_views:
            for v in self.detected_views:
                if v.view_type == sec_type and v not in result:
                    result.append(v)
                    break
        
        return result[:3]  # Kontext works best with up to 3 references


class RenderConfig(BaseModel):
    """
    How should the object be rendered? 
    This is SEPARATE from what the object IS.
    """
    
    intent: RenderIntent = Field(
        description="Primary use case for this image"
    )
    
    # Preprocessing (new)
    preprocessing: PreprocessingConfig = Field(
        default_factory=PreprocessingConfig,
        description="How to preprocess the technical drawing"
    )
    
    # Environment (derived from intent, but can be overridden)
    environment: str | None = Field(
        default=None,
        description="Override environment. If None, derived from intent."
    )
    
    # Viewing angle
    camera_angle: Literal[
        "three-quarter front",
        "side profile", 
        "front view",
        "top-down",
        "low angle",
        "detail close-up"
    ] = Field(
        default="three-quarter front",
        description="Camera position relative to object"
    )
    
    # Additional emphasis
    highlight_components: list[str] | None = Field(
        default=None,
        description="Specific parts to emphasize (e.g., ['suspension system', 'brake mechanism'])"
    )
    
    # Surface condition
    surface_condition: Literal[
        "pristine",          # Factory fresh, clean
        "working",           # Light use, some oil/wear
        "weathered",         # Aged patina, rust, wear
        "restored"           # Cleaned up but showing age
    ] = Field(
        default="pristine",
        description="Surface appearance"
    )


# =============================================================================
# INTENT-BASED DEFAULTS
# =============================================================================

INTENT_DEFAULTS: dict[RenderIntent, dict] = {
    RenderIntent.PRODUCT_CATALOG: {
        "environment": "clean white studio background",
        "lighting": "soft even studio lighting",
        "style": "commercial product photography",
        "mood": None,  # No mood words - keep neutral
    },
    RenderIntent.ENGINEERING_REVIEW: {
        "environment": "neutral gray background",
        "lighting": "bright even lighting for detail visibility",
        "style": "technical documentation photography",
        "mood": None,
    },
    RenderIntent.MARKETING_HERO: {
        "environment": "dramatic dark background with rim lighting",
        "lighting": "dramatic three-point lighting with strong key light",
        "style": "cinematic product photography",
        "mood": "impressive, powerful",
    },
    RenderIntent.DOCUMENTATION: {
        "environment": "plain white background",
        "lighting": "flat even lighting",
        "style": "technical illustration",
        "mood": None,
    },
    RenderIntent.PROTOTYPE_SHOWCASE: {
        "environment": "engineering workshop with tools visible",
        "lighting": "natural workshop lighting",
        "style": "industrial photography",
        "mood": "authentic, work-in-progress",
    },
    RenderIntent.ARTISTIC_RENDER: {
        "environment": "atmospheric studio setting",
        "lighting": "dramatic directional lighting",
        "style": "fine art photography",
        "mood": "contemplative, elegant",
    },
    RenderIntent.IN_OPERATION: {
        "environment": "natural operational setting",  # Will be customized per object
        "lighting": "natural environmental lighting",
        "style": "documentary photography",
        "mood": "dynamic, functional",
    },
    RenderIntent.HISTORICAL_RECREATION: {
        "environment": "period-appropriate setting",
        "lighting": "warm natural lighting",
        "style": "archival photography style",
        "mood": "nostalgic, authentic",
    },
}


# =============================================================================
# MAIN SCHEMA
# =============================================================================

class TechnicalDrawingPromptV2(BaseModel):
    """
    Complete schema for VLM-based technical drawing to FLUX prompt generation.
    
    Two-phase approach:
    1. VLM extracts object information (what it IS)
    2. User/system specifies render intent (how to SHOW it)
    
    The prompt generator combines these following BFL's guidelines:
    - Subject + Action + Style + Context
    - Front-load the subject
    - 30-80 words for most cases
    """
    
    # What the VLM extracts
    extracted: ExtractedObject = Field(
        description="Object information extracted from the technical drawing"
    )
    
    # How to render it
    render: RenderConfig = Field(
        description="Rendering configuration based on intended use"
    )
    
    def _get_environment(self) -> str:
        """Get environment, using intent default if not overridden."""
        if self.render.environment:
            return self.render.environment
        
        defaults = INTENT_DEFAULTS[self.render.intent]
        env = defaults["environment"]
        
        # Special case: IN_OPERATION needs context-aware environment
        if self.render.intent == RenderIntent.IN_OPERATION:
            if "railway" in self.extracted.object_type.lower() or "railway" in self.extracted.object_name.lower():
                return "on railway tracks in an active rail yard"
            elif "vehicle" in self.extracted.object_type.lower():
                return "in an industrial facility"
            # Add more domain-specific environments as needed
        
        return env
    
    def _build_subject(self) -> str:
        """
        Build the subject description - FRONT-LOADED per BFL.
        Format: [Object name] with [key components], [materials]
        """
        # Start with the object name - no fluff
        parts = [self.extracted.object_name]
        
        # Add scale context if it's a model (this matters visually)
        if self.extracted.scale_type == ScaleType.MINIATURE_MODEL and self.extracted.scale_info:
            parts[0] = f"{self.extracted.scale_info} scale model of a {self.extracted.object_name}"
        
        # Add 2-3 key components
        if self.extracted.primary_components:
            components = self.extracted.primary_components[:3]
            parts.append(f"featuring {', '.join(components)}")
        
        # Add primary material
        if self.extracted.materials_apparent:
            parts.append(f"constructed from {self.extracted.materials_apparent[0]}")
        
        return ", ".join(parts)
    
    def _build_style_context(self) -> str:
        """Build style and context portion."""
        defaults = INTENT_DEFAULTS[self.render.intent]
        
        parts = []
        
        # Style
        parts.append(defaults["style"])
        
        # Lighting
        parts.append(defaults["lighting"])
        
        # Environment
        parts.append(self._get_environment())
        
        # Camera angle
        parts.append(self.render.camera_angle)
        
        # Surface condition (only if not pristine - that's the default assumption)
        if self.render.surface_condition != "pristine":
            condition_map = {
                "working": "with light oil patina and use marks",
                "weathered": "with aged patina and weathering",
                "restored": "carefully restored showing its age"
            }
            parts.append(condition_map[self.render.surface_condition])
        
        # Mood (only if intent has one)
        if defaults.get("mood"):
            parts.append(defaults["mood"])
        
        return ", ".join(parts)
    
    def generate_prompt(self) -> str:
        """
        Generate FLUX-optimized prompt.
        Target: 30-80 words, front-loaded subject.
        
        Structure: Subject, Style, Context
        (Action is implicit - object is displayed/shown)
        """
        subject = self._build_subject()
        style_context = self._build_style_context()
        
        # Combine: Subject first (most important), then style/context
        prompt = f"{subject}, {style_context}"
        
        # Add highlight emphasis if specified
        if self.render.highlight_components:
            highlights = ", ".join(self.render.highlight_components[:2])
            prompt += f", emphasis on {highlights}"
        
        return prompt
    
    def generate_prompt_variants(self) -> dict[str, str]:
        """Generate prompts for different intents for comparison."""
        original_intent = self.render.intent
        variants = {}
        
        for intent in RenderIntent:
            self.render.intent = intent
            variants[intent.value] = self.generate_prompt()
        
        self.render.intent = original_intent
        return variants


# =============================================================================
# EXAMPLE: Railway Bogie with Different Intents
# =============================================================================

def create_railway_bogie_example() -> TechnicalDrawingPromptV2:
    """
    Example: The same railway bogie drawing rendered for different purposes.
    """
    
    extracted = ExtractedObject(
        object_name="railway bogie",
        object_type="railway vehicle component",
        primary_components=[
            "spoked wheels",
            "leaf spring suspension",
            "coil spring secondary suspension",
            "brake assembly",
            "side frames"
        ],
        materials_apparent=[
            "cast iron",
            "steel",
            "brass fittings"
        ],
        construction_style="Victorian-era riveted construction",
        scale_info="five-inch gauge",
        scale_type=ScaleType.MINIATURE_MODEL,
        drawing_source="D. Hewson Models"
    )
    
    # Default to product catalog - clean, neutral
    render = RenderConfig(
        intent=RenderIntent.PRODUCT_CATALOG,
        camera_angle="three-quarter front",
        surface_condition="pristine"
    )
    
    return TechnicalDrawingPromptV2(extracted=extracted, render=render)


def create_railway_bogie_with_preprocessing() -> TechnicalDrawingPromptV2:
    """
    Example showing how to use preprocessing with multi-view references.
    This is the RECOMMENDED approach for complex technical drawings.
    """
    
    extracted = ExtractedObject(
        object_name="railway bogie",
        object_type="railway vehicle component",
        primary_components=[
            "spoked wheels",
            "leaf spring suspension", 
            "coil spring secondary suspension",
            "brake assembly",
            "side frames"
        ],
        materials_apparent=[
            "cast iron",
            "steel",
            "brass fittings"
        ],
        construction_style="Victorian-era riveted construction",
        scale_info="five-inch gauge",
        scale_type=ScaleType.MINIATURE_MODEL,
        drawing_source="D. Hewson Models"
    )
    
    # Define the detected views from the technical drawing
    preprocessing = PreprocessingConfig(
        detected_views=[
            DrawingView(
                view_type="plan_view",
                bounding_box=(50, 20, 400, 180),  # Example coordinates
                is_primary=False,
                contains_dimensions=True,
                contains_hatching=False,
                description="Top-down view showing frame layout and wheel spacing"
            ),
            DrawingView(
                view_type="side_elevation",
                bounding_box=(50, 200, 400, 420),
                is_primary=True,  # Best view for overall shape
                contains_dimensions=True,
                contains_hatching=False,
                description="Side profile showing full suspension system and wheels"
            ),
            DrawingView(
                view_type="cross_section",
                bounding_box=(450, 20, 700, 180),
                is_primary=False,
                contains_dimensions=True,
                contains_hatching=True,  # Sections have hatching
                description="Bolster and cross member sections showing internal structure"
            ),
            DrawingView(
                view_type="end_view",
                bounding_box=(450, 200, 700, 420),
                is_primary=False,
                contains_dimensions=True,
                contains_hatching=False,
                description="End-on view showing wheel profile and brake geometry"
            ),
        ],
        remove_dimensions=True,
        remove_annotations=True,
        remove_hatching=False,  # Keep hatching for structure understanding
        remove_title_block=True,
        use_multi_reference=True,
        primary_view="side_elevation",
        secondary_views=["end_view", "plan_view"]
    )
    
    render = RenderConfig(
        intent=RenderIntent.PRODUCT_CATALOG,
        preprocessing=preprocessing,
        camera_angle="three-quarter front",
        surface_condition="pristine"
    )
    
    return TechnicalDrawingPromptV2(extracted=extracted, render=render)


if __name__ == "__main__":
    example = create_railway_bogie_example()
    
    print("=" * 80)
    print("TECHNICAL DRAWING TO FLUX PROMPT - V2")
    print("=" * 80)
    print()
    print(f"Object: {example.extracted.object_name}")
    print(f"Type: {example.extracted.object_type}")
    print(f"Scale: {example.extracted.scale_info} ({example.extracted.scale_type.value})")
    print()
    
    print("=" * 80)
    print("PROMPTS BY INTENT:")
    print("=" * 80)
    
    variants = example.generate_prompt_variants()
    
    for intent, prompt in variants.items():
        word_count = len(prompt.split())
        print(f"\n--- {intent.upper()} ({word_count} words) ---")
        print(prompt)
    
    # Show preprocessing example
    print()
    print("=" * 80)
    print("PREPROCESSING WORKFLOW EXAMPLE")
    print("=" * 80)
    
    example_with_preprocessing = create_railway_bogie_with_preprocessing()
    preprocessing = example_with_preprocessing.render.preprocessing
    
    print(f"\nDetected {len(preprocessing.detected_views)} views in drawing:")
    for i, view in enumerate(preprocessing.detected_views, 1):
        primary_marker = " [PRIMARY]" if view.is_primary else ""
        print(f"  {i}. {view.view_type}{primary_marker}")
        print(f"     Bounding box: {view.bounding_box}")
        print(f"     Description: {view.description}")
    
    print(f"\nPreprocessing settings:")
    print(f"  Remove dimensions: {preprocessing.remove_dimensions}")
    print(f"  Remove annotations: {preprocessing.remove_annotations}")
    print(f"  Remove hatching: {preprocessing.remove_hatching}")
    print(f"  Use multi-reference: {preprocessing.use_multi_reference}")
    
    ref_views = preprocessing.get_reference_views()
    print(f"\nReference views for Kontext (in order):")
    for i, view in enumerate(ref_views, 1):
        print(f"  {i}. {view.view_type}: {view.description}")
    
    print()
    print("=" * 80)
    print("MULTI-REFERENCE KONTEXT PROMPT")
    print("=" * 80)
    print()
    print("For Kontext with multiple reference images, use:")
    print()
    print("Reference images:")
    print("  1. [Cleaned side elevation crop]")
    print("  2. [Cleaned end view crop]")
    print("  3. [Cleaned plan view crop]")
    print()
    print("Prompt:")
    example_with_preprocessing.render.intent = RenderIntent.PRODUCT_CATALOG
    base_prompt = example_with_preprocessing.generate_prompt()
    kontext_prompt = f"Using the side profile for shape, end view for depth, and plan for layout: {base_prompt}"
    print(f'  "{kontext_prompt}"')