# CampusMate Development Dataset — GUNI IT (v1.0)

A small, connected, traceable dataset for building and testing CampusMate (Hybrid RAG + OKF + SQL). It has two kinds of content:

* **Official core.** Everything about the B.Tech IT and M.Tech IT curricula comes from two Ganpat University PDFs, with a page-level citation for every value.
* **Synthetic companion.** The department, people, rooms, policies, calendar, notices and FAQ are invented so the architecture can be tested. **None of it is a Ganpat University fact.** Every synthetic PDF says so on page 1 and in each page header.

Generated 2026-09-18. The demo academic year is **2026-2027**. The official syllabus effective year is **2021-2022**.

## Source-type labels (used on every record, edge, OKF item and PDF table row)

| Label | Meaning | Example |
|---|---|---|
| `official` | Stated in a GUNI PDF (page cited) | 2CEIT602 ARTIFICIAL INTELLIGENCE, 4 credits, syllabus p.15 |
| `derived_official` | Computed from or restructured out of a GUNI PDF | B.Tech IT total 174 credits; elective option credits inherited from the slot |
| `synthetic` | Invented for testing | FAC-IT-002 teaches 2CEIT602; LAB-IT-001 in room DA-301 |

Course records mix official fields with synthetic enrichment, so each one carries `field_provenance`. Official `prerequisites` and `description` stay `null`. Synthetic values live in fields that say so: `synthetic_prerequisites`, `synthetic_description`, `faculty_ids`, `lab_ids`.

## Package layout

```
CampusMate_Dataset/
├── official/                      the two authoritative GUNI PDFs + extraction
│   ├── GUNI_BTech_IT_Syllabus.pdf     (DOC-OFFICIAL-SYLLABUS-001, 742 pp; IT on pp.10-18, 104-108)
│   ├── GUNI_Course_Catalog.pdf        (DOC-OFFICIAL-CATALOG-001, 137 pp; NAAC 1.1.3 list)
│   └── extracted/official_inventory.json, GAP_ANALYSIS.md
├── synthetic/
│   ├── pdf/          10 separate RAG documents (never merged)
│   └── structured/   canonical JSON (+ csv/) for DB loading — 22 tables + relationships.json
├── knowledge/OKF_style/   297 Markdown knowledge items (YAML front-matter + prose), index.json, relationships.jsonl
├── registry/         document_registry.json/.csv, entity_index.json (entity → every representation)
├── sql/              schema.sql (PostgreSQL, FKs + CHECKs), seed.sql
├── evaluation/       evaluation_questions.json (58), negative_questions.json (23)
├── audit/            audit_report.json/.md (37 checks, all PASS)
└── tools/            generator scripts (re-run to rebuild everything)
```

`synthetic/structured/` is the canonical load set. Despite the folder name, it also holds the official curriculum records (`courses`, `semesters`, `programs`, …), and each record is labelled.

## Entities and IDs (one entity → many representations)

| Entity | IDs | Count | Source |
|---|---|---|---|
| University / org units | UNIV-GUNI-001, SCHOOL-FET-001, COLLEGE-UVPCE-001 | 3 | official |
| Department | DEPT-IT-001 | 1 | synthetic |
| Programmes | PROG-BTECH-IT-001, PROG-MTECH-IT-001 | 2 | official (+ synthetic dept link) |
| Semesters | SEM-BTECH-IT-01…08, SEM-MTECH-IT-01…04 | 12 | official |
| Courses | COURSE-<official code>, e.g. COURSE-2CEIT602 | 116 | official / derived_official |
| Elective groups | EGRP-BTECH-IT-06-ELECTIVE-III … | 18 | official |
| Course offerings | OFF-BTECH-IT-06-2CEIT602 … | 112 | official / derived_official |
| Grade bands | GRADE-BAND-01…07 | 7 | official |
| Faculty | FAC-IT-001…020 | 20 | synthetic |
| Teaching assignments | TA-SYN-001… | 90 | synthetic |
| Research areas | RA-IT-001…010 | 10 | synthetic |
| Laboratories | LAB-IT-001…010 | 10 | synthetic |
| Facilities | FCL-IT-001…010 | 10 | synthetic |
| Buildings / rooms | BLDG-DEMO-A/B, ROOM-DA-301 … | 2 / 31 | synthetic |
| Prerequisite edges | PREREQ-SYN-001…024 | 24 | synthetic |
| Policies | POLICY-001…011 (numbers CM-SYN-POL-0xx) | 11 | synthetic |
| Calendar events | CAL-2026-27-001…025 | 25 | synthetic |
| Notices | NOTICE-001…020 | 20 | synthetic |
| FAQ | FAQ-001…032 | 32 | synthetic |
| Data-quality conflicts | DQ-CONFLICT-001…010 | 10 | derived_official |
| Documents | DOC-OFFICIAL-*, DOC-DEPT-PROFILE-001 … DOC-FAQ-001 | 12 | — |

