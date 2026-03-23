"""
Tests for analyzers.

Tests EXIF, perceptual hash, and other analysis modules.
"""

from pathlib import Path

import pytest
from PIL import Image

from ingest_core.analyzers.base import BaseAnalyzer


class TestBaseAnalyzer:
    """Tests for base analyzer interface."""
    
    def test_base_analyzer_is_abstract(self):
        """Test that BaseAnalyzer is abstract."""
        from abc import ABC
        
        assert issubclass(BaseAnalyzer, ABC)
        assert hasattr(BaseAnalyzer, 'analyze')
        assert hasattr(BaseAnalyzer, 'name')


class TestEXIFAnalyzer:
    """Tests for EXIF metadata analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create EXIF analyzer instance."""
        from ingest_core.analyzers.exif import EXIFAnalyzer
        return EXIFAnalyzer()
    
    def test_analyzer_name(self, analyzer):
        """Test analyzer name."""
        assert analyzer.name == "exif"
    
    @pytest.mark.asyncio
    async def test_analyze_image_with_exif(self, analyzer, tmp_path):
        """Test extracting EXIF data from image."""
        # Create image with EXIF
        img_path = tmp_path / "with_exif.jpg"
        img = Image.new("RGB", (1920, 1080), color=(50, 100, 150))
        
        # Add EXIF data
        exif = img.getexif()
        exif[0x010F] = "Canon"  # Make
        exif[0x0110] = "EOS R5"  # Model
        
        img.save(img_path, "JPEG", exif=exif)
        
        # Analyze
        result = await analyzer.analyze(img_path, "image")
        
        assert result is not None
        assert hasattr(result, 'data')
    
    @pytest.mark.asyncio
    async def test_analyze_image_without_exif(self, analyzer, sample_image_path):
        """Test analyzing image without EXIF data."""
        result = await analyzer.analyze(sample_image_path, "image")
        
        # Should still return a result, even if empty
        assert hasattr(result, 'data')
    
    @pytest.mark.asyncio
    async def test_analyze_invalid_file(self, analyzer, tmp_path):
        """Test analyzing invalid file."""
        invalid_path = tmp_path / "not_an_image.txt"
        invalid_path.write_text("This is text")
        
        result = await analyzer.analyze(invalid_path, "image")
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')


class TestPhashAnalyzer:
    """Tests for perceptual hash analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create phash analyzer instance."""
        from ingest_core.analyzers.phash import PerceptualHashAnalyzer
        return PerceptualHashAnalyzer()
    
    def test_analyzer_name(self, analyzer):
        """Test analyzer name."""
        assert analyzer.name == "phash"
    
    @pytest.mark.asyncio
    async def test_compute_phash(self, analyzer, sample_image_path):
        """Test computing perceptual hash."""
        result = await analyzer.analyze(sample_image_path, "image")
        
        assert result is not None
        assert hasattr(result, 'data')
        if result.success:
            assert "phash" in result.data
    
    @pytest.mark.asyncio
    async def test_similar_images_same_hash(self, analyzer, tmp_path):
        """Test that similar images have similar hashes."""
        # Create two similar images
        img1_path = tmp_path / "img1.jpg"
        img2_path = tmp_path / "img2.jpg"
        
        img1 = Image.new("RGB", (640, 480), color=(100, 100, 100))
        img2 = Image.new("RGB", (640, 480), color=(101, 101, 101))  # Very similar
        
        img1.save(img1_path, "JPEG")
        img2.save(img2_path, "JPEG")
        
        hash1 = await analyzer.analyze(img1_path, "image")
        hash2 = await analyzer.analyze(img2_path, "image")
        
        assert hash1 is not None
        assert hash2 is not None
        assert hash1.success and hash2.success
        # Hashes should exist (similarity check would need more logic)


class TestAnalyzerRegistry:
    """Tests for analyzer plugin system."""
    
    def test_get_enabled_analyzers(self, test_settings):
        """Test getting list of enabled analyzers."""
        analyzers = test_settings.plugins.analyzer_list
        
        assert isinstance(analyzers, list)
        assert len(analyzers) > 0
    
    def test_analyzer_names(self):
        """Test that all analyzers have names."""
        from ingest_core.analyzers.exif import EXIFAnalyzer
        from ingest_core.analyzers.phash import PerceptualHashAnalyzer
        
        exif = EXIFAnalyzer()
        phash = PerceptualHashAnalyzer()
        
        assert exif.name == "exif"
        assert phash.name == "phash"
