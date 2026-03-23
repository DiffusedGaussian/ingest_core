"""
Tests for media processors.

Tests image, video, and 3D asset processors.
"""

from pathlib import Path

import pytest
from PIL import Image

from ingest_core.processors.base import BaseProcessor
from ingest_core.processors.image import ImageProcessor


class TestImageProcessor:
    """Tests for ImageProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create image processor instance."""
        return ImageProcessor()
    
    def test_processor_name(self, processor):
        """Test processor name."""
        assert processor.name == "image"
    
    def test_supported_extensions(self, processor):
        """Test supported file extensions."""
        assert ".jpg" in processor.supported_extensions
        assert ".jpeg" in processor.supported_extensions
        assert ".png" in processor.supported_extensions
        assert ".webp" in processor.supported_extensions
    
    def test_supports_valid_extensions(self, processor, tmp_path):
        """Test file extension support detection."""
        jpg_file = tmp_path / "test.jpg"
        png_file = tmp_path / "test.png"
        txt_file = tmp_path / "test.txt"
        
        assert processor.supports(jpg_file)
        assert processor.supports(png_file)
        assert not processor.supports(txt_file)
    
    @pytest.mark.asyncio
    async def test_validate_valid_image(self, processor, sample_image_path):
        """Test validation of valid image."""
        is_valid, error = await processor.validate(sample_image_path)
        
        assert is_valid is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_invalid_file(self, processor, tmp_path):
        """Test validation of invalid file."""
        invalid_file = tmp_path / "invalid.jpg"
        invalid_file.write_text("not an image")
        
        is_valid, error = await processor.validate(invalid_file)
        
        assert is_valid is False
        assert error is not None
    
    @pytest.mark.asyncio
    async def test_validate_nonexistent_file(self, processor, tmp_path):
        """Test validation of nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.jpg"
        
        is_valid, error = await processor.validate(nonexistent)
        
        assert is_valid is False
        assert error is not None
    
    @pytest.mark.asyncio
    async def test_extract_metadata(self, processor, sample_image_path):
        """Test metadata extraction."""
        metadata = await processor.extract_metadata(sample_image_path)
        
        assert "width" in metadata
        assert "height" in metadata
        assert "format" in metadata
        assert "mode" in metadata
        assert metadata["width"] == 800
        assert metadata["height"] == 600
        assert metadata["format"] == "JPEG"
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_exif(self, processor, tmp_path):
        """Test metadata extraction including EXIF data."""
        # Create image with EXIF data
        img_path = tmp_path / "with_exif.jpg"
        img = Image.new("RGB", (1024, 768), color=(100, 150, 200))
        
        # Add basic EXIF
        from PIL import Image as PILImage
        exif = img.getexif()
        exif[0x010F] = "Test Camera"  # Make
        exif[0x0110] = "Test Model"   # Model
        
        img.save(img_path, "JPEG", exif=exif)
        
        metadata = await processor.extract_metadata(img_path)
        
        assert "width" in metadata
        assert "height" in metadata
        assert metadata["width"] == 1024
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail(self, processor, sample_image_path, tmp_path):
        """Test thumbnail generation."""
        output_path = tmp_path / "thumbnail.jpg"
        
        result = await processor.generate_thumbnail(
            sample_image_path,
            output_path,
            size=(256, 256)
        )
        
        assert result is not None
        assert output_path.exists()
        
        # Verify thumbnail dimensions
        thumb = Image.open(output_path)
        assert thumb.width <= 256
        assert thumb.height <= 256
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail_custom_size(self, processor, sample_image_path, tmp_path):
        """Test thumbnail with custom size."""
        output_path = tmp_path / "custom_thumb.jpg"
        
        result = await processor.generate_thumbnail(
            sample_image_path,
            output_path,
            size=(128, 128)
        )
        
        assert result is not None
        thumb = Image.open(output_path)
        assert thumb.width <= 128
        assert thumb.height <= 128
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail_preserves_aspect(self, processor, sample_image_path, tmp_path):
        """Test that thumbnail preserves aspect ratio."""
        output_path = tmp_path / "aspect_thumb.jpg"
        
        # Original is 800x600 (4:3 ratio)
        await processor.generate_thumbnail(
            sample_image_path,
            output_path,
            size=(256, 256)
        )
        
        thumb = Image.open(output_path)
        # Should maintain 4:3 aspect ratio
        aspect_ratio = thumb.width / thumb.height
        assert 1.3 < aspect_ratio < 1.4  # Approximately 4:3


class TestBaseProcessor:
    """Tests for base processor interface."""
    
    def test_base_processor_interface(self):
        """Test base processor abstract interface."""
        from abc import ABC
        
        assert issubclass(BaseProcessor, ABC)
        
        # Check required methods
        assert hasattr(BaseProcessor, 'validate')
        assert hasattr(BaseProcessor, 'extract_metadata')
        assert hasattr(BaseProcessor, 'generate_thumbnail')
        assert hasattr(BaseProcessor, 'supports')
    
    def test_supports_method(self):
        """Test the supports method logic."""
        processor = ImageProcessor()
        
        # Test various extensions
        assert processor.supports(Path("test.jpg"))
        assert processor.supports(Path("test.JPG"))  # Case insensitive
        assert processor.supports(Path("/path/to/image.png"))
        assert not processor.supports(Path("document.pdf"))
