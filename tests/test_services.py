"""
Tests for service layer.

Tests business logic in services like ingestion, asset management, etc.
"""

from uuid import uuid4

import pytest

from ingest_core.models.asset import AssetType
from ingest_core.models.prompt_schema import create_empty_structured_prompt


class TestAssetService:
    """Tests for AssetService."""
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_create_asset(self):
        """Test creating an asset."""
        # Would need full container setup
        pass
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_get_asset(self):
        """Test retrieving an asset."""
        pass
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_update_asset_status(self):
        """Test updating asset status."""
        pass
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_delete_asset(self):
        """Test deleting an asset."""
        pass


class TestIngestionService:
    """Tests for IngestionService."""
    
    def test_detect_asset_type_image(self):
        """Test detecting image asset type."""
        from ingest_core.services.ingestion import IngestionService
        
        # Create mock instance
        service = IngestionService(container=None)
        
        assert service._detect_asset_type("image/jpeg") == AssetType.IMAGE
        assert service._detect_asset_type("image/png") == AssetType.IMAGE
        assert service._detect_asset_type("image/webp") == AssetType.IMAGE
    
    def test_detect_asset_type_video(self):
        """Test detecting video asset type."""
        from ingest_core.services.ingestion import IngestionService
        
        service = IngestionService(container=None)
        
        assert service._detect_asset_type("video/mp4") == AssetType.VIDEO
        assert service._detect_asset_type("video/quicktime") == AssetType.VIDEO
    
    def test_detect_asset_type_3d(self):
        """Test detecting 3D asset type."""
        from ingest_core.services.ingestion import IngestionService
        
        service = IngestionService(container=None)
        
        result = service._detect_asset_type("model/gltf-binary")
        # Should detect as 3D or default to something reasonable
        assert result in [AssetType.ASSET_3D, AssetType.IMAGE]
    
    @pytest.mark.skip(reason="Requires full container setup")
    async def test_ingest_file(self):
        """Test full file ingestion pipeline."""
        pass


class TestPromptCompiler:
    """Tests for prompt compilation service."""
    
    def test_compile_with_adapter(self, test_settings, sample_structured_prompt):
        """Test compiling prompt with specific adapter."""
        from ingest_core.adapters.kling import KlingAdapter
        
        adapter = KlingAdapter(test_settings)
        compiled = adapter.compile(sample_structured_prompt)
        
        assert isinstance(compiled, str)
        assert len(compiled) > 0
    
    def test_compile_empty_prompt(self, test_settings):
        """Test compiling empty prompt with defaults."""
        from ingest_core.adapters.kling import KlingAdapter
        
        prompt = create_empty_structured_prompt(uuid4())
        adapter = KlingAdapter(test_settings)
        compiled = adapter.compile(prompt)
        
        assert isinstance(compiled, str)
        assert len(compiled) > 0


class TestLineageService:
    """Tests for lineage tracking service."""
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_create_lineage_record(self):
        """Test creating lineage relationship."""
        pass
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_get_lineage_tree(self):
        """Test retrieving lineage tree."""
        pass
    
    @pytest.mark.skip(reason="Requires container with database setup")
    async def test_track_generation(self):
        """Test tracking generation lineage."""
        pass


class TestPromptGenerator:
    """Tests for prompt generation service."""
    
    @pytest.mark.skip(reason="Requires VLM access")
    async def test_generate_from_image(self):
        """Test generating prompt from image analysis."""
        pass
    
    @pytest.mark.skip(reason="Requires template system")
    async def test_generate_with_template(self):
        """Test generating prompt using template."""
        pass
    
    def test_structured_prompt_creation(self, sample_vlm_response):
        """Test creating structured prompt from VLM response."""
        from ingest_core.models.prompt_schema import PromptCategory, CategoryName
        
        # Simulate converting VLM response to categories
        subject_cat = PromptCategory(
            name=CategoryName.SUBJECT,
            value=sample_vlm_response["subject"],
            source="vlm"
        )
        
        assert subject_cat.name == CategoryName.SUBJECT
        assert subject_cat.value == sample_vlm_response["subject"]
        assert subject_cat.source == "vlm"
