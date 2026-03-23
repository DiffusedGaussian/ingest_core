"""
Integration tests.

Tests full workflows and interactions between multiple components.
"""

import io
from pathlib import Path

import pytest

from ingest_core.models.asset import AssetStatus


@pytest.mark.integration
class TestFullIngestionPipeline:
    """Tests for complete ingestion workflow."""
    
    @pytest.mark.skip(reason="Requires full container and database setup")
    async def test_ingest_and_process_image(self, test_settings, sample_image_path):
        """Test full pipeline: upload -> process -> analyze -> store."""
        # This would test:
        # 1. File upload
        # 2. Storage backend save
        # 3. Processor validation
        # 4. Metadata extraction
        # 5. Analyzer execution
        # 6. Database persistence
        pass
    
    @pytest.mark.skip(reason="Requires full container")
    async def test_prompt_generation_workflow(self):
        """Test: upload image -> analyze -> generate structured prompt -> compile."""
        pass


@pytest.mark.integration
class TestStorageAndDatabase:
    """Tests for storage and database integration."""
    
    @pytest.mark.skip(reason="Requires database connection")
    async def test_save_and_retrieve_asset(self):
        """Test saving asset to database and retrieving it."""
        pass
    
    @pytest.mark.skip(reason="Requires database connection")
    async def test_update_asset_metadata(self):
        """Test updating asset metadata in database."""
        pass
    
    @pytest.mark.skip(reason="Requires database and storage")
    async def test_delete_asset_cascade(self):
        """Test that deleting asset removes file and database record."""
        pass


@pytest.mark.integration
class TestAPIWorkflows:
    """Tests for API endpoint workflows."""
    
    @pytest.mark.skip(reason="Requires full API setup")
    async def test_upload_analyze_retrieve(self):
        """Test: POST /assets -> background analysis -> GET /assets/{id}."""
        pass
    
    @pytest.mark.skip(reason="Requires full API setup")
    async def test_batch_upload(self):
        """Test batch upload endpoint."""
        pass
    
    @pytest.mark.skip(reason="Requires full API setup")
    async def test_prompt_generation_api(self):
        """Test prompt generation through API."""
        pass


@pytest.mark.integration
@pytest.mark.requires_api_key
class TestVLMIntegration:
    """Tests for VLM (Vision Language Model) integration."""
    
    @pytest.mark.skip(reason="Requires Gemini API key")
    async def test_gemini_analysis(self):
        """Test real Gemini VLM analysis."""
        pass
    
    @pytest.mark.skip(reason="Requires VLM setup")
    async def test_structured_prompt_from_vlm(self):
        """Test creating StructuredPrompt from VLM analysis."""
        pass


@pytest.mark.integration
class TestAnalyzerPipeline:
    """Tests for analyzer pipeline execution."""
    
    @pytest.mark.skip(reason="Requires analyzer setup")
    async def test_run_all_analyzers(self, sample_image_path):
        """Test running all enabled analyzers on an image."""
        pass
    
    @pytest.mark.skip(reason="Requires analyzer setup")
    async def test_analyzer_error_handling(self):
        """Test that analyzer pipeline handles individual analyzer failures."""
        pass


@pytest.mark.integration
class TestLineageTracking:
    """Tests for lineage tracking across generations."""
    
    @pytest.mark.skip(reason="Requires database and lineage service")
    async def test_create_lineage_chain(self):
        """Test creating parent->child lineage relationships."""
        pass
    
    @pytest.mark.skip(reason="Requires lineage service")
    async def test_query_lineage_tree(self):
        """Test retrieving full lineage tree."""
        pass


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance and load tests."""
    
    @pytest.mark.skip(reason="Slow test")
    async def test_batch_processing_performance(self):
        """Test processing multiple assets in parallel."""
        pass
    
    @pytest.mark.skip(reason="Slow test")
    async def test_large_file_handling(self):
        """Test handling large image/video files."""
        pass


# Smoke tests - quick checks that basic functionality works
@pytest.mark.integration
class TestSmokeTests:
    """Basic smoke tests for critical paths."""
    
    def test_import_core_modules(self):
        """Test that all core modules can be imported."""
        try:
            from ingest_core.models import asset
            from ingest_core.adapters import kling
            from ingest_core.processors import image
            from ingest_core.storage import local
            from ingest_core.config import settings
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")
    
    def test_settings_initialization(self):
        """Test that settings can be initialized."""
        from ingest_core.config.settings import Settings
        
        settings = Settings()
        assert settings is not None
        assert settings.env in ["development", "staging", "production"]
    
    def test_adapter_creation(self, test_settings):
        """Test that adapters can be created."""
        from ingest_core.adapters.kling import KlingAdapter
        
        adapter = KlingAdapter(test_settings)
        assert adapter is not None
        assert adapter.name == "kling"
    
    def test_model_validation(self):
        """Test that models validate correctly."""
        from ingest_core.models.asset import Asset, AssetType
        
        asset = Asset(
            asset_type=AssetType.IMAGE,
            original_filename="test.jpg",
            file_extension=".jpg",
            file_size_bytes=1024,
            mime_type="image/jpeg",
            storage_path="test/path",
        )
        
        assert asset.id is not None
        assert asset.status == AssetStatus.PENDING
