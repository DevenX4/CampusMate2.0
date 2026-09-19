# CampusMate AI

An AI-powered campus assistant for Ganpat University's IT programmes. It combines structured university data (PostgreSQL) with document retrieval (hybrid RAG) and gives grounded answers with citations. Official, derived-official and synthetic information are always labelled as such.

**Status: Phase 12 (reranking, measured).** A 41-table PostgreSQL schema (Alembic), an idempotent validated seed (2,360 rows plus 12 PDFs), and a REST API for departments, programmes, semesters, courses and faculty. Every item in the API carries its provenance. Login sessions, roles and permissions, user management and an audit-log API are in place. Admins can upload, version, activate, deactivate, archive and delete documents. A durable worker turns each document version into structure-aware chunks with provenance. Chunks are embedded with BGE-small into a Chroma index and searchable at `/api/v1/search`. There is no answer generation or frontend yet. See [docs/architecture.md](docs/architecture.md) for the target design and the phase plan.

## Repository layout

```
backend/            FastAPI application (Python)
  app/core/         configuration (config.py), logging (logging.py), database session (db.py)
  app/models/       SQLAlchemy models = the database schema, one file per domain
  app/seed/         dataset loader: source -> transform -> write -> validate (python -m app.seed)
  app/services/     business logic and queries, no HTTP (catalog services, storage)
  app/api/routes/   HTTP endpoints (thin: parameters in, service call, response schema out)
  app/api/errors.py one JSON error format for 404 / 422 / 500
  app/schemas/      Pydantic request/response models
  migrations/       Alembic migrations (versions/ holds one file per schema change)
  scripts/          one-off setup scripts (e.g. create_local_db.sql)
  tests/
data/
  structured/       canonical dataset tables (JSON + CSV); seeded into PostgreSQL in Phase 3
  knowledge/        existing OKF-style items (reference; regenerated from PostgreSQL in Phase 13)
  registry/         document registry (IDs, SHA-256, versions)
  pdfs/             official + synthetic PDFs. NOT in Git; verify with data/pdfs.sha256
  reference/        read-only material: legacy SQL, audit, generator scripts, gap analysis
evaluation/datasets/  evaluation questions (58) and negative/hallucination questions (23)
frontend/stitch-reference/  Stitch UI mockups: visual reference only. Their sample data is NOT factual.
storage/            runtime files (uploads, processed, vector index, tmp). NOT in Git
docs/               architecture and decisions
```

## Data trust model

| `source_type` | Meaning |
|---|---|
| `official` | Stated in a Ganpat University PDF (document + page cited) |
| `derived_official` | Computed or restructured from an official PDF, with a link back to it |
| `synthetic` | Invented for development and testing. **Never a Ganpat University fact** |

## Prerequisites

- Python 3.11+ (developed on 3.13)
- PostgreSQL (developed on native PostgreSQL 18 on port 5432). Not used until Phase 2.
- Git

## Setup (Windows, Git Bash)

```bash
cd CampusMate

# 1. Configuration: copy the template, then edit .env (at least DB_PASSWORD)
cp .env.example .env

# 2. Python virtual environment + dependencies
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

In PowerShell, use `copy .env.example .env` and `.venv\Scripts\python` instead.

To reproduce the exact tested versions: `.venv/Scripts/python -m pip install -r requirements.lock && .venv/Scripts/python -m pip install -e . --no-deps`

### PDFs (not in Git)

Put the 12 PDFs under `data/pdfs/` with the paths listed in `data/pdfs.sha256`, then verify them:

```bash
cd data/pdfs && sha256sum -c ../pdfs.sha256
```

### Database setup (one-time)

The application connects as the low-privilege role `campusmate_app`, never as `postgres`. The script creates that role plus two databases: `campusmate` (development) and `campusmate_test` (used only by pytest). It reads the password from `.env`, so the role and the app always agree. Run it from the repo root as the `postgres` superuser. This is the only time the superuser is needed.

```bash
# Git Bash
psql -U postgres -h localhost -p 5432      -v app_password="$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)"      -f backend/scripts/create_local_db.sql
```

```powershell
# PowerShell
$pw = ((Select-String -Path .env -Pattern '^DB_PASSWORD=').Line -split '=', 2)[1]
psql -U postgres -h localhost -p 5432 -v app_password="$pw" -f backend/scripts/create_local_db.sql
```

Then create the schema:

```bash
cd backend
.venv/Scripts/alembic upgrade head      # apply all migrations
.venv/Scripts/alembic current           # shows the current revision, marked (head)
```

Then load the dataset:

```bash
.venv/Scripts/python -m app.seed --dry-run   # validate everything, then roll back
.venv/Scripts/python -m app.seed             # load and commit
```

The seed is **idempotent**: run it again and it reports `inserted 0, updated 0, deleted 0`. It also **repairs drift**: if a seeded value was changed in the database, the next run restores it. Everything happens in one transaction, and if any validation fails, nothing is written. It also copies the 12 PDFs (after checking their SHA-256) into `storage/originals/<2 hex>/<sha256>.pdf`.

Validation checks:
- exact row counts;
- official facts cite an official document and page, and synthetic facts cite synthetic documents;
- every cross-reference resolves;
- record version labels match version 1;
- no garbled text remains (2 known strings are repaired and listed);
- every field the schema deliberately does not store (because it repeats other data) can be rebuilt from the database and equals the original JSON. So normalization lost nothing.

## Run

```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

