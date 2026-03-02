"""
Google Cloud Storage backend.

Used for production deployments.
"""

from typing import BinaryIO
import io

from google.cloud import storage

from storage.base import StorageBackend


class GCSStorageBackend(StorageBackend):
    """
    Google Cloud Storage backend.

    Stores files in a GCS bucket.
    Suitable for production and multi-server deployments.
    """

    def __init__(self, bucket_name: str, project_id: str | None = None):
        """
        Initialize GCS storage.

        Args:
            bucket_name: GCS bucket name
            project_id: Optional GCP project ID
        """
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

    async def save(self, file: BinaryIO, destination: str) -> str:
        """Save file to GCS."""
        blob = self.bucket.blob(destination)
        blob.upload_from_file(file)
        return f"gs://{self.bucket_name}/{destination}"

    async def save_bytes(self, data: bytes, destination: str) -> str:
        """Save bytes to GCS."""
        blob = self.bucket.blob(destination)
        blob.upload_from_string(data)
        return f"gs://{self.bucket_name}/{destination}"

    async def load(self, path: str) -> bytes:
        """Load file from GCS."""
        blob = self.bucket.blob(path)
        return blob.download_as_bytes()

    async def delete(self, path: str) -> bool:
        """Delete file from GCS."""
        blob = self.bucket.blob(path)
        if blob.exists():
            blob.delete()
            return True
        return False

    async def exists(self, path: str) -> bool:
        """Check if file exists in GCS."""
        blob = self.bucket.blob(path)
        return blob.exists()

    async def list_files(self, prefix: str = "") -> list[str]:
        """List files in GCS bucket with prefix."""
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]

    def get_public_url(self, path: str) -> str | None:
        """
        Get public URL for a GCS file.

        Note: File must have public access enabled.
        """
        return f"https://storage.googleapis.com/{self.bucket_name}/{path}"