"""Rerankers: score (question, passage) pairs, reading both TOGETHER.

The retrievers compare a question with each chunk only indirectly: two separately computed
vectors, or shared words. A cross-encoder feeds "question [SEP] passage" through one
transformer, so it can see how the words relate, which is much more accurate but also much
slower. It is therefore only applied to the few dozen candidates that retrieval proposes.
"""

import re
from pathlib import Path
from typing import Protocol


class Reranker(Protocol):
    model_name: str

    def score(self, query: str, passages: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    """An MS MARCO-trained cross-encoder run with ONNX Runtime (fastembed). Higher = more relevant."""

    def __init__(self, model_name: str, cache_dir: Path):
        from fastembed.rerank.cross_encoder import TextCrossEncoder  # tests never load the real model

        self.model_name = model_name
        self._model = TextCrossEncoder(model_name=model_name, cache_dir=str(cache_dir))

    def score(self, query: str, passages: list[str]) -> list[float]:
        return [float(s) for s in self._model.rerank(query, passages, batch_size=16)]


class OverlapReranker:
    """Test stand-in: counts shared words. Never used to judge quality."""

    model_name = "test-overlap-reranker"

    def score(self, query: str, passages: list[str]) -> list[float]:
        words = set(re.findall(r"[a-z0-9]+", query.lower()))
        return [float(len(words & set(re.findall(r"[a-z0-9]+", p.lower())))) for p in passages]
