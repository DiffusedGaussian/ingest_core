"""
Example: Using the Flux Adapter for Construction Drawing → Photorealistic Render

This demonstrates how to use the FluxAdapter to transform technical
drawings into photorealistic 3D visualizations.
"""

# Example 1: Basic usage with a train bogie drawing
# -------------------------------------------------

example_prompt_data = {
    "subject": {
        "value": "high-speed train bogie suspension system"
    },
    "appearance": {
        "value": "steel frame, carbon-steel coil springs, hydraulic dampers with chrome pistons, cast iron wheels on gravel track"
    },
    "environment": {
        "value": "clean white background"
    },
    "lighting": {
        "value": "studio"
    },
    "camera": {
        "value": "isometric"
    },
    "style": {
        "value": "octane render style"
    },
    "technical": {
        "value": "all bolts and joints visible, high structural precision"
    }
}

# The adapter would compile this to something like:
EXPECTED_OUTPUT = """
A professional 3D CAD visualization transforming this technical line drawing into a photorealistic engineering render, high-speed train bogie suspension system, brushed industrial steel with subtle reflections frame, carbon-steel coil springs, hydraulic dampers with mirror-finish chrome plating pistons, cast iron with matte gray finish wheels on gravel track, isometric perspective, 30-degree angle, clean white background, professional three-point studio lighting with soft shadows, octane render style, all bolts and joints visible, high structural precision, 8k resolution, high detail, sharp focus, professional quality, photorealistic, preserving original geometry, accurate proportions, structural fidelity, precise details
"""


# Example 2: Different drawing types
# ----------------------------------

DRAWING_TYPE_EXAMPLES = {
    "architectural": {
        "subject": "modern office building floor plan",
        "appearance": "glass curtain walls, concrete structural elements, wood accents",
        "output_prefix": "A photorealistic architectural visualization transforming this blueprint into a detailed 3D render"
    },
    "mechanical": {
        "subject": "automotive engine assembly",
        "appearance": "aluminum engine block, steel crankshaft, rubber gaskets",
        "output_prefix": "A detailed mechanical engineering render transforming this CAD drawing into a photorealistic assembly visualization"
    },
    "schematic": {
        "subject": "industrial control system diagram",
        "appearance": "metal enclosures, cable conduits, electronic components",
        "output_prefix": "A 3D visualization transforming this schematic diagram into a realistic technical illustration"
    },
    "construction": {
        "subject": "steel beam connection detail",
        "appearance": "structural steel members, high-strength bolts, welded connections",
        "output_prefix": "A professional construction visualization transforming this structural drawing into a photorealistic 3D render"
    }
}


# Example 3: Using with the pipeline
# ----------------------------------

"""
# In your pipeline code:

from ingest_core.adapters import get_adapter
from ingest_core.models.prompt_schema import StructuredPrompt

# Get the Flux adapter
adapter = get_adapter("flux")

# Create structured prompt from VLM analysis
prompt = StructuredPrompt(
    subject=PromptComponent(value="train bogie suspension system"),
    appearance=PromptComponent(value="steel, springs, hydraulic dampers"),
    lighting=PromptComponent(value="studio"),
    camera=PromptComponent(value="isometric"),
)

# Compile to Flux-optimized string
flux_prompt = adapter.compile(prompt)

# Get with negative prompt
positive, negative = adapter.compile_with_negative(prompt)

# For specific drawing type
flux_prompt = adapter.compile_for_drawing_type(prompt, "mechanical")

# Get recommended img2img parameters
params = adapter.get_img2img_parameters()
# Returns: {"strength": 0.75, "guidance_scale": 7.5, "num_inference_steps": 50}
"""


# Example 4: Material expansion demonstration
# -------------------------------------------

MATERIAL_EXPANSION_EXAMPLES = [
    ("metal frame", "brushed industrial steel with subtle reflections frame"),
    ("chrome pistons", "mirror-finish chrome plating pistons"),
    ("rubber seals", "vulcanized rubber with matte black finish seals"),
    ("glass panel", "tempered glass with subtle reflections and refractions panel"),
    ("carbon fiber body", "woven carbon fiber with glossy clear coat body"),
]


# Example 5: Full API workflow
# ----------------------------

"""
# Using with Flux API (e.g., Replicate, fal.ai, etc.)

import httpx

async def generate_from_drawing(
    drawing_path: str,
    prompt: StructuredPrompt,
    api_key: str
):
    from ingest_core.adapters import get_adapter
    
    # Get adapter and compile prompt
    adapter = get_adapter("flux")
    positive_prompt, negative_prompt = adapter.compile_with_negative(prompt)
    params = adapter.get_img2img_parameters()
    
    # Read the drawing image
    with open(drawing_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    # Call Flux API (example using hypothetical endpoint)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.flux.example/v1/img2img",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "image": image_data,
                "prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "strength": params["strength"],
                "guidance_scale": params["guidance_scale"],
                "num_inference_steps": params["num_inference_steps"],
            }
        )
    
    return response.json()
"""


if __name__ == "__main__":
    print("Flux Adapter Examples")
    print("=" * 60)
    print()
    print("Example prompt structure:")
    print("-" * 40)
    import json
    print(json.dumps(example_prompt_data, indent=2))
    print()
    print("Expected output (trimmed):")
    print("-" * 40)
    print(EXPECTED_OUTPUT.strip()[:200] + "...")
    print()
    print("Drawing type prefixes:")
    print("-" * 40)
    for dtype, data in DRAWING_TYPE_EXAMPLES.items():
        print(f"  {dtype}: {data['output_prefix'][:60]}...")
    print()
    print("Material expansions:")
    print("-" * 40)
    for original, expanded in MATERIAL_EXPANSION_EXAMPLES:
        print(f"  '{original}' → '{expanded}'")
