# CampusMate AI

An AI-powered campus assistant for Ganpat University's IT programmes. It combines structured university data (PostgreSQL) with document retrieval (hybrid RAG) and gives grounded answers with citations. Official, derived-official and synthetic information are always labelled as such.

**Status: all 21 phases done, local only; pending decisions: the SLM, the vector store, building the Docker images. See [docs/deployment-evaluation.md](docs/deployment-evaluation.md).** A 41-table PostgreSQL schema (Alembic), an idempotent validated seed (2,360 rows plus 12 PDFs), and a REST API for departments, programmes, semesters, courses and faculty. Every item in the API carries its provenance. Login sessions, roles and permissions, user management and an audit-log API are in place. Admins can upload, version, activate, deactivate, archive and delete documents. A durable worker turns each document version into structure-aware chunks with provenance. Chunks are embedded with BGE-small into a Chroma index. Hybrid (BM25 + vector) search is at `/api/v1/search`, and a knowledge graph (OKF) is generated from PostgreSQL. A deterministic router gathers cited evidence for a question (`/api/v1/route`), and a replaceable generation provider writes answers: no model yet, see [docs/slm-evaluation.md](docs/slm-evaluation.md). `POST /api/v1/chat/query` answers with citations, and every answer is checked against its sources before it is returned. **There is no UI at the moment:** the React frontend was removed on 2026-09-19, to be rebuilt from scratch (it is in the Git history, commit `c2e2a2d`). Use the API through http://127.0.0.1:8000/docs. Demo logins for the API: `admin` / `admin@123` and `student` / `student@123` (local only). See [docs/architecture.md](docs/architecture.md) for the target design and the phase plan.

## Quick start (Windows)

Needs Python 3.11+, Node.js 20+, PostgreSQL running on port 5432, the 12 PDFs in `data/pdfs/`, and `backend\.venv` (see Setup below).

```powershell
cd "D:\MP 7th Sem\CampusMate"
.\scripts\setup-local.ps1 -DemoAccounts
.\scripts\start-local.ps1
```

Then open http://127.0.0.1:8000/docs (the API's interactive documentation) and log in with `POST /api/v1/auth/login` using a demo account:

| Username | Password | Can |
|---|---|---|
| `admin` | `admin@123` | everything: documents, ingestion, users, audit log, chat |
| `student` | `student@123` | chat and the catalogue |

The demo accounts are for a local demo only: their passwords are public. `python -m app.accounts demo` (which `-DemoAccounts` runs) refuses to create them when `APP_ENV=production`, and the API refuses their logins there. For a real admin, use `-AdminEmail you@example.org` instead (a hidden prompt asks for its password).

`setup-local.ps1` runs once, and is safe to re-run. It asks once for the `postgres` superuser's password and uses it only to create the low-privilege role `campusmate_app` and its two databases. The role's password comes from `DB_PASSWORD` in `.env`. The script then creates the schema, loads the dataset, queues the 12 PDFs for ingestion and creates the demo accounts (`-DemoAccounts`, safe to repeat: it resets their passwords) or a real admin (`-AdminEmail`, prompts for the password; first run only).

`start-local.ps1` opens the **CampusMate API** window, then http://127.0.0.1:8000/docs. Close the window to stop. The API ingests the queued PDFs by itself during the first minute or two (`GET /api/v1/ingestion/jobs` shows the progress).

To add another account: `backend\.venv\Scripts\python -m app.accounts create --email jane@campusmate-demo.example --username jane --role student` (run it from `backend`), or `POST /api/v1/users` as an admin.

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
- PostgreSQL (developed on native PostgreSQL 18 on port 5432)
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

The API alone:

