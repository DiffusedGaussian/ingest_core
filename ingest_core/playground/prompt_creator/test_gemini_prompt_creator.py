"""
Technical Drawing to FLUX Prompt Pipeline - Using Google Gemini

This script uses Google Gemini (2.5 Flash or 3 Flash) for VLM analysis
of technical drawings, then generates optimized prompts for FLUX.

Supports BOTH SDKs:
    - NEW (recommended): pip install google-genai
    - LEGACY (deprecated): pip install google-generativeai pillow

Requirements:
    pip install pydantic
    pip install google-genai          # New unified SDK (recommended)
    # OR
    pip install google-generativeai pillow  # Legacy SDK (still works)

Usage:
    # Set your API key (works with both SDKs)
    export GEMINI_API_KEY="your-key-here"
    # OR
    export GOOGLE_API_KEY="your-key-here"
    
    # Run with example data
    python run_pipeline_gemini.py
    
    # Analyze a real technical drawing
    python run_pipeline_gemini.py --image path/to/drawing.png
    
    # Use specific Gemini model
    python run_pipeline_gemini.py --image drawing.png --model gemini-2.5-flash-preview
    
    # Generate all intent variants
    python run_pipeline_gemini.py --image drawing.png --all-intents

Available models:
    - gemini-2.5-flash-preview (default, good balance)
    - gemini-3-flash-preview (latest, most capable)
    - gemini-2.5-flash (stable)
"""

import argparse
import json
import os
from pathlib import Path

# Import the schema
from technical_drawing_prompt_schema import (
    TechnicalDrawingPromptV2,
    ExtractedObject,
    RenderConfig,
    RenderIntent,
    ScaleType,
    PreprocessingConfig,
    DrawingView,
)


def analyze_drawing_with_gemini(
    image_path: str,
    api_key: str | None = None,
    model: str = "gemini-2.5-flash-preview"
) -> dict | None:
    """
    Use Google Gemini to analyze a technical drawing and extract structured data.
    
    Supports both:
    - New SDK: google-genai (recommended, pip install google-genai)
    - Legacy SDK: google-generativeai (deprecated but still works)
    
    Args:
        image_path: Path to the technical drawing image
        api_key: Google API key (or set GEMINI_API_KEY / GOOGLE_API_KEY env var)
        model: Gemini model to use
    
    Returns:
        Dictionary with extracted information, or None on failure
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("Error: No API key provided.")
        print("Set GEMINI_API_KEY environment variable or use --api-key flag")
        return None
    
    # Check which SDK is available
    new_sdk_available = False
    old_sdk_available = False
    
    try:
        from google import genai
        from google.genai import types
        new_sdk_available = True
    except ImportError:
        pass
    
    try:
        import google.generativeai as genai_old
        old_sdk_available = True
    except ImportError:
        pass
    
    if not new_sdk_available and not old_sdk_available:
        print("Error: No Gemini SDK installed.")
        print("Install the new SDK: pip install google-genai")
        print("Or the legacy SDK: pip install google-generativeai")
        return None
    
    # Read image file
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        return None
    
    # Determine MIME type
    suffix = image_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".heic": "image/heic",
    }
    mime_type = mime_types.get(suffix, "image/png")
    
    # Analysis prompt
    analysis_prompt = """Analyze this technical/engineering drawing and extract information.

Return ONLY a valid JSON object (no markdown, no explanation) with these fields:

{
    "object_name": "simple name like 'railway bogie' or 'steam valve' - no adjectives",
    "object_type": "category like 'vehicle component', 'machinery', 'tool'",
    "primary_components": ["list", "of", "3-6", "main visible parts"],
    "materials_apparent": ["materials you can see or infer", "like cast iron", "steel", "brass"],
    "construction_style": "era and method like 'Victorian riveted' or 'modern welded'",
    "scale_info": "scale if shown on drawing, like '1:16' or '5-inch gauge', or null if not visible",
    "scale_type": "miniature_model" or "full_scale" or "unknown",
    "drawing_source": "manufacturer or designer name if visible, or null",
    "detected_views": [
        {
            "view_type": "one of: side_elevation, end_view, plan_view, cross_section, isometric, detail_view",
            "is_primary": true or false,
            "contains_dimensions": true or false,
            "contains_hatching": true or false,
            "description": "brief description of what this view shows"
        }
    ]
}

