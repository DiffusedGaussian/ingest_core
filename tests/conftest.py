"""
Pytest configuration and shared fixtures.

This module provides common fixtures used across all test modules.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
from PIL import Image

from ingest_core.config.settings import Settings
from ingest_core.models.asset import Asset, AssetStatus, AssetType
from ingest_core.models.prompt_schema import (
    CategoryName,
    PromptCategory,
    StructuredPrompt,
    create_empty_structured_prompt,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with isolated paths."""
    temp_dir = Path(tempfile.mkdtemp())
    
    settings = Settings(
        env="development",
        database_backend="sqlite",
        vector_database_backend="local",
    )
    
    # Override paths for testing
    settings.paths.data_dir = temp_dir / "data"
    settings.paths.upload_dir = temp_dir / "uploads"
    settings.paths.processed_dir = temp_dir / "processed"
    settings.paths.failed_dir = temp_dir / "failed"
    settings.paths.temp_dir = temp_dir / "temp"
    
    # Ensure dirs exist
    for path in [
        settings.paths.data_dir,
        settings.paths.upload_dir,
        settings.paths.processed_dir,
        settings.paths.failed_dir,
        settings.paths.temp_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    
    return settings


@pytest.fixture
def sample_asset() -> Asset:
    """Create a sample asset for testing."""
    return Asset(
        id=uuid4(),
        asset_type=AssetType.IMAGE,
        status=AssetStatus.PENDING,
        original_filename="test_image.jpg",
        file_extension=".jpg",
        file_size_bytes=1024 * 100,  # 100KB
        mime_type="image/jpeg",
        storage_path="assets/test/test_image.jpg",
    )


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Create a sample test image."""
    image_path = tmp_path / "test_image.jpg"
    
    # Create a simple 800x600 test image
    img = Image.new("RGB", (800, 600), color=(73, 109, 137))
    img.save(image_path, "JPEG")
    
    return image_path


@pytest.fixture
def sample_large_image_path(tmp_path: Path) -> Path:
    """Create a larger test image for size testing."""
    image_path = tmp_path / "large_image.jpg"
    
    # Create a 4K image
    img = Image.new("RGB", (3840, 2160), color=(200, 100, 50))
    img.save(image_path, "JPEG", quality=95)
    
    return image_path


@pytest.fixture
def sample_structured_prompt() -> StructuredPrompt:
    """Create a sample structured prompt for testing."""
    asset_id = uuid4()
    
    return StructuredPrompt(
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


@pytest.fixture
def empty_structured_prompt() -> StructuredPrompt:
    """Create an empty structured prompt."""
    return create_empty_structured_prompt(uuid4())


@pytest.fixture
async def temp_upload_file(tmp_path: Path) -> AsyncGenerator[Path, None]:
    """Create a temporary upload file for testing."""
    file_path = tmp_path / "upload_test.jpg"
    
    # Create test image
    img = Image.new("RGB", (640, 480), color=(255, 0, 0))
    img.save(file_path, "JPEG")
    
    yield file_path
    
    # Cleanup
    if file_path.exists():
        file_path.unlink()


@pytest.fixture
def mock_video_file(tmp_path: Path) -> Path:
    """Create a mock video file (empty file with .mp4 extension)."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    return video_path


@pytest.fixture
def sample_vlm_response() -> dict:
    """Sample VLM analysis response."""
    return {
        "subject": "Woman in casual attire",
        "environment": "Urban street setting",
        "lighting": "Natural daylight",
        "motion": "Walking naturally",
        "mood": "Relaxed and confident",
        "style": "Documentary style photography",
        "camera_suggestion": "dolly_in",
        "duration_suggestion": 5,
    }


@pytest.fixture
def sample_exif_data() -> dict:
    """Sample EXIF metadata."""
    return {
        "Make": "Canon",
        "Model": "EOS R5",
        "DateTime": "2026:03:23 10:30:00",
        "FNumber": 2.8,
        "ExposureTime": "1/250",
        "ISOSpeedRatings": 400,
        "FocalLength": 50,
        "LensModel": "RF 50mm F1.2 L USM",
        "ImageWidth": 8192,
        "ImageHeight": 5464,
    }