```bash
cd backend
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The whole application is one process. The API also ingests uploaded documents, in a background thread (`INGESTION_IN_API`, on by default): the embedded vector store may be used by one process only, and a separate Chroma server is avoided on purpose (see [docs/security.md](docs/security.md)).

```bash
cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000   # API + ingestion
```

End-to-end check against the running application (adds one fictitious synthetic document, follows it through ingestion, answering and deactivation, then deletes it; development databases only):

```bash
cd backend
CAMPUSMATE_ADMIN_PASSWORD=... CAMPUSMATE_STUDENT_PASSWORD=...   .venv/Scripts/python scripts/e2e_live.py --admin <admin email> --student <student email>
```

- Health (liveness): http://127.0.0.1:8000/api/v1/system/health → `{"status":"ok"}`
- Readiness: http://127.0.0.1:8000/api/v1/system/ready → 200 `"status":"ready"` when PostgreSQL is reachable **and** migrated; otherwise 503 with the reason

## Accounts and login

Create the first admin (the password is asked for at a hidden prompt), or the two demo accounts:

```bash
cd backend
.venv/Scripts/python -m app.accounts create --email admin@campusmate-demo.example --username admin2 --role admin --name "Admin"
.venv/Scripts/python -m app.accounts demo   # admin / admin@123 and student / student@123 (refused when APP_ENV=production)
```

Users sign in with their username or their email (both case-insensitive). A username is 3 to 40 characters: lower-case letters, digits, `.`, `_` and `-`.

| Endpoint | Who |
|---|---|
| `POST /api/v1/auth/login` `{"username", "password"}` | anyone. `username` is a username or an email (`"email"` is still accepted as the field name). Sets an httpOnly session cookie and also returns `access_token`. Demo accounts are refused when `APP_ENV=production` |
| `GET /api/v1/auth/demo` | anyone. The demo logins for the login page; `{"enabled": false}` in production or when they do not exist |
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

## Query routing

`GET /api/v1/route?q=...` (`chat:use`) shows how a question would be answered:
- the **route** (`structured` SQL facts, `graph` relationships, `documents` hybrid retrieval, `personal`, or `automation`);
- the **reasons** (which entities and words decided it);
- the **evidence**, each item with its trust level and citation.

Structured and graph evidence are always supported by document passages.

## Answer generation

The component that writes answers is replaceable (`GENERATION_PROVIDER`):

- `extractive` (default): no model. It copies the most relevant evidence sentences with their citations, and labels synthetic ones.
- `openai_compatible`: any server with the OpenAI chat API. Usually a local model in Ollama or llama.cpp; it can also be a hosted API, but then questions and evidence leave the machine. Needs `GENERATION_MODEL`.

```bash
python -m app.generation check           # is the configured provider usable?
python -m app.generation check --probe   # does it cite, label demo data and abstain? how fast?
```

No model is downloaded yet. The options, the hardware budget (4 GB VRAM) and the comparison plan are in [docs/slm-evaluation.md](docs/slm-evaluation.md).

## Chat

`POST /api/v1/chat/query` with `{"question": "..."}` (needs `chat:use`, which logged-in students, faculty and admins have):

```
question -> router -> evidence (SQL facts / knowledge graph / hybrid passages) -> numbered sources
         -> generation provider -> grounding check -> answer with [n] citations