Be precise and factual. Only include what you can actually see in the drawing.
Return ONLY the JSON, nothing else."""

    print(f"Analyzing with {model}...")
    
    # Try new SDK first, fall back to legacy
    if new_sdk_available:
        print("Using new google-genai SDK")
        return _analyze_with_new_sdk(image_path, api_key, model, mime_type, analysis_prompt)
    else:
        print("Using legacy google-generativeai SDK (consider upgrading to google-genai)")
        return _analyze_with_legacy_sdk(image_path, api_key, model, mime_type, analysis_prompt)


def _analyze_with_new_sdk(image_path, api_key, model, mime_type, prompt) -> dict | None:
    """Use the new google-genai SDK."""
    try:
        from google import genai
        from google.genai import types
        
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        # Read image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Configure for JSON output
        config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        
        # Call API
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
            config=config
        )
        
        return _parse_response(response.text)
        
    except Exception as e:
        print(f"Error with new SDK: {e}")
        return None


def _analyze_with_legacy_sdk(image_path, api_key, model, mime_type, prompt) -> dict | None:
    """Use the legacy google-generativeai SDK."""
    try:
        import google.generativeai as genai
        from PIL import Image
        
        # Configure
        genai.configure(api_key=api_key)
        
        # Create model
        gen_model = genai.GenerativeModel(model)
        
        # Load image with PIL
        image = Image.open(image_path)
        
        # Generate content
        response = gen_model.generate_content([prompt, image])
        
        return _parse_response(response.text)
        
    except ImportError:
        print("Legacy SDK requires PIL: pip install Pillow")
        return None
    except Exception as e:
        print(f"Error with legacy SDK: {e}")
        return None


def _parse_response(response_text: str) -> dict | None:
    """Parse JSON from response, handling markdown fencing."""
    try:
        text = response_text.strip()
        
        # Handle markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            start_idx = 1 if lines[0].startswith("```") else 0
            end_idx = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            text = "\n".join(lines[start_idx:end_idx])
        
        return json.loads(text)
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Response was: {response_text[:500]}...")
        return None


def build_schema_from_analysis(analysis: dict) -> TechnicalDrawingPromptV2:
    """Convert Gemini analysis dict into the Pydantic schema."""
    
    # Build extracted object
    extracted = ExtractedObject(
        object_name=analysis["object_name"],
        object_type=analysis["object_type"],
        primary_components=analysis["primary_components"],
        materials_apparent=analysis["materials_apparent"],
        construction_style=analysis["construction_style"],
        scale_info=analysis.get("scale_info"),
        scale_type=ScaleType(analysis.get("scale_type", "unknown")),
        drawing_source=analysis.get("drawing_source"),
    )
    
    # Build preprocessing config from detected views
    detected_views = []
    for view_data in analysis.get("detected_views", []):
        detected_views.append(DrawingView(
            view_type=view_data["view_type"],
            is_primary=view_data.get("is_primary", False),
            contains_dimensions=view_data.get("contains_dimensions", True),
            contains_hatching=view_data.get("contains_hatching", False),
            description=view_data.get("description"),
        ))
    
    preprocessing = PreprocessingConfig(
        detected_views=detected_views,
        remove_dimensions=True,
        remove_annotations=True,
        use_multi_reference=len(detected_views) > 1,
    )
    
    # Build render config
    render = RenderConfig(
        intent=RenderIntent.PRODUCT_CATALOG,
        preprocessing=preprocessing,
    )
    
    return TechnicalDrawingPromptV2(extracted=extracted, render=render)


def generate_flux_payload(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """Generate payload for BFL FLUX API."""
    return {
        "prompt": prompt,
        "width": width,
        "height": height,
    }


# =============================================================================
# EXAMPLE DATA (used when no image/API provided)
# =============================================================================

EXAMPLE_ANALYSIS = {
    "object_name": "railway bogie",
    "object_type": "railway vehicle component",
    "primary_components": [
        "spoked wheels",
        "leaf spring suspension",
        "coil spring secondary suspension",
        "brake assembly",
        "side frames"
    ],
    "materials_apparent": ["cast iron", "steel", "brass fittings"],
    "construction_style": "Victorian-era riveted construction",
    "scale_info": "five-inch gauge",
    "scale_type": "miniature_model",
    "drawing_source": "D. Hewson Models",
    "detected_views": [
        {
            "view_type": "plan_view",
            "is_primary": False,
            "contains_dimensions": True,
            "contains_hatching": False,
            "description": "Top-down view showing frame layout"
        },
        {
            "view_type": "side_elevation",
            "is_primary": True,
            "contains_dimensions": True,
            "contains_hatching": False,
            "description": "Side profile showing suspension system"
        },
        {
            "view_type": "cross_section",
            "is_primary": False,
            "contains_dimensions": True,
            "contains_hatching": True,
            "description": "Bolster sections"
        },
        {
            "view_type": "end_view",
            "is_primary": False,
            "contains_dimensions": True,
            "contains_hatching": False,
            "description": "End-on view of wheels and brakes"
        }
    ]
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate FLUX prompts from technical drawings using Gemini VLM"
    )
    parser.add_argument(
        "--image", "-i",
        type=str,
        help="Path to technical drawing image"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="gemini-2.5-flash-preview",
        choices=[
            "gemini-2.5-flash-preview",
            "gemini-2.5-flash",
            "gemini-3-flash-preview",
            "gemini-3.1-pro-preview"
        ],
        help="Gemini model to use (default: gemini-2.5-flash-preview)"
    )
    parser.add_argument(
        "--intent",
        type=str,
        choices=[e.value for e in RenderIntent],
        default="product_catalog",
        help="Render intent (default: product_catalog)"
    )
    parser.add_argument(
        "--all-intents",
        action="store_true",
        help="Generate prompts for all intents"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Google API key (or set GOOGLE_API_KEY env var)"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        help="Save full schema to JSON file"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("TECHNICAL DRAWING → FLUX PROMPT (Gemini VLM)")
    print("=" * 70)
    print()
    
    # Step 1: Analyze the drawing
    analysis = None
    if args.image:
        print(f"Image: {args.image}")
        print(f"Model: {args.model}")
        analysis = analyze_drawing_with_gemini(
            args.image, 
            args.api_key,
            args.model
        )
    
    if analysis is None:
        if args.image:
            print("\nFailed to analyze image. Using example data.")
        else:
            print("No image provided. Using example data.")
            print("(Run with --image path/to/drawing.png to analyze a real drawing)")
        analysis = EXAMPLE_ANALYSIS
    
    print()
    print("-" * 70)
    print("EXTRACTED INFORMATION:")
    print("-" * 70)
    print(f"  Object: {analysis['object_name']}")
    print(f"  Type: {analysis['object_type']}")
    print(f"  Components: {', '.join(analysis['primary_components'][:3])}...")
    print(f"  Materials: {', '.join(analysis['materials_apparent'])}")
    print(f"  Scale: {analysis.get('scale_info', 'not specified')}")
    print(f"  Views detected: {len(analysis.get('detected_views', []))}")
    
    if analysis.get('detected_views'):
        print("\n  Detected views:")
        for v in analysis['detected_views']:
            primary = " [PRIMARY]" if v.get('is_primary') else ""
            print(f"    - {v['view_type']}{primary}: {v.get('description', '')}")
    
    print()
    
    # Step 2: Build schema
    schema = build_schema_from_analysis(analysis)
    
    # Step 3: Generate prompts
    if args.all_intents:
        print("=" * 70)
        print("GENERATED PROMPTS (all intents):")
        print("=" * 70)
        
        for intent in RenderIntent:
            schema.render.intent = intent
            prompt = schema.generate_prompt()
            word_count = len(prompt.split())
            
            print(f"\n--- {intent.value.upper()} ({word_count} words) ---")
            print(prompt)
    else:
        schema.render.intent = RenderIntent(args.intent)
        prompt = schema.generate_prompt()
        word_count = len(prompt.split())
        
        print("=" * 70)
        print(f"GENERATED PROMPT ({args.intent}, {word_count} words):")
        print("=" * 70)
        print()
        print(prompt)
    
    # Step 4: Show API usage
    print()
    print("=" * 70)
    print("FLUX API PAYLOAD:")
    print("=" * 70)
    print()
    payload = generate_flux_payload(schema.generate_prompt())
    print(json.dumps(payload, indent=2))
    
    # Step 5: Save to JSON if requested
    if args.output_json:
        output_data = {
            "analysis": analysis,
            "schema": schema.model_dump(),
            "prompts": {
                intent.value: schema.generate_prompt() 
                for intent in RenderIntent 
                for _ in [setattr(schema.render, 'intent', intent)]
            }
        }
        # Reset intent after generating all
        schema.render.intent = RenderIntent(args.intent)
        
        # Actually generate all prompts properly
        output_data["prompts"] = {}
        for intent in RenderIntent:
            schema.render.intent = intent
            output_data["prompts"][intent.value] = schema.generate_prompt()
        
        with open(args.output_json, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nSaved to: {args.output_json}")
    
    print()


if __name__ == "__main__":
    main()