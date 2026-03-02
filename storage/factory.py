"""
Storage backend factory.

Creates the appropriate storage backend based on configuration.
"""

from config import Settings
from storage.base import StorageBackend
from storage.local import LocalStorage


def get_storage_backend(settings: Settings) -> StorageBackend:
    """
    Create storage backend based on environment and configuration.

    Args:
        settings: Application settings

    Returns:
        StorageBackend: Configured storage backend
    """
    if settings.storage.storage_backend == "gcs":
        from storage.gcs import GCSStorageBackend
        return GCSStorageBackend(
            bucket_name=settings.storage.gcs_bucket,
            project_id=settings.storage.gcs_project_id,
        )
    else:
        return LocalStorage(
            root_dir=settings.paths.data_dir / "storage"
        )
