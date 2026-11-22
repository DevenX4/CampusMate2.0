"""
Hybrid RAG Chat Route — Production Ready, Local & Online Compatible.
Exposes:
  POST /api/v1/chat/bypass   — Hybrid RAG chat (BM25 + Chroma Dense + RRF + LLM/Extractive + Grounding)
  POST /api/v1/chat/hybrid   — Dedicated Hybrid RAG endpoint
  POST /api/v1/chat/stream   — Server-Sent Events (SSE) real-time pipeline & token stream
  POST /api/v1/chat/ingest   — Ingest document into BM25 + ChromaDB + disk JSON
"""
import hashlib
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.assistant import CampusAssistant
from app.retrieval.hybrid_engine import HybridRAGEngine

logger = logging.getLogger("campusmate")
router = APIRouter(prefix="/chat", tags=["chat-hybrid"])
UPLOAD_ROOT = (Path(__file__).resolve().parents[5] / "server" / "uploads" / "knowledge").resolve()


# ── Models ────────────────────────────────────────────────────────────────────
class BypassRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


class SimpleSource(BaseModel):
    title: str
    content: str
    score: Optional[float] = None
    cited: Optional[bool] = True
    ref: Optional[int] = None
    source_type: Optional[str] = None


class BypassResponse(BaseModel):
    answer: str
    sources: List[SimpleSource]
    route: str
    answer_type: str
    provider: Optional[str] = None
    conversation_id: Optional[str] = None
    timings_ms: Optional[Dict[str, int]] = None
    query_id: Optional[str] = None
    grounding: Optional[Dict[str, Any]] = None
    clarification_required: bool = False
    options: List[str] = []
    links: List[Dict[str, str]] = []


class IngestRequest(BaseModel):
    file_path: str
    original_name: str
    source_type: str = "official"


class IngestResponse(BaseModel):
    status: str
    chunks: int
    doc_id: str


def _chunk_pdf_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return [clean] if clean else []
    chunks: List[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            split_at = clean.rfind(". ", start + max_chars // 2, end)
            if split_at == -1:
                split_at = clean.rfind(" ", start + max_chars // 2, end)
            if split_at != -1:
                end = split_at + 1
        piece = clean[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


# ── Chat endpoints ────────────────────────────────────────────────────────────
@router.post("/bypass", response_model=BypassResponse)
def chat_bypass(body: BypassRequest):
    engine = HybridRAGEngine.get_instance()
    result = engine.answer_query(
        body.question,
        conversation_id=body.conversation_id,
        history=body.history,
        model=body.model,
    )
    return BypassResponse(
        answer=result["answer"],
        sources=[SimpleSource(**s) for s in result.get("sources", [])],
        route=result.get("route", "hybrid_rag"),
        answer_type=result.get("answer_type", "answered"),
        provider=result.get("provider", "CampusMate Hybrid Engine"),
        conversation_id=result.get("conversation_id"),
        timings_ms=result.get("timings_ms"),
        query_id=result.get("query_id"),
        grounding=result.get("grounding"),
    )


@router.post("/hybrid", response_model=BypassResponse)
def chat_hybrid(body: BypassRequest):
    assistant = CampusAssistant.get_instance()
    if not assistant.groq.available:
        return chat_bypass(body)
    return BypassResponse(**assistant.answer(body.question, body.conversation_id, body.history))


@router.post("/stream")
def chat_stream(body: BypassRequest):
    """Stream live pipeline stages, token deltas, and the final cited response over SSE."""
    assistant = CampusAssistant.get_instance()
    engine = HybridRAGEngine.get_instance()

    def event_generator():
        try:
            source = (
                assistant.stream(body.question, body.conversation_id, body.history)
                if assistant.groq.available
                else engine.answer_query_stream(
                    body.question,
                    conversation_id=body.conversation_id,
                    history=body.history,
                    model=body.model,
                )
            )
            for item in source:
                ev = item.get("event", "message")
                data = json.dumps(item.get("data", {}))
                yield f"event: {ev}\ndata: {data}\n\n"
        except Exception as exc:
            logger.error("SSE stream error: %s", exc, exc_info=True)
            err_payload = json.dumps({"message": str(exc)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Ingest webhook ────────────────────────────────────────────────────────────
def _do_ingest(file_path: str, original_name: str, source_type: str) -> int:
    path = Path(file_path)
    if not path.exists():
        logger.error("Ingest: file not found: %s", file_path)
        return 0

    d_id = hashlib.md5(original_name.encode()).hexdigest()[:16]
    logger.info("Ingesting %s (doc_id=%s)", original_name, d_id)

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        new_chunks = []
        engine = HybridRAGEngine.get_instance()

        for i, page in enumerate(reader.pages):
            txt = page.extract_text()
            if not txt or len(txt.strip()) <= 20:
                continue
            page_num = i + 1
            sub_chunks = _chunk_pdf_text(txt, max_chars=1200, overlap=150)
            for sub_idx, chunk_text in enumerate(sub_chunks):
                c_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{d_id}:{page_num}:{sub_idx}"))
                new_chunks.append(
                    {
                        "id": c_id,
                        "title": f"{original_name} (Page {page_num})",
                        "category": "uploaded_document",
                        "source_type": source_type,
                        "text": chunk_text,
                        "metadata": {
                            "doc_id": d_id,
                            "title": f"{original_name} (Page {page_num})",
                            "page": page_num,
                            "chunk_index": sub_idx,
                            "source_type": source_type,
                        },
                    }
                )

        if new_chunks:
            added = engine.add_chunks_and_persist(new_chunks)
            logger.info("Persisted %d chunks from %s into BM25 + ChromaDB + KB JSON", added, original_name)
            return added
    except Exception as e:
        logger.error("Error during ingestion of %s: %s", original_name, e)
        return 0
    return 0


@router.post("/ingest", response_model=IngestResponse)
def ingest_file(body: IngestRequest, background_tasks: BackgroundTasks):
    # Only files the admin upload route saved may enter the knowledge base.
    if not Path(body.file_path).resolve().is_relative_to(UPLOAD_ROOT):
        raise HTTPException(status_code=400, detail="file_path must be inside the knowledge upload folder")
    d_id = hashlib.md5(body.original_name.encode()).hexdigest()[:16]
    background_tasks.add_task(_do_ingest, body.file_path, body.original_name, body.source_type)
    logger.info("Ingest queued for %s", body.original_name)
    return IngestResponse(status="queued", chunks=0, doc_id=d_id)
