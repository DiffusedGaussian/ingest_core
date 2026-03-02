"""
Base storage interface.

Defines the contract for all storage backends.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, BinaryIO


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    Implementations must handle:
    - Saving files
    - Retrieving files
    - Deleting files
    - Generating presigned URLs (optional)
    """

    @abstractmethod
    async def save(self, file_obj: BinaryIO, destination: str, content_type: str | None = None) -> str:
        """
        Save a file to storage.

        Args:
            file_obj: File-like object opened in binary mode
            destination: Destination path/key
            content_type: MIME type of the file

        Returns:
            str: Publicly accessible URL or path
        """
        pass

    @abstractmethod
    async def get(self, path: str) -> AsyncGenerator[bytes, None]:
        """
        Retrieve a file from ingest_core.storage as a stream.

        Args:
            path: Path/key of the file

        Yields:
            bytes: File content chunks
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a file from ingest_core.storage.

        Args:
            path: Path/key of the file

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path/key of the file

        Returns:
            bool: True if exists
        """
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """
        Get the public URL for a file.

        Args:
            path: Path/key of the file

        Returns:
            str: Public URL
        """
        pass
