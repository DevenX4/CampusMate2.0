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

## Database schema (Phase 2)

41 tables across 8 model modules in `backend/app/models/`, created by Alembic migrations.

| Module | Tables |
|---|---|
| organization | universities, org_units, departments, research_areas |
| campus | buildings, rooms, laboratories, facilities, lab_courses |
| curriculum | programs, semesters, courses, course_offerings, elective_groups, course_prerequisites, catalog_listings, course_shared_listings, grade_bands, grade_band_programs, data_quality_conflicts |
| people | faculty, faculty_research_areas, teaching_assignments |
| content | policies, policy_links, notices, notice_links, faq, faq_links, calendar_events, calendar_event_semesters |
| documents | documents, document_versions, document_entities, document_chunks |
| auth | roles, permissions, role_permissions, users |
| operations | ingestion_jobs, audit_logs |

### Design decisions

| Decision | Why |
|---|---|
| Dataset IDs (`COURSE-2CEIT602`) are the primary keys of domain tables. UUIDs for users, chunks and jobs. BIGINT identity for audit logs | Citations, OKF and evaluation already use the dataset IDs |
| Every fact carries `source_type` plus a foreign key to the exact **document version** and page | A citation keeps pointing at the version it came from, even after a replacement |
| `document_versions` key is `(document_id, version_no)`. `sha256` is unique. A partial unique index allows at most one `active` version | Versioning, duplicate detection and "only the active version is retrieved" are enforced by the database |
| Store what the source states; compute what we derive | Programme totals, a notice's active/expired status, `is_hod` and building-of-a-lab are computed, never stored twice |
| No full-row JSONB copies. JSONB only for semi-structured data (`field_provenance`, contact block, page scope, raw exam strings, job timings) | One representation per fact |
| Courses have no `program_id`. A course's programme is its offering's semester's programme | Avoids two places that could disagree |
| `teaching_assignments` → `course_offerings` composite foreign key | Nobody can teach a course in a semester where it is not offered |
| Notice, FAQ and policy cross-references: foreign key on the owner side, target validated by the seed | Targets span up to 12 entity types, so a single foreign key is impossible |
| No `relationships` table | Edges are derived from foreign keys and link tables (Phase 13). The 1,202-edge dataset file is the test oracle |
| Two circular foreign keys (department ↔ head, document → department) are `DEFERRABLE INITIALLY DEFERRED` and added after table creation | Both sides of a cycle can be inserted in one transaction |
| `audit_logs` is append-only through a trigger | History cannot be rewritten through the application. Users with audit history are deactivated, not deleted |
| Status/type columns use `TEXT` + `CHECK`, not PostgreSQL ENUM | Adding a value later is a one-line migration |
| Vague source dates stay `NULL` (with a note) | "2021-06-01 (exact date not stated)" must not become a fake precise date |

