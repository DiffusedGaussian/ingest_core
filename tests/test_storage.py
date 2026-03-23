"""
Tests for storage backends.

Tests local and cloud storage implementations.
"""

import io
from pathlib import Path

import pytest

from ingest_core.storage.base import StorageBackend
from ingest_core.storage.local import LocalStorage


class TestLocalStorage:
    """Tests for local file system storage."""
    
    @pytest.fixture
    def storage(self, test_settings):
        """Create local storage instance."""
        return LocalStorage(test_settings.paths.data_dir)
    
    @pytest.mark.asyncio
    async def test_save_file(self, storage, test_settings):
        """Test saving a file to local storage."""
        content = b"Hello, World!"
        file_obj = io.BytesIO(content)
        destination = "test/hello.txt"
        
        saved_path = await storage.save(file_obj, destination, "text/plain")
        
        assert saved_path is not None
        # Verify file exists
        full_path = test_settings.paths.data_dir / destination
        assert full_path.exists()
        assert full_path.read_bytes() == content
    
    @pytest.mark.asyncio
    async def test_save_binary_file(self, storage, test_settings, sample_image_path):
        """Test saving binary file."""
        with open(sample_image_path, "rb") as f:
            saved_path = await storage.save(f, "test/image.jpg", "image/jpeg")
        
        assert saved_path is not None
        full_path = test_settings.paths.data_dir / "test/image.jpg"
        assert full_path.exists()
    
    @pytest.mark.asyncio
    async def test_get_file(self, storage):
        """Test retrieving a file."""
        # First save a file
        content = b"Test content for retrieval"
        file_obj = io.BytesIO(content)
        destination = "test/retrieve.txt"
        
        await storage.save(file_obj, destination)
        
        # Now retrieve it
        retrieved_content = b""
        async for chunk in storage.get(destination):
            retrieved_content += chunk
        
        assert retrieved_content == content
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, storage):
        """Test retrieving nonexistent file."""
        with pytest.raises(FileNotFoundError):
            async for _ in storage.get("nonexistent/file.txt"):
                pass
    
    @pytest.mark.asyncio
    async def test_exists(self, storage):
        """Test checking file existence."""
        # Save a file
        content = b"Existence test"
        file_obj = io.BytesIO(content)
        destination = "test/exists.txt"
        
        await storage.save(file_obj, destination)
        
        # Test existence
        assert await storage.exists(destination) is True
        assert await storage.exists("does/not/exist.txt") is False
    
    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test deleting a file."""
        # Save a file
        content = b"Delete me"
        file_obj = io.BytesIO(content)
        destination = "test/delete.txt"
        
        await storage.save(file_obj, destination)
        assert await storage.exists(destination)
        
        # Delete it
        result = await storage.delete(destination)
        assert result is True
        assert await storage.exists(destination) is False
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        """Test deleting nonexistent file."""
        result = await storage.delete("does/not/exist.txt")
        assert result is False
    
    def test_get_url(self, storage, test_settings):
        """Test getting file URL."""
        destination = "test/file.txt"
        url = storage.get_url(destination)
        
        # Local storage returns relative path (not full URL)
        assert url == destination
    
    @pytest.mark.asyncio
    async def test_save_creates_directories(self, storage, test_settings):
        """Test that save creates nested directories."""
        content = b"Nested content"
        file_obj = io.BytesIO(content)
        destination = "deep/nested/path/file.txt"
        
        saved_path = await storage.save(file_obj, destination)
        
        assert saved_path is not None
        full_path = test_settings.paths.data_dir / destination
        assert full_path.exists()
        assert full_path.parent.exists()


class TestStorageBackend:
    """Tests for storage backend interface."""
    
    def test_storage_backend_interface(self):
        """Test that storage backend is an abstract base class."""
        from abc import ABC
        
        assert issubclass(StorageBackend, ABC)
        
        # Check required methods
        assert hasattr(StorageBackend, 'save')
        assert hasattr(StorageBackend, 'get')
        assert hasattr(StorageBackend, 'delete')
        assert hasattr(StorageBackend, 'exists')
        assert hasattr(StorageBackend, 'get_url')
    
    def test_storage_factory(self, test_settings):
        """Test storage factory creates correct backend."""
        from ingest_core.storage.factory import get_storage_backend
        
        # With local backend
        test_settings.storage.storage_backend = "local"
        storage = get_storage_backend(test_settings)
        
        assert isinstance(storage, LocalStorage)
