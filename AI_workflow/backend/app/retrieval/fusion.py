"""Reciprocal Rank Fusion (Cormack, Clarke & Buettcher, SIGIR 2009).

BM25 scores (0 to about 20) and cosine similarities (0 to 1) cannot be added directly, so RRF
uses only each list's RANKS:

    fused(d) = sum over lists L containing d of 1 / (k + rank_L(d))

With k = 60, a chunk ranked #3 in BOTH lists (2/63 = 0.0317) beats one ranked #1 in only one
list (1/61 = 0.0164): agreement between two independent methods is strong evidence.
"""

from collections import defaultdict

RRF_K = 60


def reciprocal_rank_fusion(rankings: dict[str, list[str]], k: int = RRF_K) -> list[tuple[str, float, dict[str, int]]]:
    """rankings: {method: [chunk ids, best first]} -> [(chunk id, fused score, {method: rank})],
    best first. Ties keep the order in which chunks were first seen."""
    fused: dict[str, float] = defaultdict(float)
    ranks: dict[str, dict[str, int]] = defaultdict(dict)
    for method, ids in rankings.items():
        for rank, chunk_id in enumerate(ids, start=1):
            fused[chunk_id] += 1.0 / (k + rank)
            ranks[chunk_id][method] = rank
    order = sorted(fused, key=lambda chunk_id: fused[chunk_id], reverse=True)
    return [(chunk_id, fused[chunk_id], ranks[chunk_id]) for chunk_id in order]