- Health (liveness): http://127.0.0.1:8000/api/v1/system/health → `{"status":"ok"}`
- Readiness: http://127.0.0.1:8000/api/v1/system/ready → 200 `"status":"ready"` when PostgreSQL is reachable **and** migrated; otherwise 503 with the reason

## Accounts and login

Create the first admin (the password is asked for at a hidden prompt):

```bash
cd backend
.venv/Scripts/python -m app.accounts create --email admin@campusmate-demo.example --role admin --name "Admin"
```

| Endpoint | Who |
|---|---|
| `POST /api/v1/auth/login` `{"email", "password"}` | anyone. Sets an httpOnly session cookie and also returns `access_token` |
| `POST /api/v1/auth/logout` | revokes the session immediately |
| `GET /api/v1/auth/me` | logged in. Returns the user and their permissions |
| `GET/POST /api/v1/users`, `PATCH /api/v1/users/{id}` | `users:manage` (admin) |
| `GET /api/v1/audit-logs` | `audit:read` (admin) |

In `/docs`, click **Authorize** and paste the `access_token` to call protected endpoints. The catalog stays public: visitors who are not logged in act as the `guest` role, which has `catalog:read`.

| Role | Permissions |
|---|---|
| guest | catalog:read |
| student | + chat:use |
| faculty | + documents:read |
| admin | + documents:manage, ingestion:manage, users:manage, audit:read |

## Document management

| Endpoint | Who |
|---|---|
| `GET /api/v1/documents` (`q`, `document_type`, `source_type`, `status`, `department_id`), `/documents/stats`, `/documents/{id}`, `/documents/{id}/versions` | `documents:read` (faculty, admin) |
| `POST /api/v1/documents` (multipart: `file` + `title`, `document_type`, `source_type`, …) | `documents:manage` (admin) |
| `POST /documents/{id}/versions` (replace), `POST /documents/{id}/versions/{v}/activate` (activate or roll back) | admin |
| `POST /documents/{id}/activate`, `/deactivate`, `/archive`, `DELETE /documents/{id}` (soft), `POST /documents/{id}/reindex` | admin |
| `GET /documents/{id}/versions/{v}/file` (original download) | admin |

```bash
curl -b jar.txt -F "file=@rules.pdf;type=application/pdf" -F "title=Exam rules"      -F "document_type=examination" -F "source_type=synthetic" http://127.0.0.1:8000/api/v1/documents
```

Uploads are checked for extension, declared type, **content** (`%PDF-` and it must open), size (`MAX_UPLOAD_MB`) and duplicates (SHA-256). They are stored as `storage/originals/<2 hex>/<sha256>.pdf`, never under the client's filename, and each upload queues an ingestion job.

## Ingestion

```bash
cd backend
.venv/Scripts/python -m app.ingestion queue-missing   # once, after seeding: queue the 12 dataset documents
.venv/Scripts/python -m app.ingestion worker          # keep running in a second terminal
.venv/Scripts/python -m app.ingestion worker --once   # or: process what is waiting, then exit
```

