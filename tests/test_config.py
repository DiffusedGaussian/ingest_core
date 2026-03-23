"""
Tests for configuration and settings.

Tests Pydantic settings and configuration management.
"""

from pathlib import Path

import pytest

from ingest_core.config.settings import (
    Settings,
    PathSettings,
    GeminiSettings,
    KlingAdapterSettings,
    PromptAdapterSettings,
    get_settings,
)


class TestSettings:
    """Tests for main Settings class."""
    
    def test_default_settings(self):
        """Test creating settings with defaults."""
        settings = Settings()
        
        assert settings.env == "development"
        assert settings.database_backend in ["mongodb", "sqlite"]
        assert settings.vector_database_backend in ["qdrant", "local"]
    
    def test_settings_singleton(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_environment_checks(self):
        """Test environment property checks."""
        dev_settings = Settings(env="development")
        prod_settings = Settings(env="production")
        
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False
        
        assert prod_settings.is_development is False
        assert prod_settings.is_production is True
    
    def test_nested_settings(self):
        """Test access to nested settings groups."""
        settings = Settings()
        
        assert hasattr(settings, 'paths')
        assert hasattr(settings, 'storage')
        assert hasattr(settings, 'mongodb')
        assert hasattr(settings, 'api')
        assert hasattr(settings, 'adapters')
        
        assert isinstance(settings.paths, PathSettings)
        assert isinstance(settings.adapters, PromptAdapterSettings)


class TestPathSettings:
    """Tests for path configuration."""
    
    def test_default_paths(self):
        """Test default path values."""
        paths = PathSettings()
        
        assert paths.data_dir is not None
        assert paths.upload_dir is not None
        assert paths.processed_dir is not None
        assert paths.failed_dir is not None
        assert paths.temp_dir is not None
    
    def test_paths_are_absolute(self):
        """Test that paths are converted to absolute."""
        paths = PathSettings()
        
        assert paths.data_dir.is_absolute()
        assert paths.upload_dir.is_absolute()
        assert paths.processed_dir.is_absolute()
    
    def test_paths_created(self):
        """Test that paths are created on initialization."""
        paths = PathSettings()
        
        # Paths should exist after initialization
        assert paths.data_dir.exists()
        assert paths.upload_dir.exists()


class TestGeminiSettings:
    """Tests for Gemini VLM settings."""
    
    def test_default_model(self):
        """Test default Gemini model."""
        gemini = GeminiSettings()
        
        assert gemini.model == "gemini-3-flash-preview"
        assert gemini.api_key is None or isinstance(gemini.api_key, str)


class TestAdapterSettings:
    """Tests for prompt adapter settings."""
    
    def test_kling_adapter_defaults(self):
        """Test Kling adapter default settings."""
        kling = KlingAdapterSettings()
        
        assert kling.version == "1.5"
        assert kling.max_prompt_length == 500
        assert kling.default_separator == ". "
        assert len(kling.category_order) > 0
        assert len(kling.camera_vocabulary) > 0
        assert len(kling.lighting_vocabulary) > 0
    
    def test_kling_camera_vocabulary(self):
        """Test Kling camera vocabulary contains expected terms."""
        kling = KlingAdapterSettings()
        
        expected_cameras = ["static", "dolly_in", "dolly_out", "orbit_left", "pan_left"]
        for camera in expected_cameras:
            assert camera in kling.camera_vocabulary
    
    def test_kling_lighting_vocabulary(self):
        """Test Kling lighting vocabulary."""
        kling = KlingAdapterSettings()
        
        expected_lighting = ["golden_hour", "studio", "natural", "dramatic"]
        for light in expected_lighting:
            assert light in kling.lighting_vocabulary
    
    def test_kling_negative_prompt(self):
        """Test default negative prompt."""
        kling = KlingAdapterSettings()
        
        assert len(kling.negative_prompt) > 0
        assert "blurry" in kling.negative_prompt.lower()
    
    def test_adapter_settings_default_adapter(self):
        """Test default adapter selection."""
        adapters = PromptAdapterSettings()
        
        assert adapters.default_adapter == "kling"
        assert hasattr(adapters, 'kling')
        assert hasattr(adapters, 'runway')
        assert hasattr(adapters, 'midjourney')
    
    def test_access_nested_adapter_config(self):
        """Test accessing nested adapter configurations."""
        settings = Settings()
        
        # Access Kling config through main settings
        kling_config = settings.adapters.kling
        
        assert isinstance(kling_config, KlingAdapterSettings)
        assert kling_config.version == "1.5"


class TestPluginSettings:
    """Tests for plugin configuration."""
    
    def test_default_analyzers(self):
        """Test default enabled analyzers."""
        settings = Settings()
        
        analyzer_list = settings.plugins.analyzer_list
        
        assert isinstance(analyzer_list, list)
        assert len(analyzer_list) > 0
    
    def test_analyzer_list_parsing(self):
        """Test parsing comma-separated analyzer list."""
        from ingest_core.config.settings import PluginSettings
        
        plugins = PluginSettings(enabled_analyzers="exif,phash,vlm")
        
        analyzers = plugins.analyzer_list
        assert "exif" in analyzers
        assert "phash" in analyzers
        assert "vlm" in analyzers
        assert len(analyzers) == 3


class TestProcessingSettings:
    """Tests for processing configuration."""
    
    def test_default_processing_params(self):
        """Test default processing parameters."""
        settings = Settings()
        
        assert settings.processing.max_file_size_mb > 0
        assert settings.processing.video_max_duration_seconds > 0
        assert settings.processing.keyframe_max_count > 0
        assert settings.processing.keyframe_extraction_method in ["scene", "interval", "uniform"]


class TestAPISettings:
    """Tests for API configuration."""
    
    def test_default_api_config(self):
        """Test default API settings."""
        settings = Settings()
        
        assert settings.api.api_host == "0.0.0.0"
        assert settings.api.api_port > 0
        assert settings.api.api_workers > 0
        assert isinstance(settings.api.api_reload, bool)
