"""
Tests for model adapters.

Tests the adapter system for compiling StructuredPrompt to model-specific formats.
"""

import pytest

from ingest_core.adapters.base import BaseModelAdapter
from ingest_core.adapters.kling import KlingAdapter
from ingest_core.config.settings import Settings


class TestKlingAdapter:
    """Tests for Kling adapter."""
    
    def test_adapter_initialization(self, test_settings):
        """Test adapter initialization with settings."""
        adapter = KlingAdapter(test_settings)
        
        assert adapter.name == "kling"
        assert adapter.version == "1.5"
        assert adapter.max_length == 500
        assert adapter.separator == ". "
    
    def test_compile_full_prompt(self, test_settings, sample_structured_prompt):
        """Test compiling a complete prompt."""
        adapter = KlingAdapter(test_settings)
        compiled = adapter.compile(sample_structured_prompt)
        
        # Check that prompt contains expected elements
        assert "Young woman" in compiled
        assert "Mediterranean terrace" in compiled
        assert "camera" in compiled.lower() or "pushes" in compiled.lower()
        assert len(compiled) > 0
    
    def test_compile_with_negative(self, test_settings, sample_structured_prompt):
        """Test compiling with negative prompt."""
        adapter = KlingAdapter(test_settings)
        positive, negative = adapter.compile_with_negative(sample_structured_prompt)
        
        assert len(positive) > 0
        assert len(negative) > 0
        assert "blurry" in negative.lower()
    
    def test_camera_vocabulary_mapping(self, test_settings):
        """Test camera movement vocabulary mapping."""
        adapter = KlingAdapter(test_settings)
        
        # Test known camera movements
        assert "pushes" in adapter.get_camera_term("dolly_in")
        assert "orbit" in adapter.get_camera_term("orbit_left")
        assert "static" in adapter.get_camera_term("static")
    
    def test_lighting_vocabulary_mapping(self, test_settings):
        """Test lighting vocabulary mapping."""
        adapter = KlingAdapter(test_settings)
        
        # Test known lighting terms
        assert "golden" in adapter.get_lighting_term("golden_hour")
        assert "studio" in adapter.get_lighting_term("studio")
    
    def test_category_order(self, test_settings):
        """Test that adapter respects category order."""
        adapter = KlingAdapter(test_settings)
        
        expected_order = [
            "subject", "appearance", "environment", "lighting",
            "camera", "motion", "mood", "style", "technical"
        ]
        
        assert adapter.category_order == expected_order
    
    def test_validate_prompt(self, test_settings, sample_structured_prompt):
        """Test prompt validation."""
        adapter = KlingAdapter(test_settings)
        warnings = adapter.validate_prompt(sample_structured_prompt)
        
        # Should have no warnings for reasonable prompt
        assert isinstance(warnings, list)
    
    def test_validate_long_prompt(self, test_settings):
        """Test validation with overly long prompt."""
        adapter = KlingAdapter(test_settings)
        
        from ingest_core.models.prompt_schema import PromptCategory, CategoryName, StructuredPrompt
        from uuid import uuid4
        
        # Create prompt with very long values
        long_prompt = StructuredPrompt(
            asset_id=uuid4(),
            subject=PromptCategory(
                name=CategoryName.SUBJECT,
                value="A" * 200,
                source="manual"
            ),
            appearance=PromptCategory(
                name=CategoryName.APPEARANCE,
                value="B" * 200,
                source="manual"
            ),
            environment=PromptCategory(
                name=CategoryName.ENVIRONMENT,
                value="C" * 200,
                source="manual"
            ),
            lighting=PromptCategory(
                name=CategoryName.LIGHTING,
                value="studio",
                source="manual"
            ),
            camera=PromptCategory(
                name=CategoryName.CAMERA,
                value="static",
                source="manual"
            ),
            motion=PromptCategory(
                name=CategoryName.MOTION,
                value="none",
                source="manual"
            ),
            mood=PromptCategory(
                name=CategoryName.MOOD,
                value="neutral",
                source="manual"
            ),
            style=PromptCategory(
                name=CategoryName.STYLE,
                value="realistic",
                source="manual"
            ),
            technical=PromptCategory(
                name=CategoryName.TECHNICAL,
                value="4K",
                source="manual"
            ),
            created_from="manual"
        )
        
        warnings = adapter.validate_prompt(long_prompt)
        assert len(warnings) > 0
        assert "exceeds max length" in warnings[0].lower()
    
    def test_empty_prompt_compilation(self, test_settings, empty_structured_prompt):
        """Test compiling an empty/default prompt."""
        adapter = KlingAdapter(test_settings)
        compiled = adapter.compile(empty_structured_prompt)
        
        # Should produce some output even with defaults
        assert len(compiled) > 0


class TestBaseAdapter:
    """Tests for base adapter interface."""
    
    def test_base_adapter_interface(self, test_settings):
        """Test that base adapter defines correct interface."""
        from abc import ABC
        
        assert issubclass(BaseModelAdapter, ABC)
        
        # Check required methods exist
        assert hasattr(BaseModelAdapter, 'compile')
        assert hasattr(BaseModelAdapter, '_get_adapter_config')
    
    def test_adapter_properties(self, test_settings):
        """Test adapter property accessors."""
        adapter = KlingAdapter(test_settings)
        
        # Test all property accessors
        assert isinstance(adapter.version, str)
        assert isinstance(adapter.category_order, list)
        assert isinstance(adapter.separator, str)
        assert isinstance(adapter.max_length, int)
        assert adapter.max_length > 0
    
    def test_get_negative_prompt(self, test_settings):
        """Test getting default negative prompt."""
        adapter = KlingAdapter(test_settings)
        negative = adapter.get_negative_prompt()
        
        assert isinstance(negative, str)
        assert len(negative) > 0
