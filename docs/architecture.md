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

43 tables across 8 model modules in `backend/app/models/`, created by Alembic migrations.

| Module | Tables |
|---|---|
| organization | universities, org_units, departments, research_areas |
| campus | buildings, rooms, laboratories, facilities, lab_courses |
| curriculum | programs, semesters, courses, course_offerings, elective_groups, elective_group_options, course_prerequisites, catalog_listings, course_shared_listings, grade_bands, grade_band_programs, data_quality_conflicts |
| people | faculty, faculty_research_areas, teaching_assignments |
| content | policies, policy_links, notices, notice_links, faq, faq_links, calendar_events, calendar_event_programs, calendar_event_semesters |
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

## Phases

0 audit ✅ · 1 foundation ✅ · 2 PostgreSQL ✅ · 3 seed · 4 REST catalog · 5 auth · 6 documents · 7 ingestion · 8 vector · 9 evaluation · 10 BM25 · 11 hybrid · 12 rerank · 13 OKF · 14 router · 15 generation · 16 chat API · 17 frontend · 18 hardening · 19 testing · 20 Docker · 21 deployment prep
