import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np


class FaissRepository:
    """
    Local vector storage using FAISS and pickle for metadata.
    """
    def __init__(self, data_dir: Path, dimension: int = 1536):
        self.data_dir = data_dir
        self.dimension = dimension
        self.index_path = data_dir / "faiss.index"
        self.metadata_path = data_dir / "faiss_metadata.pkl"
        self.index = None
        self.metadata = [] # List of IDs or dicts matching index order

    async def initialize(self) -> None:
        """Initialize FAISS index."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []

    async def upsert(self, id: str, vector: list[float], payload: dict[str, Any] = None) -> None:
        """Add a vector to the index."""
        vector_np = np.array([vector]).astype('float32')
        self.index.add(vector_np)
        self.metadata.append({"id": id, "payload": payload or {}})
        await self.save()

    async def search(self, vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        vector_np = np.array([vector]).astype('float32')
        distances, indices = self.index.search(vector_np, limit)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                res = self.metadata[idx].copy()
                res["score"] = float(distances[0][i])
                results.append(res)
        return results

    async def save(self) -> None:
        """Persist index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

    async def close(self) -> None:
        """Cleanup."""
        await self.save()
