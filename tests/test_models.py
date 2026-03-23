"""
Tests for data models.

Tests all Pydantic models including Asset, StructuredPrompt, and related models.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from ingest_core.models.asset import Asset, AssetStatus, AssetType
from ingest_core.models.prompt_schema import (
    CategoryName,
    PromptCategory,
    StructuredPrompt,
    create_default_category,
    create_empty_structured_prompt,
)


class TestAssetModel:
    """Tests for Asset model."""
    
    def test_create_asset(self):
        """Test creating a basic asset."""
        asset = Asset(
            asset_type=AssetType.IMAGE,
            original_filename="test.jpg",
            file_extension=".jpg",
            file_size_bytes=1024,
            mime_type="image/jpeg",
            storage_path="assets/test.jpg",
        )
        
        assert asset.id is not None
        assert asset.asset_type == AssetType.IMAGE
        assert asset.status == AssetStatus.PENDING
        assert asset.original_filename == "test.jpg"
        assert asset.created_at is not None
    
    def test_asset_status_transitions(self, sample_asset):
        """Test asset status state transitions."""
        assert sample_asset.status == AssetStatus.PENDING
        
        # Mark as processing
        sample_asset.mark_processing()
        assert sample_asset.status == AssetStatus.PROCESSING
        
        # Mark as completed
        sample_asset.mark_completed()
        assert sample_asset.status == AssetStatus.COMPLETED
        assert sample_asset.processed_at is not None
    
    def test_asset_failure(self, sample_asset):
        """Test marking asset as failed."""
        error_msg = "Processing failed due to corrupt file"
        sample_asset.mark_failed(error_msg)
        
        assert sample_asset.status == AssetStatus.FAILED
        assert sample_asset.error_message == error_msg
        assert sample_asset.updated_at is not None
    
    def test_asset_metadata(self, sample_asset):
        """Test extensible metadata."""
        sample_asset.extra_metadata["width"] = 1920
        sample_asset.extra_metadata["height"] = 1080
        sample_asset.extra_metadata["tags"] = ["portrait", "outdoor"]
        
        assert sample_asset.extra_metadata["width"] == 1920
        assert len(sample_asset.extra_metadata["tags"]) == 2
    
    def test_asset_types(self):
        """Test all asset types."""
        assert AssetType.IMAGE.value == "image"
        assert AssetType.VIDEO.value == "video"
        assert AssetType.ASSET_3D.value == "3d"


class TestPromptCategory:
    """Tests for PromptCategory model."""
    
    def test_create_category(self):
        """Test creating a prompt category."""
        cat = PromptCategory(
            name=CategoryName.SUBJECT,
            value="Young woman",
            source="manual"
        )
        
        assert cat.name == CategoryName.SUBJECT
        assert cat.value == "Young woman"
        assert cat.version == "1.0"
        assert cat.weight == 1.0
        assert cat.locked is False
    
    def test_category_with_weight(self):
        """Test category with custom weight."""
        cat = PromptCategory(
            name=CategoryName.LIGHTING,
            value="dramatic lighting",
            weight=1.5,
            source="vlm"
        )
        
        assert cat.weight == 1.5
        assert cat.source == "vlm"
    
    def test_locked_category(self):
        """Test locked category flag."""
        cat = PromptCategory(
            name=CategoryName.CAMERA,
            value="static",
            locked=True,
            source="manual"
        )
        
        assert cat.locked is True


class TestStructuredPrompt:
    """Tests for StructuredPrompt model."""
    
    def test_create_structured_prompt(self, sample_structured_prompt):
        """Test creating a structured prompt."""
        assert sample_structured_prompt.id is not None
        assert sample_structured_prompt.asset_id is not None
        assert sample_structured_prompt.subject.value == "Young woman with flowing brown hair"
        assert sample_structured_prompt.camera.value == "dolly_in"
    
    def test_get_category(self, sample_structured_prompt):
        """Test getting a category by name."""
        subject = sample_structured_prompt.get_category(CategoryName.SUBJECT)
        assert subject is not None
        assert subject.value == "Young woman with flowing brown hair"
        
        # Test with string name
        lighting = sample_structured_prompt.get_category("lighting")
        assert lighting is not None
        assert lighting.value == "golden_hour"
    
    def test_set_category(self, sample_structured_prompt):
        """Test modifying a category."""
        sample_structured_prompt.set_category(
            CategoryName.LIGHTING,
            "studio lighting",
            lock=True
        )
        
        lighting = sample_structured_prompt.get_category(CategoryName.LIGHTING)
        assert lighting.value == "studio lighting"
        assert lighting.locked is True
        assert lighting.source == "manual"
    
    def test_to_category_dict(self, sample_structured_prompt):
        """Test exporting categories to dictionary."""
        cat_dict = sample_structured_prompt.to_category_dict()
        
        assert "subject" in cat_dict
        assert "camera" in cat_dict
        assert "lighting" in cat_dict
        assert cat_dict["subject"] == "Young woman with flowing brown hair"
    
    def test_clone_with_override(self, sample_structured_prompt):
        """Test cloning prompt with category override."""
        original_lighting = sample_structured_prompt.lighting.value
        
        variant = sample_structured_prompt.clone_with_override(
            "lighting",
            "studio lighting"
        )
        
        # Original should be unchanged
        assert sample_structured_prompt.lighting.value == original_lighting
        
        # Variant should have new value
        assert variant.lighting.value == "studio lighting"
        assert variant.id != sample_structured_prompt.id
        assert variant.lighting.source == "manual"
    
    def test_empty_structured_prompt(self):
        """Test creating empty structured prompt."""
        asset_id = uuid4()
        prompt = create_empty_structured_prompt(asset_id)
        
        assert prompt.asset_id == asset_id
        assert prompt.subject.value == "Main subject"
        assert prompt.camera.value == "Static shot"
        assert prompt.created_from == "manual"
    
    def test_create_default_category(self):
        """Test category factory function."""
        cat = create_default_category(
            CategoryName.MOTION,
            "Slow movement",
            source="template"
        )
        
        assert cat.name == CategoryName.MOTION
        assert cat.value == "Slow movement"
        assert cat.source == "template"
    
    def test_prompt_with_optional_product(self):
        """Test structured prompt with optional product category."""
        asset_id = uuid4()
        
        prompt = StructuredPrompt(
            asset_id=asset_id,
            subject=create_default_category(CategoryName.SUBJECT, "Perfume bottle"),
            appearance=create_default_category(CategoryName.APPEARANCE, ""),
            environment=create_default_category(CategoryName.ENVIRONMENT, "Clean backdrop"),
            lighting=create_default_category(CategoryName.LIGHTING, "studio"),
            camera=create_default_category(CategoryName.CAMERA, "orbit_right"),
            motion=create_default_category(CategoryName.MOTION, "rotating slowly"),
            product=PromptCategory(
                name=CategoryName.PRODUCT,
                value="Luxury fragrance",
                source="manual"
            ),
            mood=create_default_category(CategoryName.MOOD, "elegant"),
            style=create_default_category(CategoryName.STYLE, "commercial"),
            technical=create_default_category(CategoryName.TECHNICAL, "4K"),
            created_from="manual"
        )
        
        assert prompt.product is not None
        assert prompt.product.value == "Luxury fragrance"


class TestCategoryName:
    """Tests for CategoryName enum."""
    
    def test_all_category_names(self):
        """Test all category name values."""
        expected_categories = {
            "SUBJECT", "APPEARANCE", "ENVIRONMENT", "LIGHTING",
            "CAMERA", "MOTION", "PRODUCT", "MOOD", "STYLE", "TECHNICAL"
        }
        
        actual_categories = {name.name for name in CategoryName}
        assert actual_categories == expected_categories
    
    def test_category_values(self):
        """Test category enum values."""
        assert CategoryName.SUBJECT.value == "subject"
        assert CategoryName.CAMERA.value == "camera"
        assert CategoryName.LIGHTING.value == "lighting"