No course codes were invented. Faculty IDs use `FAC-`, so facilities use `FCL-` to avoid a collision. The same ID appears in the JSON, the SQL row, the OKF file, the PDF text (with its page recorded in `registry/entity_index.json`) and the official PDF page. For example, `COURSE-2CEIT602` resolves to courses.json, `courses` row, `knowledge/OKF_style/courses/COURSE-2CEIT602.md`, Course_Catalog.pdf p.10, syllabus p.15, and catalog pp.2 and 41.

Relationship predicates (1,202 edges in `relationships.json`, each with its own source_type):
`HAS_ORG_UNIT, HAS_DEPARTMENT, OFFERS, HOSTED_BY, CONTAINS, OFFERED_IN, BELONGS_TO, HAS_ELECTIVE_GROUP, HAS_OPTION, WORKS_IN, HEADS, TEACHES, RESEARCHES, HAS_OFFICE, REQUIRES, HAS_LAB, PRACTICALS_IN, MANAGED_BY, LOCATED_IN, IN_BUILDING, HAS_FACILITY, HAS_RESEARCH_AREA, APPLIES_TO, GOVERNS, OWNED_BY, MENTIONS, SUPERSEDES, REFERENCES, COORDINATED_BY`.

## How the dataset supports the CampusMate architecture

| Capability | What in the dataset exercises it |
|---|---|
| **OKF** | One Markdown file per entity. The front-matter carries id, type, department, program, semester, academic_year, source_type, source_document/page, field_provenance, rendered_in, version, status, last_updated and typed `relationships` (forward and inverse). |
| **Hybrid RAG** | The PDFs mix prose (overviews, policy clauses, notice text, FAQ answers) for dense retrieval with tables of exact identifiers. |
| **BM25 / lexical** | Course codes (2CEIT78PE7), entity IDs, policy numbers (CM-SYN-POL-004 §3), room numbers (DA-302), notice IDs and dates are kept verbatim, never paraphrased. Near-duplicates test disambiguation: CLOUD COMPUTING (2CEIT603 vs 3CEIT203), NLP (2CEIT78PE7 vs 3CEIT307), HIGH PERFORMANCE COMPUTING, DEEP LEARNING. |
| **Metadata filtering** | Every item carries source_type, program, semester, department, academic_year, status (active/expired/superseded), category and dates. Evaluation category D needs these filters, for example "only official facts" or "active notices". |
| **Reranking** | Distractors are built in: the superseded NOTICE-005 against NOTICE-008, expired notices, same-name courses across B.Tech and M.Tech, and code collisions (2HS102 SEMINAR vs LINEAR ALGEBRA). |
| **SQL / structured** | `sql/schema.sql` with 33 tables and real FKs. `seed.sql` loads cleanly into PostgreSQL 16. 14 evaluation questions include a `reference_sql` that the audit ran successfully. |
| **Provenance & citations** | Official records cite document and page and are re-checked against the PDF text by the audit. Synthetic PDFs record the page of each entity, and policies cite clause numbers. |
| **Admin upload / replace / delete** | Each document is an independent unit in `document_registry` with sha256, version, status, effective dates and the entity IDs it describes. `document_entities` and `document_chunks` in SQL use `ON DELETE CASCADE`, so one document can be deactivated, replaced or re-indexed without touching the others. Replacing the synthetic Faculty_Directory with real data only touches `DOC-FACULTY-001`, `faculty` and `teaching_assignments`. |
| **Evaluation** | 58 questions: A simple (8), B lexical (8), C semantic (7), D metadata (7), E multi-hop (8), F cross-document (7), G SQL (7), H unanswerable (6). There are also 23 negative/hallucination traps (real contacts, "official" versions of synthetic policies, nonexistent IDs, out-of-scope years, code collisions). Every question has expected_answer, required_sources (doc + page), expected_entities, retrieval_type, difficulty, answerable and expected_source_types. |

## Swapping in real data later

Keep the IDs and schema, and replace one synthetic document group at a time. Mark the old registry row `superseded`, load the new structured file, regenerate its OKF items and PDF, and re-index. The official curriculum layer (courses, semesters, programmes) is already real and stays as it is. When GUNI publishes a newer syllabus, add a new version of `DOC-OFFICIAL-SYLLABUS-*` and version the offerings by effective year.

## Rebuilding

`tools/` contains the generator (Python 3.11, reportlab, pypdf, pyyaml). The sequence is: `parse_official.py` → `catalog_lookup.py` → `build_all.py` → `finalize.py`. The scripts use absolute paths from the build environment, so adjust `OUT` and the source paths before re-running. The audit expects a local PostgreSQL on socket `/var/tmp/cmpg:5433`.
