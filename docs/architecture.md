# CampusMate architecture

## Responsibilities

| Layer | Responsibility |
|---|---|
| PostgreSQL | Structured source of truth: entities, documents, versions, chunks, jobs, users, audit |
| OKF | Knowledge representation **generated from** PostgreSQL. Never hand-edited |
| RAG (vector + BM25 → RRF → reranker) | Retrieval over document chunks |
| Query router | Deterministic choice of SQL / OKF / RAG per question |
| SLM / LLM | Writes the final grounded answer. Replaceable behind a provider interface |
| FastAPI | The only way in: business logic, auth, authorization, validation |
| React | UI only. No secrets, no DB access, no authorization decisions |

## Data ownership

| Data | Owner | Derived copies (rebuildable) |
|---|---|---|
| Entities (courses, faculty, …) | PostgreSQL | OKF files, relationship edges |
| Document bytes | `storage/originals/` (by SHA-256) | — |
| Document metadata, versions, ingestion jobs | PostgreSQL | — |
| Chunk text + metadata (incl. per-chunk `source_type`) | PostgreSQL `document_chunks` | Chroma vectors, BM25 index |

## Known dataset constraints (from the Phase 0 audit)

- The official syllabus has teaching/exam schemes only, with **no unit-wise content**. Such questions must abstain or be answered from clearly labelled synthetic data.
- The syllabus PDF is university-wide. B.Tech IT is on pp.10–18 and M.Tech IT on pp.104–108, so ingestion must be page-scoped.
- Curriculum facts are tables. Exact curriculum questions go to SQL, not RAG.
- Synthetic PDFs contain some official fields, so `source_type` is tracked per chunk.
- Course codes are not globally unique across programmes (DQ-CONFLICT-001…010).
- The Stitch mockups contain false sample facts (e.g. 2CEIT602 is ARTIFICIAL INTELLIGENCE, not Cloud Computing). The UI must show only API data.

## Phases

0 audit ✅ · 1 foundation ✅ · 2 PostgreSQL · 3 seed · 4 REST catalog · 5 auth · 6 documents · 7 ingestion · 8 vector · 9 evaluation · 10 BM25 · 11 hybrid · 12 rerank · 13 OKF · 14 router · 15 generation · 16 chat API · 17 frontend · 18 hardening · 19 testing · 20 Docker · 21 deployment prep
