"""The vector index (Chroma): stores one embedding per chunk and finds the nearest ones.

Chroma is a DERIVED index: every vector can be rebuilt from document_chunks in PostgreSQL
(`python -m app.retrieval rebuild-index`). PostgreSQL decides which chunks are eligible
(active versions of active documents); Chroma only measures similarity among them.

The search is EXACT: Chroma filters the vectors by metadata and numpy compares the query with
every one of them. Chroma's own approximate (HNSW) search was measured to return different
neighbours in different processes, missing a true #2 neighbour in about half the runs, even on
a freshly built index. At this size (about 1,000 chunks) the exact search costs about 25 ms; it
grows linearly (roughly 30 ms per 1,000 chunks), so with tens of thousands of chunks an
approximate index would be worth its errors again, after measuring its recall.
"""

from dataclasses import dataclass
from pathlib import Path

import chromadb
import numpy as np


def version_key(document_id: str, version_no: int) -> str:
    return f"{document_id}:v{version_no}"


@dataclass
class VectorItem:
    chunk_id: str
    vector: list[float]
    text: str  # the embedded text (kept for inspection)
    metadata: dict


class VectorIndex:
    def __init__(self, path: Path, collection: str, model_name: str, dimension: int):
        self._client = chromadb.PersistentClient(
            path=str(path), settings=chromadb.Settings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(
            collection, embedding_function=None,
            metadata={"hnsw:space": "cosine", "embedding_model": model_name, "dimension": dimension},
        )
        stored = self._collection.metadata or {}
        if stored.get("embedding_model") != model_name or stored.get("dimension") != dimension:
            # Vectors from different models are not comparable: never mix them.
            raise RuntimeError(
                f"Chroma collection '{collection}' was built with {stored.get('embedding_model')} "
                f"({stored.get('dimension')} dims), not {model_name} ({dimension} dims). "
                f"Run: python -m app.retrieval rebuild-index --reset")

    def count(self) -> int:
        return self._collection.count()

    def upsert(self, items: list[VectorItem]) -> None:
        for start in range(0, len(items), 500):  # Chroma limits the batch size
            batch = items[start:start + 500]
            self._collection.upsert(
                ids=[i.chunk_id for i in batch], embeddings=[i.vector for i in batch],
                documents=[i.text for i in batch], metadatas=[i.metadata for i in batch],
            )

    def delete_version(self, key: str, keep_ids: set[str] = frozenset()) -> int:
        """Remove a version's vectors, except the ones in keep_ids (e.g. just written)."""
        existing = self._collection.get(where={"version_key": key}, include=[])["ids"]
        stale = [i for i in existing if i not in keep_ids]
        if stale:
            self._collection.delete(ids=stale)
        return len(stale)

    def query(self, vector: list[float], k: int, where: dict) -> list[tuple[str, float]]:
        """(chunk_id, cosine similarity) of the k most similar vectors matching `where`: exact,
        and deterministic (equal scores are ordered by chunk id)."""
        found = self._collection.get(where=where, include=["embeddings"])
        if not found["ids"]:
            return []
        matrix = np.asarray(found["embeddings"], dtype=np.float32)
        query = np.asarray(vector, dtype=np.float32)
        similarity = matrix @ query / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query) + 1e-12)
        order = np.lexsort((np.asarray(found["ids"]), -similarity))[:k]
        return [(found["ids"][i], float(similarity[i])) for i in order]

    def reset(self) -> None:
        name, metadata = self._collection.name, self._collection.metadata
        self._client.delete_collection(name)
        self._collection = self._client.create_collection(name, embedding_function=None, metadata=metadata)
