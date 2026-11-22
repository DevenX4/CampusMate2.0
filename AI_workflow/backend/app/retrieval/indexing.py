"""Turning stored chunks into vectors (used by the ingestion worker and by rebuild-index)."""

from dataclasses import dataclass

from app.models.documents import Document, DocumentChunk
from app.retrieval.embeddings import Embedder, embedding_text
from app.retrieval.vector_index import VectorIndex, VectorItem, version_key


@dataclass
class ChunkIndexer:
    embedder: Embedder
    index: VectorIndex

    def index_chunks(self, document: Document, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        texts = [embedding_text(document.title, c.section, c.text) for c in chunks]
        vectors = self.embedder.embed_documents(texts)
        self.index.upsert([
            VectorItem(str(c.chunk_id), vector, text, _metadata(document, c))
            for c, vector, text in zip(chunks, vectors, texts)
        ])

    def remove_stale(self, document_id: str, version_no: int, keep_ids: set[str]) -> int:
        return self.index.delete_version(version_key(document_id, version_no), keep_ids)


def _metadata(document: Document, chunk: DocumentChunk) -> dict:
    """Filterable fields. Eligibility (active version, active document) is NOT stored here:
    PostgreSQL decides it at query time, so activation never requires re-indexing."""
    metadata = {
        "version_key": version_key(chunk.document_id, chunk.version_no),
        "document_id": chunk.document_id,
        "version_no": chunk.version_no,
        "source_type": chunk.source_type,
        "document_type": document.document_type,
    }
    for field in ("program_ids", "semester_ids"):
        if chunk.metadata_.get(field):  # Chroma does not accept empty lists
            metadata[field] = chunk.metadata_[field]
    return metadata
