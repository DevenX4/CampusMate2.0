"""Embedding models behind one small interface, so the model can be swapped without touching
indexing or search code.

- BgeEmbedder: the real model (BAAI/bge-small-en-v1.5, 384 dimensions) run with ONNX Runtime
  through fastembed. Downloaded once into MODEL_CACHE_DIR.
- HashEmbedder: a deterministic bag-of-words stand-in for tests (no download, no GPU). It
  only captures word overlap, so it is NEVER used to judge retrieval quality.
"""

import hashlib
import math
import re
from pathlib import Path
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class BgeEmbedder:
    # BGE is trained to embed short queries WITH this instruction and passages without it.
    QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

    def __init__(self, model_name: str, cache_dir: Path):
        from fastembed import TextEmbedding  # imported here: tests never load the real model

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir))
        self.dimension = len(next(iter(self._model.embed(["dimension probe"]))))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.embed([self.QUERY_INSTRUCTION + text]))).tolist()


class HashEmbedder:
    """Words hashed into a fixed-size vector, L2-normalised. Test use only."""

    model_name = "test-hash-embedder"

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimension] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def embedding_text(title: str | None, section: str | None, text: str) -> str:
    """What gets embedded: the chunk plus a short context header (document title, section),
    so a bare table row still carries "which document / which semester" in its vector."""
    header = " | ".join(part for part in (title, section) if part)
    return f"{header}\n{text}" if header else text
