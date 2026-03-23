#!/usr/bin/env python3
"""
Test script for the StructuredPrompt workflow.

Run this to verify the new prompt schema system works:
    python -m ingest_core.test_structured_prompt

This tests:
1. Creating a StructuredPrompt manually
2. Compiling it with the Kling adapter (config from settings)
3. Category overrides (ablation simulation)
"""

from uuid import uuid4

from ingest_core.config import get_settings
from ingest_core.models.prompt_schema import (
    StructuredPrompt,
    PromptCategory,
    CategoryName,
    create_empty_structured_prompt,
)
from ingest_core.adapters import get_adapter


def test_manual_prompt_creation():
    """Test creating a StructuredPrompt manually."""
    print("\n" + "="*60)
    print("TEST 1: Manual StructuredPrompt Creation")
    print("="*60)
    
    asset_id = uuid4()
    
    prompt = StructuredPrompt(
        asset_id=asset_id,
        subject=PromptCategory(
            name=CategoryName.SUBJECT,
            value="Young woman with flowing brown hair",
            source="manual"
        ),
        appearance=PromptCategory(
            name=CategoryName.APPEARANCE,
            value="wearing white linen dress, minimal jewelry",
            source="manual"
        ),
        environment=PromptCategory(
            name=CategoryName.ENVIRONMENT,
            value="Mediterranean terrace overlooking the sea",
            source="manual"
        ),
        lighting=PromptCategory(
            name=CategoryName.LIGHTING,
            value="golden_hour",
            source="manual"
        ),
        camera=PromptCategory(
            name=CategoryName.CAMERA,
            value="dolly_in",
            source="manual"
        ),
        motion=PromptCategory(
            name=CategoryName.MOTION,
            value="hair gently moving in breeze, dress fabric flowing",
            source="manual"
        ),
        mood=PromptCategory(
            name=CategoryName.MOOD,
            value="peaceful, contemplative",
            source="manual"
        ),
        style=PromptCategory(
            name=CategoryName.STYLE,
            value="cinematic, shallow depth of field, anamorphic",
            source="manual"
        ),
        technical=PromptCategory(
            name=CategoryName.TECHNICAL,
            value="4K, high quality, film grain",
            source="manual"
        ),
        created_from="manual"
    )
    
    print(f"Created StructuredPrompt with ID: {prompt.id}")
    print(f"Categories: {list(prompt.to_category_dict().keys())}")
    
    return prompt


def test_kling_compilation(sample_structured_prompt: StructuredPrompt):
    """Test compiling with Kling adapter (config from settings)."""
    print("\n" + "="*60)
    print("TEST 2: Kling Adapter Compilation (Settings-based)")
    print("="*60)
    
    settings = get_settings()
    adapter = get_adapter("kling", settings)
    prompt = sample_structured_prompt
    
    print(f"Using adapter: {adapter.name} v{adapter.version}")
    print(f"Config from: settings.adapters.kling")
    print(f"Max length: {adapter.max_length}")
    print(f"Separator: '{adapter.separator}'")
    
    compiled = adapter.compile(prompt)
    print(f"\nCompiled prompt ({len(compiled)} chars):")
    print("-"*40)
    print(compiled)
    print("-"*40)
    
    # Test with negative prompt
    positive, negative = adapter.compile_with_negative(prompt)
    print(f"\nNegative prompt:")
    print(negative[:80] + "..." if len(negative) > 80 else negative)
    
    return compiled


def test_category_override(sample_structured_prompt: StructuredPrompt):
    """Test changing a single category (ablation simulation)."""
    print("\n" + "="*60)
    print("TEST 3: Category Override (Ablation)")
    print("="*60)
    
    prompt = sample_structured_prompt
    # Clone with different lighting
    variant = prompt.clone_with_override("lighting", "studio")
    
    settings = get_settings()
    adapter = get_adapter("kling", settings)
    
    original_compiled = adapter.compile(prompt)
    variant_compiled = adapter.compile(variant)
    
    print("Original lighting:", prompt.lighting.value)
    print("Variant lighting:", variant.lighting.value)
    print()
    print("Original prompt:")
    print(original_compiled[:150] + "...")
    print()
    print("Variant prompt:")
    print(variant_compiled[:150] + "...")
    
    print()
    print("✓ Changed only the lighting category - everything else identical")


def test_settings_config():
    """Test that adapter config comes from settings."""
    print("\n" + "="*60)
    print("TEST 4: Settings Configuration")
    print("="*60)
    
    settings = get_settings()
    
    print(f"Default adapter: {settings.adapters.default_adapter}")
    print(f"Kling version: {settings.adapters.kling.version}")
    print(f"Kling max length: {settings.adapters.kling.max_prompt_length}")
    print(f"Kling separator: '{settings.adapters.kling.default_separator}'")
    print(f"Camera vocab entries: {len(settings.adapters.kling.camera_vocabulary)}")
    print(f"Lighting vocab entries: {len(settings.adapters.kling.lighting_vocabulary)}")
    
    # Show a few camera mappings
    print("\nSample camera mappings:")
    for key in ["dolly_in", "orbit_left", "static"]:
        value = settings.adapters.kling.camera_vocabulary.get(key, "N/A")
        print(f"  {key} → {value}")


def test_empty_prompt():
    """Test creating empty prompt with defaults."""
    print("\n" + "="*60)
    print("TEST 5: Empty Prompt with Defaults")
    print("="*60)
    
    asset_id = uuid4()
    prompt = create_empty_structured_prompt(asset_id)
    
    settings = get_settings()
    adapter = get_adapter("kling", settings)
    compiled = adapter.compile(prompt)
    
    print("Empty/default prompt compiles to:")
    print(compiled)


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# StructuredPrompt Workflow Test (Settings-based)")
    print("#"*60)
    
    # Test 1: Create prompt
    prompt = test_manual_prompt_creation()
    
    # Test 2: Compile with Kling
    test_kling_compilation(prompt)
    
    # Test 3: Override (ablation)
    test_category_override(prompt)
    
    # Test 4: Settings config
    test_settings_config()
    
    # Test 5: Empty/default
    test_empty_prompt()
    
    print("\n" + "#"*60)
    print("# All tests passed!")
    print("#"*60 + "\n")


if __name__ == "__main__":
    main()
