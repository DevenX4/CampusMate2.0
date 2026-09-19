"""One embedding model and one vector index per process (loading a model takes seconds).
Used as FastAPI dependencies and by the worker; tests replace them with fakes."""

from functools import lru_cache

from app.core.config import get_settings
from app.retrieval.embeddings import BgeEmbedder, Embedder
from app.retrieval.indexing import ChunkIndexer
from app.retrieval.vector_index import VectorIndex


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return BgeEmbedder(settings.embedding_model, settings.model_cache_dir)


@lru_cache
def get_vector_index() -> VectorIndex:
    settings, embedder = get_settings(), get_embedder()
    return VectorIndex(settings.storage_dir / "chroma", settings.chroma_collection,
                       embedder.model_name, embedder.dimension)


def get_indexer() -> ChunkIndexer:
    return ChunkIndexer(get_embedder(), get_vector_index())