Pipeline per job: **extract** (only the version's page scope, e.g. syllabus pp.10–18, 104–108) → **clean** (repair garbled text, remove running headers and footers) → **chunk** (new chunk at each entity or numbered heading or semester page; lines are never split; at most `CHUNK_MAX_CHARS`) → **enrich** (page range, section, entity IDs, programme/semester, trust level) → **store** (one transaction). A successful ingest activates a newer version automatically. A failure never touches the version that is currently answering.

| Endpoint | Who |
|---|---|
| `GET /api/v1/ingestion/jobs` (`status`, `document_id`), `/ingestion/jobs/{id}` (stage, per-stage timings, error) | `ingestion:manage` (admin) |
| `POST /api/v1/ingestion/jobs/{id}/retry` (failed jobs) | admin |

## Search (vector retrieval)

```bash
cd backend
.venv/Scripts/python -m app.retrieval rebuild-index            # embed all chunks (first run downloads ~65 MB)
.venv/Scripts/python -m app.retrieval search "minimum attendance" -k 3
curl -b jar.txt "http://127.0.0.1:8000/api/v1/search?q=minimum%20attendance&source_type=official"
```

`GET /api/v1/search` (`chat:use`) takes `q`, `mode` (`hybrid` (default), `vector`, `bm25`, or the opt-in `hybrid_rerank`: a cross-encoder, about 5 s per query on CPU), `k`, `source_type` (repeatable), `document_type`, `program_id` and `semester_id`. Each hit has `text`, `score`, `source_type`, `entity_ids` and a `citation` (document, version, pages, section). The worker indexes new versions automatically. `rebuild-index --reset` recreates the whole index from PostgreSQL.

## Evaluation

```bash
cd backend
.venv/Scripts/python -m app.evaluation retrieval --mode vector
```

This runs the 58 dataset questions through one retrieval mode and writes `evaluation/results/retrieval_<mode>.json` (per-question metrics and top hits). It also regenerates `evaluation/results/RETRIEVAL.md`, which compares every stored mode on Hit@K, Recall@K, Precision@K, MRR, entity recall, latency and a per-category breakdown.

## Catalog API (read-only)

| Endpoint | Notes |
|---|---|
| `GET /api/v1/departments`, `/departments/{id}` | profile, head, contact (synthetic) |
| `GET /api/v1/programs`, `/programs/{id}` | semesters; semester count and total credits are computed |
| `GET /api/v1/semesters/{id}` | regular courses and elective/audit/open slots with their options |
| `GET /api/v1/courses` | `q` (code/name search), `code`, `program_id`, `semester_id`, `course_type`, `limit` (1–100), `offset` |
| `GET /api/v1/courses/{id}` | offerings and credits, teaching staff, labs, prerequisites, catalog listings |
| `GET /api/v1/faculty`, `/faculty/{id}` | `department_id`, `q`; detail includes teaching and research areas |

```bash
curl "http://127.0.0.1:8000/api/v1/courses?q=artificial"
curl "http://127.0.0.1:8000/api/v1/semesters/SEM-BTECH-IT-06"
curl "http://127.0.0.1:8000/api/v1/courses/COURSE-2CEIT602"
```

Every entity in a response carries `provenance` (`source_type`, `document_id`, `version_no`, `page`, `section`) or, in short references, `source_type`. Clients must show `synthetic` data as demo data.

Errors always look like `{"error": {"code": "not_found", "message": "...", "details": null}}`:
- 404 for an unknown ID or URL;
- 422 for invalid parameters, with `details` naming each bad parameter;
- 500 with a generic message (the details are logged on the server only).
- Interactive API docs: http://127.0.0.1:8000/docs

## Test

```bash
cd backend
.venv/Scripts/python -m pytest -v -rs
```

Database tests run against `campusmate_test`, which they rebuild from the migrations. They are skipped, with the reason shown, if that database is not reachable.

## Changing the database schema

1. Edit or add a model in `backend/app/models/`.
2. `.venv/Scripts/alembic revision --autogenerate -m "short description"` generates a migration by comparing the models with the database.
3. **Review the generated file.** Autogenerate misses some things. In the initial migration it silently omitted the two circular foreign keys, and triggers are never detected. Fix it by hand where needed.
4. `.venv/Scripts/alembic upgrade head`, then `.venv/Scripts/alembic check` (it must report "No new upgrade operations detected").
5. `.venv/Scripts/alembic downgrade -1` must also work. The test suite checks the full down/up round trip.

## Configuration

All settings come from environment variables or `.env` (see `.env.example`). Real environment variables override `.env`. Switching to Docker or cloud PostgreSQL later means changing `DB_*` values, not code. The app refuses to start if a required value such as `DB_PASSWORD` is missing.
