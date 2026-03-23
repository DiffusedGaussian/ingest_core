"""
Test utilities and helper functions.

Common utilities used across test modules.
"""

import io
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from PIL import Image

from ingest_core.models.asset import Asset, AssetType, AssetStatus
from ingest_core.models.prompt_schema import (
    CategoryName,
    PromptCategory,
    StructuredPrompt,
)


def create_test_image(
    width: int = 800,
    height: int = 600,
    color: tuple[int, int, int] = (100, 150, 200),
    format: str = "JPEG"
) -> Image.Image:
    """
    Create a test image in memory.
    
    Args:
        width: Image width
        height: Image height
        color: RGB color tuple
        format: Image format
    
    Returns:
        PIL Image object
    """
    img = Image.new("RGB", (width, height), color=color)
    return img


def save_test_image(
    path: Path,
    width: int = 800,
    height: int = 600,
    color: tuple[int, int, int] = (100, 150, 200),
) -> Path:
    """
    Create and save a test image to disk.
    
    Args:
        path: Path to save image
        width: Image width
        height: Image height
        color: RGB color tuple
    
    Returns:
        Path to saved image
    """
    img = create_test_image(width, height, color)
    img.save(path, "JPEG")
    return path


def create_test_image_bytes(
    width: int = 800,
    height: int = 600,
    format: str = "JPEG"
) -> bytes:
    """
    Create test image as bytes.
    
    Args:
        width: Image width
        height: Image height
        format: Image format
    
    Returns:
        Image bytes
    """
    img = create_test_image(width, height)
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


def create_test_asset(
    asset_type: AssetType = AssetType.IMAGE,
    filename: str = "test.jpg",
    status: AssetStatus = AssetStatus.PENDING,
    **kwargs
) -> Asset:
    """
    Create a test Asset instance.
    
    Args:
        asset_type: Type of asset
        filename: Original filename
        status: Asset status
        **kwargs: Additional Asset fields
    
    Returns:
        Asset instance
    """
    defaults = {
        "asset_type": asset_type,
        "original_filename": filename,
        "file_extension": Path(filename).suffix,
        "file_size_bytes": 1024 * 100,
        "mime_type": f"{asset_type.value}/jpeg",
        "storage_path": f"test/{filename}",
        "status": status,
    }
    defaults.update(kwargs)
    return Asset(**defaults)


def create_test_structured_prompt(
    asset_id: str | None = None,
    **overrides
) -> StructuredPrompt:
    """
    Create a test StructuredPrompt with sensible defaults.
    
    Args:
        asset_id: Asset ID (generates new if None)
        **overrides: Override specific category values
    
    Returns:
        StructuredPrompt instance
    """
    if asset_id is None:
        asset_id = uuid4()
    
    defaults = {
        "subject": "Test subject",
        "appearance": "Test appearance",
        "environment": "Test environment",
        "lighting": "studio",
        "camera": "dolly_in",
        "motion": "subtle movement",
        "mood": "neutral",
        "style": "realistic",
        "technical": "4K, high quality",
    }
    defaults.update(overrides)
    
    return StructuredPrompt(
        asset_id=asset_id,
        subject=PromptCategory(
            name=CategoryName.SUBJECT,
            value=defaults["subject"],
            source="manual"
        ),
        appearance=PromptCategory(
            name=CategoryName.APPEARANCE,
            value=defaults["appearance"],
            source="manual"
        ),
        environment=PromptCategory(
            name=CategoryName.ENVIRONMENT,
            value=defaults["environment"],
            source="manual"
        ),
        lighting=PromptCategory(
            name=CategoryName.LIGHTING,
            value=defaults["lighting"],
            source="manual"
        ),
        camera=PromptCategory(
            name=CategoryName.CAMERA,
            value=defaults["camera"],
            source="manual"
        ),
        motion=PromptCategory(
            name=CategoryName.MOTION,
            value=defaults["motion"],
            source="manual"
        ),
        mood=PromptCategory(
            name=CategoryName.MOOD,
            value=defaults["mood"],
            source="manual"
        ),
        style=PromptCategory(
            name=CategoryName.STYLE,
            value=defaults["style"],
            source="manual"
        ),
        technical=PromptCategory(
            name=CategoryName.TECHNICAL,
            value=defaults["technical"],
            source="manual"
        ),
        created_from="manual"
    )


def assert_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        value: String to check
    
    Returns:
        True if valid UUID
    """
    from uuid import UUID
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def mock_file_upload(content: bytes, filename: str, content_type: str) -> BinaryIO:
    """
    Create a mock file upload object.
    
    Args:
        content: File content bytes
        filename: Filename
        content_type: MIME type
    
    Returns:
        File-like object
    """
    file_obj = io.BytesIO(content)
    file_obj.name = filename
    file_obj.content_type = content_type
    return file_obj


class MockContainer:
    """Mock container for testing services."""
    
    def __init__(self, settings=None):
        """Initialize mock container."""
        from ingest_core.config.settings import Settings
        self.settings = settings or Settings()
        self.storage = None
        self.db = None
        self.mongodb = None
    

def compare_dicts_subset(actual: dict, expected: dict) -> bool:
    """
    Check if actual dict contains all keys/values from expected dict.
    
    Args:
        actual: Actual dictionary
        expected: Expected key/value pairs
    
    Returns:
        True if all expected keys exist with matching values
    """
    for key, value in expected.items():
        if key not in actual:
            return False
        if actual[key] != value:
            return False
    return True


def create_mock_vlm_response() -> dict:
    """
    Create mock VLM analysis response.
    
    Returns:
        Dict with VLM analysis fields
    """
    return {
        "subject": "Person in frame",
        "environment": "Indoor setting",
        "lighting": "Natural light",
        "motion": "Minimal movement",
        "mood": "Calm atmosphere",
        "style": "Documentary style",
        "camera_suggestion": "static",
        "duration_suggestion": 5,
    }
