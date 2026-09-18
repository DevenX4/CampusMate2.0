# CampusMate AI

An AI-powered campus assistant for Ganpat University's IT programmes. It combines structured university data (PostgreSQL) with document retrieval (hybrid RAG) and gives grounded answers with citations. Official, derived-official and synthetic information are always labelled as such.

**Status: Phase 1 (project foundation).** A FastAPI skeleton with configuration, logging and a health endpoint. There is no database layer, authentication, RAG or frontend yet. See [docs/architecture.md](docs/architecture.md) for the target design and the phase plan.

## Repository layout

```
backend/            FastAPI application (Python)
  app/core/         configuration (config.py) and logging (logging.py)
  app/api/routes/   HTTP endpoints
  app/schemas/      Pydantic request/response models
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

### Database role (one-time, needed from Phase 2)

The application connects as the low-privilege role `campusmate_app`, never as `postgres`. Create the role and the database once, using the same password you put in `.env`:

```bash
psql -U postgres -h localhost -p 5432 -v app_password='YOUR_DB_PASSWORD' -f backend/scripts/create_local_db.sql
```

## Run

```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

- Health check: http://127.0.0.1:8000/api/v1/system/health → `{"status":"ok"}`
- Interactive API docs: http://127.0.0.1:8000/docs

## Test

```bash
cd backend
.venv/Scripts/python -m pytest -v
```

## Configuration

All settings come from environment variables or `.env` (see `.env.example`). Real environment variables override `.env`. Switching to Docker or cloud PostgreSQL later means changing `DB_*` values, not code. The app refuses to start if a required value such as `DB_PASSWORD` is missing.