```

The response has:
- `answer` and `answer_type`: `answered`; `fallback` (the model's answer failed the check, so the extractive answer is shown); `abstained` ("I couldn't find authoritative information..."); or `unsupported` (personal records, reminders);
- `sources`: each source with its trust level and whether the answer cites it;
- `contains_synthetic`: whether a cited source is synthetic demo data;
- `tables`: cited structured facts as tables (a semester's courses, a course's offerings, the grading scheme), each linked to its source number;
- `reasons`: why the router chose this evidence (shown as the answer's trace);
- the grounding result and per-stage timings.

The request may carry `program_id` and `semester_id` (the programme and term chosen in the UI). They apply only when the question names no programme or semester itself.

`GET /api/v1/chat/history?q=` lists your own earlier questions. `GET /api/v1/chat/analytics` (`audit:read`) gives 7-day counts, answer types, routes, feedback, latency percentiles, and the questions that were not answered or were rated down, without user identities.

Every exchange is stored in `chat_queries`. `POST /api/v1/chat/feedback` with `{"query_id", "rating": "up"|"down", "comment"}` rates one of your own answers; rating again replaces the previous rating.

```bash
python -m app.evaluation answers   # all dataset questions through the whole pipeline -> evaluation/results/ANSWERS.md
```

## Frontend

None at the moment. The first UI (React 19, Vite, Tailwind 4, to the Stitch designs) was removed on
2026-09-19 so that it can be rebuilt from scratch; `git show c2e2a2d` has the last version, and
`git checkout c2e2a2d -- frontend/stitch-reference` restores the Stitch designs alone. The API is
ready for a new UI: every screen of the old one was fed by the endpoints listed in this README.
A new frontend must talk only to this API (never to PostgreSQL or the vector store) and should
be served from the same origin (for example through a dev-server proxy for `/api`), so the
session cookie stays httpOnly and no CORS is needed.

## Docker

`compose.yaml` runs CampusMate in two containers (the `web` container went with the frontend):

- `db`: PostgreSQL 18, created with the same low-privilege role as a native install;
- `api`: the API with its ingestion thread and the embedding model baked in; it runs as a non-root user and migrates on start;

Only the API is published, and only on `127.0.0.1:8000`. The database is reachable only inside the compose network.

```bash
# in .env: DB_PASSWORD (application role) and POSTGRES_PASSWORD (superuser, used once to create that role)
docker compose up --build -d
docker compose run --rm api python -m app.seed                     # once: the dataset (./data is mounted read-only)
docker compose run --rm api python -m app.ingestion queue-missing  # the API's thread then ingests the PDFs
docker compose run --rm api python -m app.accounts create --email admin@campusmate-demo.example --role admin
# open http://localhost:8000/docs  (API docs are disabled when APP_ENV=production; use /api/v1/system/ready)
```

Data lives in two named volumes, `pgdata` and `storage` (uploads and the vector index). `docker compose down` keeps them; `docker compose down -v` deletes them. To use a model server on the host (e.g. Ollama), set `GENERATION_PROVIDER=openai_compatible` and `GENERATION_MODEL` in `.env`; the API reaches the host at `host.docker.internal:11434`.

## Security

Summary. The full review, with the test behind each control and the open risks, is in [docs/security.md](docs/security.md).

- Login: Argon2id; after 5 failures for an account, or 30 from one client, within 15 minutes → 429 with `Retry-After`, even for the right password. Sessions are hashed, httpOnly, `SameSite=Lax`, and `Secure` in production (enforced).
- Chat: 20 questions per minute per user. JSON bodies are limited to 64 KB; uploads to 50 MB.
- Every API response carries `Content-Security-Policy: default-src 'none'`, `X-Frame-Options: DENY`, `nosniff`, `no-referrer` and `Cache-Control: no-store`.
- `python -m app.accounts purge-sessions` deletes expired and logged-out sessions.
- Dependency audit: `npm audit` is clean. chromadb has an **unfixed** remote-code-execution flaw in its *server*; CampusMate uses only the embedded store, and never runs that server.

## Knowledge (OKF)

```bash
cd backend
.venv/Scripts/python -m app.knowledge validate   # derived graph vs the dataset's 1,202 edges and 297 items
.venv/Scripts/python -m app.knowledge generate   # write storage/knowledge/<type>/<id>.md (+ index.json, relationships.jsonl)
```

`GET /api/v1/knowledge/entities/{id}` returns any entity with its attributes, per-attribute trust labels, and typed relationships in both directions (`taught_by`, `offered_in`, …), each with its own `source_type`. `/entities/{id}/okf` returns the same as an OKF Markdown file. The OKF is generated from PostgreSQL and never edited by hand.

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
