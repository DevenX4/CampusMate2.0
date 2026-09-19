"""Checks that the generated knowledge reproduces the dataset's own knowledge files.

The dataset ships 1,202 relationship edges and 297 OKF items produced by its generator.
Our OKF is derived from the normalised PostgreSQL schema instead, so matching them proves
that normalisation lost no relationship and no entity.
"""

import json
from collections import Counter
from pathlib import Path

from app.knowledge.graph import Edge


def _records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))


def compare_edges(edges: list[Edge], fixture_path: Path) -> dict:
    want = {(r["subject_id"], r["predicate"], r["object_id"]): r for r in _records(fixture_path)}
    got = {(e.subject_id, e.predicate, e.object_id): e for e in edges}
    both = set(want) & set(got)
    return {
        "fixture": len(want), "generated": len(got),
        "missing": sorted(set(want) - set(got)),
        "extra": sorted(set(got) - set(want)),
        "source_type_mismatches": sorted(k for k in both if want[k]["source_type"] != got[k].source_type),
        # Informational: same edge and trust level, but a different (equally valid) citation.
        "citation_differences": dict(Counter(
            k[1] for k in both
            if (want[k]["source_document"], want[k]["source_page"]) != (got[k].source_document_id, got[k].source_page))),
    }


def compare_items(items: list[dict], fixture_index: Path) -> dict:
    want = {i["id"] for i in json.loads(fixture_index.read_text(encoding="utf-8"))["items"]}
    got = {i["id"] for i in items}
    return {"fixture": len(want), "generated": len(got),
            "missing": sorted(want - got), "extra": sorted(got - want)}