Migration 2 (`drop redundant link tables`) removed `elective_group_options` (identical to `course_offerings.elective_group_id`) and `calendar_event_programs` (always the programmes of the event's semesters). Its downgrade rebuilds both tables from those sources, so it is lossless in both directions.

## Dataset seeding (Phase 3)

`python -m app.seed` runs source → transform → write → validate in one transaction.

| Aspect | Design |
|---|---|
| Input | `data/structured/*.json` (22 tables), `data/registry/` (documents, entity pages) and `data/pdfs/` (verified against registry SHA-256). `relationships.json` is not loaded; it is the Phase 13 test oracle |
| Write order | `Base.metadata.sorted_tables` (parents before children). SQLAlchemy orders INSERTs only by `relationship()`, so the seed never relies on that |
| Idempotency | `INSERT … ON CONFLICT DO UPDATE … WHERE <any column IS DISTINCT FROM new value>`, so a re-run touches 0 rows |
| Write modes | `upsert` for entity tables. `sync` (upsert + delete stale) for link tables and `document_entities`. `insert_only` for `documents` / `document_versions`, whose lifecycle belongs to the admin after bootstrap |
| Provenance | Every row cites `(source_document_id, version 1, page)`. Validated: official/derived facts → official document with a page; synthetic → synthetic document |
| Text repair | UTF-8 decoded as cp1252 (`â€“` for `–`) is repaired: 2 strings, both in the catalog PDF's own text layer |
| Dates | Only exact ISO dates are stored. Approximate registry dates go into `document_versions.notes` |
| Lost-information check | 25 comparisons rebuild every dropped JSON field (e.g. `faculty.courses_taught`, `laboratories.room_number`, notice status as of 2026-09-18) from the database |
| Totals | 2,360 rows in 34 tables. Facts: official 436, derived_official 444, synthetic 286. These reconcile with the dataset audit (145 / 135 / 286) once the 291 catalog-listing and 309 shared-listing sub-records are excluded |

## REST API (Phase 4)

```
HTTP request -> route (app/api/routes)  -> service (app/services) -> SQLAlchemy -> PostgreSQL
                 parameters, status code    queries, rules, DTOs
             <- response schema (app/schemas): the contract, never a raw database row
```

| Decision | Why |
|---|---|
| Services raise domain errors (`NotFoundError`), and `app/api/errors.py` maps them to HTTP | Services stay HTTP-free, so the Phase 16 chat pipeline calls them directly |
| One error envelope `{"error": {code, message, details}}` for 404/422/500 | Clients branch on `error.code`. Internals never leak on 500 |
| `provenance` on every summary and detail, `source_type` on every short reference | The UI and the chat layer can never present synthetic data as official |
| Computed values (programme credits, `is_head_of_department`, a slot's options) are computed in services | Consistent with "store once, compute the rest" |
| `limit` 1–100 (default 20) + `offset`, and `total` in every page | Bounded responses, and the client knows how many pages exist |
| Search escapes `%` and `_` | User text is matched literally. All values are bound parameters, never string-built SQL |
| Only GET endpoints so far | Writes (documents) arrive with authentication and authorization in Phases 5–6 |

## Authentication and authorization (Phase 5)

| Decision | Why |
|---|---|
| Argon2id password hashes (`argon2-cffi`); a dummy verification for unknown emails | Slow, memory-hard hashing; response time doesn't reveal which emails exist |
| Opaque random session token; the database stores only its SHA-256 (`user_sessions`) | A leaked database contains no usable tokens. Logout and deactivation take effect **immediately**, which a stateless JWT cannot do without a denylist |
| Token delivered as an httpOnly, SameSite=Lax cookie (browser) **or** `Authorization: Bearer` (API clients) | JavaScript can't read the cookie, so XSS can't steal it. SameSite blocks cross-site POSTs. `COOKIE_SECURE=true` in production |
| Endpoints require a **permission** (`require("users:manage")`), not a role | Changing who may do what is a data change (`role_permissions`), not a code change |
| Anonymous requests get the `guest` role's permissions | The catalog is public by configuration, not by special-casing |
| Roles and permissions are inserted by migration 3 | The code depends on them, so they are part of the schema version |
| 401 vs 403 | 401 = unknown caller (log in); 403 = known caller without the permission |
| Failed logins answer "Invalid email or password." for every cause | No account enumeration |
| Admins cannot deactivate or demote themselves; deactivation or a password change revokes all of that user's sessions | Prevents lock-out and makes the change immediate |
| No user deletion (deactivate instead) | Audit entries keep pointing at a real account |
| Every login, logout and user change is audited, in the same transaction as the change; passwords and tokens never appear in audit details | An action and its audit record succeed or fail together |
| `X-Request-ID` on every response (generated, or a safe caller-supplied one), stored in audit entries | One ID links a user's error report to the exact log line |

Not yet: login rate limiting and account lockout, and expired-session cleanup. Both are planned for Phase 18 (hardening).

## Document management (Phase 6)

```
upload ─► validate (ext, declared type, %PDF- magic, opens, not encrypted, size) ─► SHA-256 duplicate check
       ─► storage/originals/<sha> (atomic rename) ─► version N (pending) + ingestion job + audit, one transaction
pending ─(Phase 7 ingest)─► ready ─(activate)─► active ─(another version activated)─► superseded ─(rollback)─► active
document: active ⇄ inactive, active/inactive ─► archived ─► active, any ─► deleted (soft, final)
```

| Decision | Why |
|---|---|
| Metadata and file arrive as one multipart form model, validated before any bytes are written | An invalid request stores nothing |
| Size checked from `Content-Length` first, then enforced while streaming to `storage/tmp` | Oversized uploads are cut off. (A reverse proxy limit is still needed in production for chunked uploads.) |
| The content is checked, not just the filename or declared type | A renamed `.txt` or a broken PDF is refused (415/422) |
| Activation moves a pointer; old versions are `superseded`, not deleted | Instant rollback, and citations to old versions stay valid |
| Activation requires `ready` (ingested) or `superseded` | Nothing un-indexed ever becomes the answering version |
| Soft delete only; files stay | The audit trail and past citations remain verifiable |
| Upload IDs are `DOC-<10 hex>` | Unique without a counter race. Seeded documents keep their dataset IDs |
| `storage_root` is a FastAPI dependency | Tests store files in a temporary folder |

## Ingestion (Phase 7)

```
worker ─ claim (FOR UPDATE SKIP LOCKED; re-claim 'processing' jobs past their lease)
       ─ extract (page scope) ─ clean ─ chunk ─ enrich ─ store ┐ one transaction: replace the version's chunks,
                                                                 ┘ version ready/active, job completed, audit
       ─ on error: roll back, job failed (stage, type, trace), ingest version failed, audit
```

| Decision | Why |
|---|---|
| Separate worker process polling a DB job table | Durable (a restart loses nothing), observable (stage + timings), no Redis/Celery needed at this scale |
| Page scope from `document_versions.page_scope` | The 742-page university-wide syllabus contributes only its 14 IT pages |
| Boilerplate = same text at the same top/bottom position on at least 60% of pages | Removes running headers ("Page #", the synthetic banner). The first version removed every repeated line, which deleted field labels and their trust markers. Found by inspecting chunks |
| Structure-aware chunking; lines never split | Official table rows (a course with all its credits) stay intact. Entity blocks (`COURSE-… —`) become their own chunks. Semantic (embedding-based) chunking is deferred until evaluation shows a need |
| Per-chunk `source_type`: official PDF → `official`; synthetic PDF → `synthetic` if any synthetic label (or none), else `derived_official` | A demo document is never an official source, even when it quotes one |
| Chunk metadata: title, document_type, department, academic_year, program_ids, semester_ids (official pages via the semesters' page provenance), labels | Enables metadata filters ("semester VI", "official only") in retrieval |
| Old versions keep their chunks; retrieval uses only active versions of active documents | Rollback is instant |
| `storage/processed/<doc>/v<n>.json` | A human-readable view of exactly what was extracted, for debugging |

Real dataset: 12 documents → 935 chunks in about 20 s. The official catalog is ingested in full (137 pages, 619 chunks). Its other programmes' course lists are genuine official data, and they are exactly the code/name collisions the evaluation set tests.

## Vector retrieval (Phase 8)

```
query ─► PostgreSQL: eligible versions (active version of an active document, + document filters)
      ─► Chroma: vectors WHERE version_key IN eligible AND chunk filters (source_type, semester, programme)
      ─► numpy: exact cosine similarity against every one of them, ties ordered by chunk id
      ─► PostgreSQL: load chunks by id, re-check eligibility, keep similarity order ─► hits with citations
```

| Decision | Why |
|---|---|
| Model `BAAI/bge-small-en-v1.5` (384 dims) run by `fastembed`. It resolves to Qdrant's quantized ONNX export (65 MB) | The BGE model the project specified, on CPU without PyTorch (7 GB RAM machine). Queries get BGE's search instruction prefix; passages don't |
| `Embedder` interface; `HashEmbedder` in tests | The model can be swapped without touching indexing or search; tests never download models or judge quality |
| Embedded text = `title \| section` + chunk | A bare table row still carries which document and which semester |
| PostgreSQL decides eligibility at query time via `version_key` | Activating, deactivating or deleting a document needs no index update. Stale vectors can never answer |
| Vectors written before the chunk commit; stale vectors removed after | A committed chunk always has a vector. A leftover vector is ignored by the eligibility check |
| Collection records model name and dimension; a mismatch refuses to start | Vectors from different models are never mixed. `rebuild-index --reset` re-embeds from PostgreSQL |
| **Exact search** (changed in Phase 16): Chroma stores and filters; numpy scores | Chroma's approximate HNSW search was *measured* to be non-deterministic. The same query in different processes returned different neighbours, and the true #2 neighbour was missing in about half the runs, even on a freshly built index and with `ef_search` = 200. Exact search over about 1,000 vectors costs about 25 ms (p50 of hybrid: 21 → 49 ms) and makes every evaluation reproducible. It grows linearly (about 30 ms per 1,000 chunks); at tens of thousands of chunks an approximate index becomes worth its errors, after its recall is measured |

First observations with the real model (to be *measured* in Phase 9):
- semantic questions work (attendance → FAQ-026 and POLICY-001);
- exact codes fail (`2CEIT78PE7` returns other `2CEIT78PE*` courses);
- number-heavy official table rows rank poorly. This is the motivation for BM25 (Phase 10).

## Retrieval evaluation (Phase 9)

`app/evaluation`: pure metric functions and a runner that accepts any `retrieve(question, k)`, so every mode is measured identically. A chunk is relevant if it comes from a question's required source (same document, page covered by the chunk). Results: `evaluation/results/`.

| Metric | Question it answers |
|---|---|
| Hit@K | Is any correct page in the top K? (Can the model find the evidence at all?) |
| Recall@K | What share of all required pages is in the top K? (Multi-source questions) |
| Precision@K | How much of the top K is relevant? (Noise reaching the model) |
| MRR@10 | How high is the first correct page? |
| Entity recall@K | Do the retrieved chunks mention the expected entities? (Independent signal) |

**Baseline, vector only (BGE-small, 935 chunks, 52 answerable questions):** Hit@1 0.346, Hit@5 0.712, Recall@5 0.357, Precision@5 0.238, MRR 0.495, entity recall@5 0.810, p50 17 ms.

Findings:
1. The mean top similarity is 0.708 for answerable and **0.701 for unanswerable** questions. A similarity threshold cannot detect unanswerable questions, so abstention must rely on grounding checks (Phase 16).
2. Most "semantic" misses retrieve FAQ entries that paraphrase the answer (entity recall 1.0), not the primary policy or facility page the dataset requires. The metric is deliberately strict about *which* source is cited.
3. The official catalog (619 of 935 chunks) crowds out relevant pages for loosely worded questions (EVAL-018).
4. Exact codes are weak for embeddings (Phase 8 observation).

These are the targets for BM25, hybrid fusion and reranking.

## BM25 (Phase 10)

| Decision | Why |
|---|---|
| Okapi BM25 implemented in `app/retrieval/bm25.py` (k1 = 1.5, b = 0.75) | About 60 lines with the formula visible; no dependency |
| Tokenizer: lowercase alphanumeric runs, small stopword list | `2CEIT78PE7` stays one token; `COURSE-2CEIT602` yields `2ceit602`, so a bare code matches the entity ID |
| Indexed text = `title \| section` + chunk (same as the embeddings) | "Semester VI" and document titles are searchable words too |
| In memory, built from PostgreSQL, cached under a fingerprint of the eligible corpus (active version keys, chunk count, newest chunk) | Nothing is persisted, so nothing can drift. Uploads and activation changes show on the next query (rebuild 336 ms; cached check 4 ms) |

**Measured (52 answerable questions, K = 5):**

| mode | Hit@1 | Hit@5 | Recall@5 | MRR | p50 |
|---|---|---|---|---|---|
| vector | **0.346** | **0.712** | 0.357 | **0.495** | 17 ms |
| bm25 | 0.288 | 0.692 | **0.412** | 0.457 | **4 ms** |

The two are complementary. BM25 wins on simple factual (recall 0.54 vs 0.38), semantic and cross-document questions; vector wins on metadata-style (Hit@5 0.71 vs 0.43) and multi-hop questions. Exact code lookups (`2CEIT78PE7`) now rank the right course first. Different failure patterns are the condition under which fusion should help. That is Phase 11's hypothesis to *measure*.

## Hybrid retrieval (Phase 11)

Vector and BM25 each propose 30 candidates, which are merged with Reciprocal Rank Fusion (`fused = Σ 1/(60 + rank)`), and the best K are kept. RRF uses ranks only, so incomparable scores (BM25 about 0–20, cosine 0–1) need no calibration, and agreement between the methods wins. Every hit's `scores` shows `vector_rank` and `bm25_rank`, so the fusion is explainable.

**Measured (52 answerable questions, K = 5):**

| mode | Hit@1 | Hit@5 | Recall@5 | MRR | p50 |
|---|---|---|---|---|---|
| vector | 0.346 | 0.712 | 0.357 | 0.495 | 17 ms |
| bm25 | 0.288 | 0.692 | **0.412** | 0.457 | 4 ms |
| hybrid | **0.442** | **0.769** | 0.410 | **0.581** | 21 ms |

Latencies in this table were measured with Chroma's approximate search. With exact vector search (Phase 16) every quality metric above is identical, and p50 is vector 41 ms and hybrid 46 ms.

**Paired per question (reciprocal rank, versus vector):** hybrid is better on 15, the same on 31 and worse on 6; sign test **p = 0.078**. The improvement is consistent across the averages and the per-question comparison, but with 52 questions it is **not statistically conclusive** at the 0.05 level. It is reported as such, not as proven. Hybrid is the default search mode because it is best on every ranking metric and rarely worse.

## Reranking (Phase 12)

A cross-encoder reads (question, `title | section` + passage) *together* and rescores hybrid's top 30 candidates. `app/retrieval/rerank.py` provides a `Reranker` interface, fastembed ONNX cross-encoders, and a test stand-in. The model is loaded only when `mode=hybrid_rerank` is requested.

**Measured grid (52 answerable questions; CPU):**

| configuration | Hit@1 | Hit@5 | Recall@5 | MRR | p50 | vs hybrid (better/worse, p) |
|---|---|---|---|---|---|---|
| hybrid (no reranker) | 0.442 | 0.769 | 0.410 | 0.581 | **21 ms** | — |
| MiniLM-L6, 600-char passages | 0.481 | 0.827 | 0.468 | 0.617 | 0.9 s | 14 / 14, p = 1.00 |
| MiniLM-L12, 600-char passages | 0.462 | 0.788 | 0.442 | 0.618 | 1.7 s | 14 / 14, p = 1.00 |
| MiniLM-L6, full passages | **0.500** | 0.769 | 0.441 | 0.624 | 3.1 s | 14 / 12, p = 0.85 |
| MiniLM-L12, full passages | 0.481 | **0.827** | **0.477** | **0.644** | 5.2 s | 15 / 12, p = 0.70 |

Re-measured with exact vector search (commit cfa5142): identical quality and paired comparisons; p50 latencies 0.9 s, 1.8 s, 2.2 s and 4.4 s respectively (the machine's load varies between runs).

Against *vector*, L12 is the only configuration with a significant gain (24 better / 9 worse, p = 0.014). Against *hybrid*, however, **no reranker is reliably better**: each helps and hurts about equally often. The earlier gain was hybrid's. A plausible cause is domain mismatch: MS MARCO rerankers learned from web passages, while these chunks are key/value blocks and tables full of codes. Latency grows linearly with candidates and passage length (L12: 4.5 s full vs 1.6 s at 600 characters).

**Decision:** default retrieval stays **hybrid**. `hybrid_rerank` remains available as an opt-in mode using the best-measured configuration (L12, full passages). Future experiments, each one command in the harness: BGE-reranker-base (1 GB), a GPU ONNX runtime, or a domain-tuned reranker.

## OKF knowledge layer (Phase 13)

```
PostgreSQL rows + link tables ─► 29 edge queries (app/knowledge/graph.py) ─► 1,202 typed edges (with trust + citation)
                              └► 16 entity types ─► OKF items (YAML front-matter + labelled Markdown) ─► storage/knowledge/
```

| Decision | Why |
|---|---|
| Edges are *derived* per predicate by SQL over foreign keys and link tables; there is no stored relationships table | One source of truth. The dataset's `relationships.json` becomes the test oracle |
| An edge's trust level and citation come from the row that states it (TEACHES from the synthetic assignment, OFFERED_IN from the official/derived offering; HAS_OPTION from the official slot; BELONGS_TO is official via the syllabus, derived_official for legacy catalog-only courses) | A relationship can be less trustworthy than the entities it connects |
| Per-attribute trust labels: `field_provenance`, then `synthetic_*` fields, then references to synthetic entities, then the row's level | A found bug: the first version printed `[official] synthetic_description` on an official course |
| Files are rebuilt into a staging folder and swapped in (with retries on Windows file locks) | Readers never see a half-written knowledge base, and hand edits cannot survive, by design |

**Validation (in the test suite):**
- all **1,202** dataset edges are reproduced (0 missing, 0 extra, 0 trust-level mismatches);
- all **297** OKF entities are reproduced.

The only difference is the citation of the 2 COORDINATED_BY edges: the faculty record instead of the programmes document, at the same synthetic level. The schema stores a field's trust level (`field_provenance`) but not which document stated that one field.

## Query routing (Phase 14)

```
question ─► resolve entities (IDs, printed codes, names, unambiguous acronyms, "Semester VI of B.Tech", "official")
         ─► ordered rules: automation │ personal │ structured intents │ graph (entity + relation words) │ documents
         ─► evidence: structured facts / graph neighbourhood (2 hops, hubs not expanded) first, then hybrid passages
```

| Decision | Why |
|---|---|
| Deterministic rules, not an LLM agent | Explainable (`reasons`), repeatable, testable, and 27 ms |
| Structured intents: course facts, a semester's courses, programme summary, elective-slot options, grade for marks | Exact tabular facts come with their official citation (e.g. syllabus p.15), with no paraphrasing |
| Documents always appended as supporting evidence | A routing miss costs precision, not the answer |
| An acronym is used only if it names exactly one entity and is not a department code | A found bug: "IT" in "B.Tech IT" matched four "Industrial Training"-style course names |
| Arbitrary aggregates ("faculty with more than four courses") are **not** handled; they fall back to documents | That needs text-to-SQL (an LLM plus a read-only, whitelisted query layer), a deliberate future step |

**Measured (same 52 questions; re-measured with exact vector search, commit cfa5142):** routed Hit@1 **0.615** (hybrid 0.442), MRR **0.710** (0.581), Hit@5 0.846, p50 52 ms. Against hybrid it is better on 11, the same on 39, worse on 2 (p = 0.022). With approximate search it was MRR 0.707, 11/38/3, p = 0.057. It is strongest on structured (Hit@5 0.857 vs vector 0.429) and multi-hop questions (MRR 0.875).

**Caveat:** the rules were written while reading these same questions, so this is an **in-sample, optimistic** estimate. A held-out question set is needed for an unbiased number.

## Generation providers (Phase 15)

```
evidence ─► context blocks [1..n] (kind, trust level, label, text) ─► GenerationProvider.generate() ─► answer citing [n]
                                                                      ├── ExtractiveProvider (no model; the default)
                                                                      └── OpenAICompatibleProvider ─HTTP─► Ollama / llama.cpp / LM Studio / hosted API
```

| Decision | Why |
|---|---|
| A `Protocol` with `generate()` and `check()`; one factory (`generation/runtime.py`) | Only the factory knows the concrete classes. Changing the model means changing configuration, not code |
| One provider for every OpenAI-compatible server, instead of one class per model or vendor | The same code serves local runtimes and hosted APIs. No model-specific logic, apart from dropping a leading `<think>` block, which is a convention shared by reasoning models |
| The model runs in its own process (HTTP), not inside the API | A model crash or out-of-memory error cannot take the API down; models can be swapped freely; no fragile CUDA Python builds |
| The prompt lives in one provider-independent module (`generation/prompt.py`) | Numbered sources with trust labels, five short rules, and the exact abstain sentence |
| The extractive provider is the default | CampusMate works end to end with no download. It cannot invent anything, and it is the baseline an SLM must beat |
| Temperature 0 | The same evidence gives the same answer, so answers are reproducible and can be evaluated |
| The API key is a `SecretStr`, sent only as a header to `GENERATION_BASE_URL`. Error messages drop any `user:password@`. A warning is logged when the server is not local | Keeps secrets out of logs and makes data leaving the machine visible |
| `GENERATION_MODEL` is checked with a field validator, not a model validator | Found in testing: a model validator's error message printed the whole settings input, including `DB_PASSWORD` |

Two bugs found while testing the extractive provider:
- The sentence splitter broke names after "Dr." and initials.
- An official graph item quoted a relationship to a *synthetic* lab without a label. Each quoted piece is now labelled by what it says, not only by its block.

Model choice: [slm-evaluation.md](slm-evaluation.md).

## Chat pipeline (Phase 16)

```
POST /chat/query ─► router (route, intents) ─► personal / automation: "not supported yet" (no search, no model)
                 ─► evidence ─► context builder ─► generation provider ─► grounding check ─┬─ passed ─► answer
                                                                                            └─ failed ─► extractive answer from the same sources
                                                                                                         (or abstain)
                 ─► chat_queries row (question, answer, sources, grounding result, timings) ─► response with query_id
```

| Decision | Why |
|---|---|
| Context builder: at most 8 sources, 3 of them graph items, and 6,000 characters in total. Order: structured, graph, documents. Duplicates are removed. A question that asks for "official" drops synthetic sources | Fits a small model's 4,096-token window with room for the rules and the answer. The exact facts come first |
| Grounding check without a model (`chat/grounding.py`): citations exist; every number and code occurs in the sources; every capitalised name occurs in the sources | Wrong numbers and invented names are the most harmful and the most checkable errors. A false positive only costs a fallback to the extractive answer |
| A rejected or failed generation falls back to the extractive answer, not to an error | The extractive answer is grounded by construction. The user gets the sources' own words instead of nothing. `answer_type` says so |
| A refusal in the model's own words becomes the one canonical abstain sentence | Abstentions are recognisable in the UI and in evaluation |
| An undisclosed synthetic source gets a notice appended (a fix, not a rejection) | Synthetic information is never presented as official, whatever the model wrote |
| Personal and automation routes answer "not supported yet" without searching | Searching documents for "my marks" can only produce a misleading answer |
| Every exchange is stored (`chat_queries`); one rating per answer (`chat_feedback`, upsert with `ON CONFLICT`) | Answers can be audited, feedback points at the exact sources used, and real questions can become evaluation data. Query ids are random UUIDs, and someone else's query looks exactly like a missing one (404) |
| Answer evaluation (`python -m app.evaluation answers`) reports: answered rate, fact recall (numbers and codes of the expected answer), term recall, whether a required source is cited, correct abstention on unanswerable questions, fallbacks, latency | The same run for each provider makes the SLM comparison measurable |

**Baseline: the extractive provider, no model (58 questions, commit 353d253, `evaluation/results/ANSWERS.md`)**

| answered (A–G) | fact recall | term recall | cites a required source | unanswerable abstained (H) | fallbacks | p50 |
|---|---|---|---|---|---|---|
| 0.654 | 0.335 | 0.320 | 0.481 | 4 / 6 | 0 | 62 ms |

(At cfa5142, before quoted graph clauses kept their subject: fact recall 0.327, required source cited 0.462.)

It answers 88% of simple factual and 100% of exact-lexical questions, but only 14% of semantic ones: it abstains wherever the question's words differ from the source's. It never falls back, because copied text always passes the grounding check. On 2 of the 6 unanswerable questions it quoted a loosely matching sentence instead of abstaining. These are the gaps an SLM is expected to close; the same run with a model will show whether it does.

Limits of the grounding check: a false statement made only of words found in the sources ("closed" vs "open", or a number from the wrong row) passes. Catching that needs a model as a judge, or human review.

Found by the answer evaluation and fixed:
- the name check read the letters inside `2CEIT78PE7` as names;
- BM25 ties and Chroma's approximate search made evidence differ between processes (see Phase 8).

## Frontend (Phase 17)

```
browser ── http://127.0.0.1:5173 ──► Vite (static UI) ── /api/* ──► FastAPI :8000 ──► PostgreSQL / Chroma
            one origin: httpOnly session cookie, no CORS, no token in JavaScript
```

| Decision | Why |
|---|---|
| Vite + React 19 + TypeScript (strict) + Tailwind 4; tokens from the Stitch `DESIGN.md` (warm neutrals, one sapphire accent) | The stack the project specified. Design tokens in one `@theme` block |
| One API module (`src/api/client.ts`), same-origin requests with the cookie | The browser never sees PostgreSQL, Chroma or the session token. The backend's error format becomes one `ApiError` |
| Route guards read `GET /auth/me` permissions; the server checks every request again | The UI hides what a role cannot do; it is never the security boundary |
| No facts in the UI: everything shown comes from API responses. The example questions are only questions | The Stitch mockups contained wrong facts; see below |
| Answers rendered as React text; `[n]` becomes a button that opens source *n* | No HTML from answers ever reaches the DOM (tested with an `<img onerror>` answer) |
| Trust levels on every source; synthetic data in amber, never in the official sapphire; a warning under any answer that uses it | Synthetic information must never look official |
| An upload requires the admin to choose "official" or "synthetic"; there is no default | The label decides how every answer from that file is presented |
| A document panel lists its versions: status, file, size, pages, SHA-256. It offers "Activate" only for `ready` and `superseded` versions (a rollback), and a new-version upload | Mirrors the backend's rules. A new version replaces the active one automatically once ingested |
| Fonts self-hosted (`@fontsource`); no external requests at runtime | Works offline, and nothing leaks to third parties |

**Stitch mock facts not carried over:**
- 2CEIT601–604 were mapped to the wrong courses. The syllabus has 601 THEORY OF COMPUTATION and 602 ARTIFICIAL INTELLIGENCE.
- "Charusat / GTU" names other universities.
- "Revision v3.2", "Section 3.4 … 16 credits" and the "Authentic" badge were invented.
- "ChromaDB v0.5", "text-embedding-3-small", "PyMuPDF / OCR" and "overlap 120 tokens / 512" misdescribe the real pipeline.
- The document counts were invented.
- A quotation was attributed to Gandhi, but that attribution is disputed.

The admin page describes the pipeline as implemented, and shows counts from `GET /documents/stats`.

**Testing:**
- Vitest + Testing Library (17 tests) with a fetch mock that exercises the real client, routing and auth.
- The whole flow was also checked against the running API through the Vite proxy, with curl: login cookie, `/me`, a chat answer, feedback, a 403 for a student on documents, and logout.
- Headless Edge, driven over the DevTools protocol, took screenshots of the login page, the assistant (desktop and 390 px mobile), the admin page and a document's versions panel.

Found by the headless browser and fixed:
- Chromium's `scrollIntoView` returns a Promise. An effect returned it, React called it as a clean-up and the page went blank. jsdom has no `scrollIntoView`, so the unit tests could not see it; a regression test now simulates Chromium.
- An extractive answer quoted a neighbouring course's relationship without its subject.

## Full integration (Phase 18)

```
chroma run :8001 ◄── HTTP ──┬── API (uvicorn :8000) ◄── /api proxy ── Vite UI :5173 ◄── browser
                            └── ingestion worker ──► PostgreSQL (jobs, chunks, chat log)
```

*Superseded in Phase 19: the Chroma server has an unfixed pre-authentication remote-code-execution flaw (CVE-2026-45829). Ingestion now runs as a thread of the API process, which is the only user of the embedded store. See "Security hardening (Phase 19)".*

**Found by running the processes together:** the API and the worker each opened the embedded Chroma store (`PersistentClient`). After the worker indexed a new document, the API's next question failed with `chromadb InternalError: Error finding id`. Each process keeps its own in-memory view of the index, and the embedded store is not safe across processes. It never showed up before, because the worker and the API had not run at the same time. Now both use one Chroma server (`CHROMA_URL`). The embedded store remains for tests and single-process tools, and the worker warns when it starts without `CHROMA_URL`. Exact search now fetches the eligible vectors over HTTP: about 60 ms instead of 25 ms.

**Scenarios:**

| | How | What it proves |
|---|---|---|
| `tests/test_e2e.py` (in the test suite) | HTTP through the real app, the real ingestion pipeline, the full seeded dataset (test embedder, extractive generation) | SQL facts cite syllabus p.15. Graph answers label synthetic lab data. Personal questions are unsupported; unknown questions abstain. A student cannot upload. For an uploaded document: not answered before ingestion, answered after it, gone once deactivated. A new version replaces the fact after ingestion (the old one answers meanwhile), and a rollback brings the old fact back. Feedback is stored |
| `scripts/e2e_live.py` (against the running application) | Four real processes (Chroma server, API, worker with BGE, Vite proxy) and real logins | The same lifecycle with the real embedding model and a separate worker process. Ingestion took about 2 s, the answer 0.22 s; it passed twice in a row with no errors |

Not yet integrated: the SLM. The pipeline runs with the extractive provider until a model is chosen (see [slm-evaluation.md](slm-evaluation.md)). Switching is configuration only, and the same scenarios and the answer evaluation will then run with the model.

## Security hardening (Phase 19)

Full review: [security.md](security.md). What was added, and why:

| Change | Why |
|---|---|
| Login throttling from the audit log: 5 failures per account, 30 per client IP, in 15 minutes, checked before the password | Stops password guessing and spraying without Redis. During a lockout the right password is refused too, so guessing learns nothing |
| 20 questions per minute per user, counted from `chat_queries` | Generation can take seconds of a local model; one user must not starve the others |
| Security headers on every response; CSP `default-src 'none'` and `no-store` on the API | The API serves only JSON: nothing may frame it, script it or cache personal answers |
| JSON bodies ≤ 64 KB, enforced by Content-Length and while reading (chunked bodies too) | Without it, one huge body is parsed into memory. Found in testing: the limit had to be the innermost middleware, or FastAPI turned it into a generic 400 |
| `COOKIE_SECURE` mandatory in production; API docs off in production | Safe defaults cannot be forgotten |
| `purge-sessions`, plus a per-user purge at each login | Dead sessions do not accumulate |
| An ID in the question that does not exist → abstain | Found by the hallucination traps: "Is LAB-IT-011 open on Sundays?" was answered from an unrelated lab notice |
| A PDF line wrap never splits a quoted sentence | Found by the hallucination traps: "... are not / an actual Ganpat University schedule" was quoted as "an actual Ganpat University schedule" |
| **Ingestion inside the API process; no Chroma server** | The dependency audit found CVE-2026-45829 (pre-authentication remote code execution in chromadb's server, no fix) |

**Hallucination tests:** all 23 trap questions of `negative_questions.json` run through the whole pipeline with every real PDF ingested (`tests/test_hallucination.py`), and also in `python -m app.evaluation answers`. The rule: abstain, or answer only from sources, with demo data labelled; never cite synthetic data for an "official" question; never answer about an entity that does not exist.

## Phases

0 audit ✅ · 1 foundation ✅ · 2 PostgreSQL ✅ · 3 seed ✅ · 4 REST catalog ✅ · 5 auth ✅ · 6 documents ✅ · 7 ingestion ✅ · 8 vector ✅ · 9 evaluation ✅ · 10 BM25 ✅ · 11 hybrid ✅ · 12 rerank ✅ · 13 OKF ✅ · 14 router ✅ · 15 generation ✅ (model choice pending) · 16 chat API ✅ · 17 frontend ✅ · 18 integration ✅ (SLM pending) · 19 testing + hardening ✅ · 20 Docker · 21 deployment evaluation
