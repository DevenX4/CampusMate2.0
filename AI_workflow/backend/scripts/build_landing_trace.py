"""Record real runs of the answer pipeline for the "How it works" animation and the project facts.

Run from AI_workflow/backend:  python scripts/build_landing_trace.py
It makes one routing call and one answer call to Groq per example question.
"""

import json
import logging
import re
import sys
import time
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
logging.disable(logging.WARNING)

from app.assistant.service import _FACT, CampusAssistant  # noqa: E402
from app.retrieval.hybrid_engine import _expand_aliases  # noqa: E402

DATA_DIR = BACKEND.parent / "data" / "structured"
OUTPUT_DIR = BACKEND.parents[1] / "src" / "data"
EXAMPLES = [
    ("How many credits does Artificial Intelligence carry?", "English"),
    ("bhai attendance kitni chahiye exam ke liye?", "Hinglish"),
    ("Which lab is used for Database practicals?", "English"),
]


def short_title(title):
    return re.sub(r"\s+", " ", title).strip()[:58]


def preview(answer, limit=270):
    text = re.sub(r"[*#`]", "", answer)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.M)
    text = re.sub(r"\s*\n+\s*", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("] "))
    return (cut[:end + 1] if end > 90 else cut.rsplit(" ", 1)[0]).strip()


def main():
    assistant = CampusAssistant.get_instance()
    if not assistant.groq.available:
        raise SystemExit("GROQ_API_KEY is not set")
    engine = assistant.engine
    runs = []
    for question, language in EXAMPLES:
        plan = assistant._plan(question, [])
        query = _expand_aliases(plan["search_queries"][0])
        started = time.perf_counter()
        bm25 = engine.bm25_search(query, k=3)
        vector = engine.vector_search(query, k=3)
        search_ms = round((time.perf_counter() - started) * 1000)
        fused = assistant._retrieve(plan["search_queries"])[:3]
        time.sleep(7)
        result = assistant.answer(question)
        answer = preview(result["answer"])
        checked = sorted({f for f in _FACT.findall(re.sub(r"\[\d+\]", " ", answer))})[:4]
        runs.append({
            "question": question,
            "language": language,
            "intent": plan["intent"],
            "search_query": plan["search_queries"][0],
            "bm25": [{"title": short_title(engine.chunk_by_id[i]["title"]), "score": round(s, 2)} for i, s in bm25],
            "vector": [{"title": short_title(engine.chunk_by_id[i]["title"]), "score": round(s, 2)} for i, s in vector],
            "fused": [{"title": short_title(r["title"]), "score": r["score"]} for r in fused],
            "search_ms": search_ms,
            "answer": answer,
            "provider": result.get("provider", ""),
            "checked_facts": checked,
            "grounded": bool((result.get("grounding") or {}).get("passed")),
            "sources": [short_title(s["title"]) for s in result.get("sources", [])][:3],
            "total_ms": (result.get("timings_ms") or {}).get("total"),
        })
        print("recorded:", question, "| grounded:", runs[-1]["grounded"], flush=True)
        time.sleep(8)

    tables, total, source_types = {}, 0, Counter()
    for path in sorted(DATA_DIR.glob("*.json")):
        if path.stem == "relationships":
            continue
        records = json.loads(path.read_text(encoding="utf-8")).get("records", [])
        tables[path.stem] = len(records)
        total += len(records)
        source_types.update(str(r.get("source_type", "unknown")) for r in records if isinstance(r, dict))
    kb = engine.chunks
    facts = {
        "datasets": len(tables),
        "structured_records": total,
        "indexed_records": len(kb),
        "vectors": engine.chroma_collection.count(),
        "tables": tables,
        "source_types": dict(source_types),
        "indexed_by_category": dict(Counter(c.get("category") for c in kb)),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pipeline_trace.json").write_text(json.dumps(runs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "project_facts.json").write_text(json.dumps(facts, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(facts))


if __name__ == "__main__":
    main()
