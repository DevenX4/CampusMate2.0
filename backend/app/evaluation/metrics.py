"""Retrieval metrics, as pure functions (no database, easy to check by hand).

A retrieved chunk is RELEVANT to a question if it comes from one of the question's required
sources: the same document, and (when the source names a page) a page range that covers it.
"""

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Source:
    document_id: str
    page: int | None


@dataclass(frozen=True)
class Retrieved:
    document_id: str
    page_start: int | None
    page_end: int | None
    entity_ids: tuple[str, ...]
    score: float


def matches(hit: Retrieved, source: Source) -> bool:
    if hit.document_id != source.document_id:
        return False
    if source.page is None or hit.page_start is None:
        return True
    return hit.page_start <= source.page <= (hit.page_end or hit.page_start)


def question_metrics(hits: list[Retrieved], sources: list[Source], entities: list[str], k: int) -> dict:
    """Metrics for one question at cut-off k.

    hit        1 if any relevant chunk is in the top k (the answer is reachable at all)
    recall     share of the required sources covered by the top k (all evidence present?)
    precision  share of the top k that is relevant (how much noise reaches the model)
    rr         1 / rank of the first relevant chunk (0 if none): averaged, this is MRR
    entity_recall  share of the expected entities mentioned by the top k chunks
    """
    top = hits[:k]
    relevant_flags = [any(matches(h, s) for s in sources) for h in top]
    first = next((rank for rank, ok in enumerate(relevant_flags, 1) if ok), None)
    found_entities = {e for h in top for e in h.entity_ids}
    return {
        "hit": 1.0 if first else 0.0,
        "recall": sum(any(matches(h, s) for h in top) for s in sources) / len(sources) if sources else 0.0,
        "precision": sum(relevant_flags) / len(top) if top else 0.0,
        "rr": 1.0 / first if first else 0.0,
        "entity_recall": len(set(entities) & found_entities) / len(entities) if entities else 0.0,
    }


def average(rows: list[dict]) -> dict:
    return {key: round(mean(r[key] for r in rows), 4) for key in rows[0]} if rows else {}


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(share * (len(ordered) - 1)))] if ordered else 0.0
