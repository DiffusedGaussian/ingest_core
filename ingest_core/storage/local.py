"""
Local filesystem storage implementation.
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import BinaryIO

import aiofiles

from ingest_core.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """
    Storage backend that saves files to the local filesystem.
    """

    def __init__(self, root_dir: Path):
        """
        Initialize local storage.

        Args:
            root_dir: Root directory for storing files
        """
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Resolve full path and ensure it's within root_dir."""
        full_path = (self.root_dir / path).resolve()
        if not str(full_path).startswith(str(self.root_dir.resolve())):
            raise ValueError(f"Path traversal detected: {path}")
        return full_path

    async def save(self, file_obj: BinaryIO, destination: str, content_type: str | None = None) -> str:
        """
        Save a file to local storage.

        Args:
            file_obj: File-like object opened in binary mode
            destination: Destination path relative to root
            content_type: Ignored for local storage

        Returns:
            str: Relative path to the saved file
        """
        full_path = self._get_full_path(destination)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            # Check if file_obj supports async read, otherwise read synchronously
            if hasattr(file_obj, "read"):
                content = file_obj.read()
                if isinstance(content, bytes):
                    await f.write(content)
                else:
                    # Handle async read if needed, though most UploadFiles expose read/await read
                    await f.write(await content)
            else:
                 # Fallback/Assumption it's bytes
                 await f.write(file_obj)

        return str(destination)

    async def get(self, path: str) -> AsyncGenerator[bytes, None]:
        """
        Retrieve a file from local storage as a stream.

        Args:
            path: Relative path to file

        Yields:
            bytes: File content chunks
        """
        full_path = self._get_full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(8192):  # 8KB chunks
                yield chunk

    async def delete(self, path: str) -> bool:
        """
        Delete a file from local storage.

        Args:
            path: Relative path to file

        Returns:
            bool: True if deleted, False if not found
        """
        full_path = self._get_full_path(path)
        if not full_path.exists():
            return False

        os.remove(full_path)
        return True

    async def exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Relative path to file

        Returns:
            bool: True if exists
        """
        full_path = self._get_full_path(path)
        return full_path.exists()

    def get_url(self, path: str) -> str:
        """
        Get local path (not a real URL).

        Args:
            path: Relative path

        Returns:
            str: The relative path (local storage doesn't generate HTTP URLs by itself)
        """
        return str(path)
