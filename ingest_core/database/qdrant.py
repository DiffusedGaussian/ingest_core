"""
Qdrant vector database repository.
"""

from typing import Any, List
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from structlog import get_logger

from ingest_core.config import QdrantSettings

logger = get_logger()


class QdrantRepository:
    """
    Qdrant client wrapper for vector storage.
    """

    def __init__(self, settings: QdrantSettings):
        """
        Initialize Qdrant repository.

        Args:
            settings: Qdrant configuration
        """
        self.settings = settings
        self._client: AsyncQdrantClient | None = None

    async def initialize(self) -> None:
        """
        Initialize Qdrant client and ensure collection exists.
        """
        if self._client:
            return

        try:
            logger.info(
                "Connecting to Qdrant",
                host=self.settings.qdrant_host,
                port=self.settings.qdrant_port
            )

            self._client = AsyncQdrantClient(
                host=self.settings.qdrant_host,
                port=self.settings.qdrant_port,
                api_key=self.settings.qdrant_api_key,
            )

            # Check if collection exists, create if not
            collections = await self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.settings.qdrant_collection not in collection_names:
                logger.info(
                    "Creating Qdrant collection",
                    collection=self.settings.qdrant_collection
                )
                await self._client.create_collection(
                    collection_name=self.settings.qdrant_collection,
                    vectors_config=models.VectorParams(
                        size=768,  # Default for many embeddings (e.g. CLIP/Gemini) - Make configurable?
                        distance=models.Distance.COSINE,
                    ),
                )

        except Exception as e:
            logger.error("Failed to initialize Qdrant", error=str(e))
            raise

    async def close(self) -> None:
        """Close Qdrant client."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Qdrant")

    async def upsert(
        self,
        id: str | UUID,
        vector: List[float],
        payload: dict[str, Any] | None = None
    ) -> None:
        """
        Upsert a vector.

        Args:
            id: Unique identifier (UUID or string)
            vector: Embedding vector
            payload: Metadata payload
        """
        if not self._client:
            await self.initialize()

        await self._client.upsert(
            collection_name=self.settings.qdrant_collection,
            points=[
                models.PointStruct(
                    id=str(id),
                    vector=vector,
                    payload=payload or {}
                )
            ]
        )

    async def search(
        self,
        vector: List[float],
        limit: int = 10,
        score_threshold: float | None = None
    ) -> List[models.ScoredPoint]:
        """
        Search for similar vectors.

        Args:
            vector: Query vector
            limit: Max results
            score_threshold: Minimum similarity score

        Returns:
            List of scored points
        """
        if not self._client:
            await self.initialize()

        return await self._client.search(
            collection_name=self.settings.qdrant_collection,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
        )
