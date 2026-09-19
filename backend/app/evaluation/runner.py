"""Run the evaluation questions through a retriever and summarise the metrics.

The runner only needs a function `retrieve(question, k) -> list[Retrieved]`, so every
retrieval mode (vector, bm25, hybrid, hybrid + reranker) is measured the same way.
"""

import json
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from app.evaluation.metrics import Retrieved, Source, average, percentile, question_metrics, sign_test_p

Retriever = Callable[[str, int], list[Retrieved]]
K_VALUES = (1, 3, 5, 10)


@dataclass
class Question:
    question_id: str
    text: str
    category: str
    answerable: bool
    sources: list[Source]
    entities: list[str]


def load_questions(path: Path) -> list[Question]:
    data = json.loads(path.read_text(encoding="utf-8"))["questions"]
    return [
        Question(q["question_id"], q["question"], q["category"], q["answerable"],
                 [Source(s["document_id"], s.get("page")) for s in q["required_sources"]],
                 q["expected_entities"])
        for q in data
    ]


def evaluate(questions: list[Question], retrieve: Retriever, k_values=K_VALUES) -> dict:
    per_question, latencies = [], []
    for q in questions:
        started = time.perf_counter()
        hits = retrieve(q.text, max(k_values))
        latencies.append((time.perf_counter() - started) * 1000)
        per_question.append({
            "question_id": q.question_id, "category": q.category, "answerable": q.answerable,
            "top_score": hits[0].score if hits else None,
            # String keys ("5"), because results are stored as JSON.
            "metrics": {str(k): question_metrics(hits, q.sources, q.entities, k) for k in k_values}
            if q.answerable else None,
            "top_hits": [f"{h.document_id} p.{h.page_start}" for h in hits[:5]],
        })

    answerable = [r for r in per_question if r["answerable"]]
    by_category = defaultdict(list)
    for r in answerable:
        by_category[r["category"]].append(r)
    top_scores = {flag: [r["top_score"] for r in per_question if r["answerable"] == flag and r["top_score"] is not None]
                  for flag in (True, False)}
    return {
        "overall": {str(k): average([r["metrics"][str(k)] for r in answerable]) for k in k_values},
        "by_category": {cat: {str(k): average([r["metrics"][str(k)] for r in rows]) for k in k_values}
                        for cat, rows in sorted(by_category.items())},
        "latency_ms": {"mean": round(mean(latencies), 1), "p50": round(percentile(latencies, 0.5), 1),
                       "p95": round(percentile(latencies, 0.95), 1)},
        # For abstention later: do unanswerable questions score lower than answerable ones?
        "top_score": {"answerable_mean": _mean(top_scores[True]), "unanswerable_mean": _mean(top_scores[False])},
        "questions": {"answerable": len(answerable), "unanswerable": len(per_question) - len(answerable)},
        "per_question": per_question,
    }


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 4) if values else None


def summary_table(results: dict[str, dict], k: int = 5) -> str:
    """Markdown comparison of every stored mode at cut-off k."""
    lines = [f"| mode | Hit@1 | Hit@{k} | Recall@{k} | Precision@{k} | MRR@10 | Entity recall@{k} | p50 ms |",
             "|---|---|---|---|---|---|---|---|"]
    for mode, result in results.items():
        o, ms = result["overall"], result["latency_ms"]
        lines.append(f"| {mode} | {o['1']['hit']:.3f} | {o[str(k)]['hit']:.3f} | {o[str(k)]['recall']:.3f} | "
                     f"{o[str(k)]['precision']:.3f} | {o['10']['rr']:.3f} | {o[str(k)]['entity_recall']:.3f} | "
                     f"{ms['p50']} |")
    return "\n".join(lines)


def category_table(result: dict, k: int = 5) -> str:
    lines = [f"| category | Hit@{k} | Recall@{k} | MRR@10 | Entity recall@{k} |", "|---|---|---|---|---|"]
    for category, metrics in result["by_category"].items():
        m, m10 = metrics[str(k)], metrics["10"]
        lines.append(f"| {category} | {m['hit']:.3f} | {m['recall']:.3f} | {m10['rr']:.3f} | {m['entity_recall']:.3f} |")
    return "\n".join(lines)


def paired_comparison(results: dict[str, dict], baseline: str, metric: str = "rr", k: str = "10") -> str:
    """Per question: is each mode better, equal or worse than the baseline? Averages can hide
    losses; this shows them, with a sign-test p-value for "could this be chance?"."""
    base = {r["question_id"]: r["metrics"][k][metric] for r in results[baseline]["per_question"] if r["answerable"]}
    lines = [f"| mode vs {baseline} ({metric}@{k}) | better | same | worse | sign-test p |", "|---|---|---|---|---|"]
    for mode, result in results.items():
        if mode == baseline:
            continue
        other = {r["question_id"]: r["metrics"][k][metric] for r in result["per_question"] if r["answerable"]}
        wins = sum(other[q] > base[q] for q in base)
        losses = sum(other[q] < base[q] for q in base)
        lines.append(f"| {mode} | {wins} | {len(base) - wins - losses} | {losses} | {sign_test_p(wins, losses):.3f} |")
    return "\n".join(lines)
