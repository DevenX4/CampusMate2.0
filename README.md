# CampusMate AI

An AI-powered campus assistant for Ganpat University's IT programmes. It combines structured university data (PostgreSQL) with document retrieval (hybrid RAG) and gives grounded answers with citations. Official, derived-official and synthetic information are always labelled as such.

**Status: Phase 4 (read-only catalog API).** A 41-table PostgreSQL schema (Alembic), an idempotent validated seed (2,360 rows plus 12 PDFs), and a REST API for departments, programmes, semesters, courses and faculty. Every item in the API carries its provenance. There is no authentication, document management, RAG or frontend yet. See [docs/architecture.md](docs/architecture.md) for the target design and the phase plan.

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
