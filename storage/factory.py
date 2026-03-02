"""
Storage backend factory.

Creates the appropriate storage backend based on configuration.
"""

from ingest_core.config import Settings
from ingest_core.storage.base import StorageBackend
from ingest_core.storage.local import LocalStorageBackend
from ingest_core.storage.gcs import GCSStorageBackend


def get_storage_backend(settings: Settings) -> StorageBackend:
    """
    Create storage backend based on environment and configuration.

    Args:
        settings: Application settings

    Returns:
        StorageBackend: Configured storage backend
    """
    if settings.use_gcs:
        return GCSStorageBackend(
            bucket_name=settings.storage.gcs_bucket_name,
            project_id=settings.storage.gcs_project_id,
        )
    else:
        return LocalStorageBackend(
            base_path=settings.storage.local_storage_path
        )