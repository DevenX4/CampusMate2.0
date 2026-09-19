"""Evaluation command line.

    python -m app.evaluation retrieval --mode vector
    python -m app.evaluation answers [--label NAME]

`retrieval` runs the 58 dataset questions through one retrieval mode against the development
database and vector index, writes evaluation/results/retrieval_<mode>.json (every question's
metrics and top hits), and regenerates evaluation/results/RETRIEVAL.md comparing all stored modes.

`answers` runs them through the whole chat pipeline with the configured generation provider
(GENERATION_*), writes evaluation/results/answers_<label>.json and regenerates ANSWERS.md.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.config import REPO_ROOT, get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.chat.pipeline import answer_question
from app.evaluation.answers import evaluate_answers, report
from app.evaluation.metrics import Retrieved
from app.generation.runtime import get_generator
from app.evaluation.runner import category_table, evaluate, load_questions, paired_comparison, summary_table
from app.models.documents import DocumentChunk
from app.retrieval.rerank import CrossEncoderReranker
from app.retrieval.runtime import get_bm25_cache, get_indexer
from app.retrieval.search import bm25_search, hybrid_search, reranked_search, vector_search
from app.routing.entities import EntityResolver
from app.routing.evidence import RetrievalDeps, gather
from app.routing.router import decide

QUESTIONS = REPO_ROOT / "evaluation" / "datasets" / "evaluation_questions.json"
RESULTS = REPO_ROOT / "evaluation" / "results"
MODES = ("vector", "bm25", "hybrid", "hybrid_rerank", "routed")  # extended as retrieval modes are added


def to_retrieved(hits) -> list[Retrieved]:
    return [Retrieved(h.citation.document_id, h.citation.page_start, h.citation.page_end,
                      tuple(h.entity_ids), h.score) for h in hits]


ROUTES: dict[str, str] = {}  # question -> route, filled by the routed retriever


def make_retriever(mode: str, db, reranker_model: str | None = None):
    if mode == "bm25":
        cache = get_bm25_cache()
        return lambda question, k: to_retrieved(bm25_search(db, cache, question, k))
    indexer = get_indexer()
    if mode == "vector":
        return lambda question, k: to_retrieved(vector_search(db, indexer.embedder, indexer.index, question, k))
    if mode == "hybrid":
        cache = get_bm25_cache()
        return lambda question, k: to_retrieved(hybrid_search(db, indexer.embedder, indexer.index, cache, question, k))
    if mode == "routed":
        resolver, deps = EntityResolver(db), RetrievalDeps(indexer.embedder, indexer.index, get_bm25_cache())

        def routed(question: str, k: int) -> list[Retrieved]:
            decision = decide(question, resolver.resolve(question))
            ROUTES[question] = decision.route
            evidence = gather(db, question, decision, deps, k_documents=k)
            return [Retrieved(e.citation.document_id, e.citation.page_start, e.citation.page_end,
                              tuple(e.entity_ids), e.score) for e in evidence][:k]
        return routed
    if mode == "hybrid_rerank":
        cache, settings = get_bm25_cache(), get_settings()
        reranker = CrossEncoderReranker(reranker_model or settings.reranker_model, settings.model_cache_dir)
        return lambda question, k: to_retrieved(reranked_search(
            db, indexer.embedder, indexer.index, cache, reranker, question, k,
            candidates=settings.rerank_candidates, max_chars=settings.rerank_max_chars))
    raise ValueError(f"unknown mode {mode}")


def git_commit() -> str | None:
    try:
        # "-dirty" marks results measured with uncommitted code, which the commit alone would misstate.
        return subprocess.run(["git", "describe", "--always", "--dirty"], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def questions_by_id() -> dict:
    return {q.question_id: q for q in load_questions(QUESTIONS)}


def route_table(result: dict, questions: dict) -> str:
    counts: dict[str, dict[str, int]] = {}
    for qid, route in result["routes"].items():
        row = counts.setdefault(questions[qid].category, {})
        row[route] = row.get(route, 0) + 1
    routes = sorted({r for row in counts.values() for r in row})
    lines = ["Routes chosen per category:", "", "| category | " + " | ".join(routes) + " |",
             "|---|" + "---|" * len(routes)]
    lines += [f"| {cat} | " + " | ".join(str(row.get(r, 0)) for r in routes) + " |" for cat, row in sorted(counts.items())]
    return "\n".join(lines) + "\n"


def write_report() -> None:
    results = {path.stem.removeprefix("retrieval_"): json.loads(path.read_text(encoding="utf-8"))
               for path in sorted(RESULTS.glob("retrieval_*.json"))}
    parts = ["# Retrieval evaluation", "",
             "Generated by `python -m app.evaluation retrieval --mode <mode>`. Answerable questions only "
             "(categories A-G); H (unanswerable) is summarised by its top score.", "",
             "## Overall (K = 5)", "", summary_table(results), ""]
    if "vector" in results and len(results) > 1:
        parts += ["## Paired comparison against the vector baseline", "",
                  "Per question, on reciprocal rank (how high the first correct page appears). "
                  "A sign-test p below 0.05 means the difference is unlikely to be chance.", "",
                  paired_comparison(results, "vector"), ""]
    if "hybrid" in results and len(results) > 2:
        parts += ["## Paired comparison against hybrid", "",
                  "Does anything improve on hybrid retrieval itself? (reciprocal rank)", "",
                  paired_comparison(results, "hybrid"), ""]
    for mode, result in results.items():
        run = result["run"]
        parts += [f"## {mode}", "",
                  f"Commit `{run['commit']}` · {run['timestamp']} · model `{run['embedding_model']}` · "
                  f"{run['chunks']} chunks · {result['questions']['answerable']} answerable questions", "",
                  category_table(result), "",
                  *([route_table(result, questions_by_id())] if "routes" in result else []),
                  f"Mean top score: answerable {result['top_score']['answerable_mean']}, "
                  f"unanswerable {result['top_score']['unanswerable_mean']}.", ""]
    (RESULTS / "RETRIEVAL.md").write_text("\n".join(parts), encoding="utf-8")


def run_answers(label: str | None) -> int:
    settings, generator, indexer = get_settings(), get_generator(), get_indexer()
    print(generator.check())
    with SessionLocal() as db:
        deps = RetrievalDeps(indexer.embedder, indexer.index, get_bm25_cache())
        result = evaluate_answers(load_questions(QUESTIONS), lambda question: answer_question(
            db, question, deps, generator, settings.generation_max_tokens, settings.generation_temperature))
    label = label or re.sub(r"[^A-Za-z0-9_.-]+", "-", generator.model)
    result["run"] = {"label": label, "provider": generator.name, "model": generator.model, "commit": git_commit(),
                     "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                     "max_tokens": settings.generation_max_tokens, "temperature": settings.generation_temperature}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"answers_{label}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    results = {path.stem.removeprefix("answers_"): json.loads(path.read_text(encoding="utf-8"))
               for path in sorted(RESULTS.glob("answers_*.json"))}
    (RESULTS / "ANSWERS.md").write_text(report(results), encoding="utf-8")
    s = result["summary"]
    print(f"{label}: answered {s['answerable']['answered']} | fact recall {s['answerable']['fact_recall']} | "
          f"term recall {s['answerable']['term_recall']} | cites required {s['answerable']['cites_required']} | "
          f"H abstained {s['unanswerable']['abstained']} | fallbacks {s['fallbacks']} | p50 {s['latency_ms']['p50']} ms")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    retrieval = commands.add_parser("retrieval", help="evaluate one retrieval mode")
    retrieval.add_argument("--mode", choices=MODES, default="vector")
    retrieval.add_argument("--reranker-model", default=None, help="for hybrid_rerank (default: RERANKER_MODEL)")
    retrieval.add_argument("--label", default=None, help="name of the result, e.g. to compare two rerankers")
    answers = commands.add_parser("answers", help="evaluate answers with the configured generation provider")
    answers.add_argument("--label", default=None, help="name of the result (default: the model name)")
    args = parser.parse_args(argv)
    settings = get_settings()
    setup_logging("WARNING")
    if args.command == "answers":
        return run_answers(args.label)

    questions = load_questions(QUESTIONS)
    with SessionLocal() as db:
        result = evaluate(questions, make_retriever(args.mode, db, args.reranker_model))
        chunks = db.scalar(select(func.count()).select_from(DocumentChunk))
    label = args.label or args.mode
    if ROUTES:  # routing decisions per question, for the report
        text_of = {q.text: q for q in questions}
        result["routes"] = {text_of[t].question_id: r for t, r in ROUTES.items()}
    result["run"] = {"mode": args.mode, "label": label, "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
                     "reranker_model": (args.reranker_model or settings.reranker_model) if args.mode == "hybrid_rerank" else None,
                     "rerank_candidates": settings.rerank_candidates, "rerank_max_chars": settings.rerank_max_chars,
                     "commit": git_commit(), "embedding_model": settings.embedding_model, "chunks": chunks,
                     "dataset": str(QUESTIONS.relative_to(REPO_ROOT))}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"retrieval_{label}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    write_report()
    o = result["overall"]
    print(f"{label}: Hit@1 {o['1']['hit']:.3f} | Hit@5 {o['5']['hit']:.3f} | Recall@5 {o['5']['recall']:.3f} | "
          f"MRR {o['10']['rr']:.3f} | EntityRecall@5 {o['5']['entity_recall']:.3f} | p50 {result['latency_ms']['p50']} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
