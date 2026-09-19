# Deployment evaluation (Phase 21)

**Nothing is deployed.** CampusMate is local-only by the project owner's instruction. This
document evaluates where it *could* run, from the application's measured requirements, so the
choice can be made deliberately later. Platform prices and limits change: check them at
decision time.

## What the application actually needs

| Requirement | Measured / known | Consequence |
|---|---|---|
| API process memory | About 300 MB working set with BGE, Chroma and BM25 loaded (Phase 15), more while ingesting | At least 1 GB of RAM per API instance; 512 MB tiers are too small |
| Vector store | Embedded Chroma on a local disk, usable by **one** process only (Phase 18); a Chroma server is not an option (unfixed CVE-2026-45829, Phase 19) | Today: **exactly one API instance with a persistent disk**. Scaling out first needs the vectors moved into PostgreSQL |
| Background work | The ingestion thread in the API; jobs durable in PostgreSQL | Needs a long-running process: no serverless functions |
| Uploads | Up to 50 MB per PDF (the official syllabus is 37 MB), stored by content hash | A persistent disk, or object storage once there are several instances |
| Database | PostgreSQL 18; the app uses a low-privilege role; rate limits and throttling live in the database | Any managed PostgreSQL works; the limits keep working across instances |
| Browser security | UI and API on **one origin** (httpOnly `SameSite=Lax` cookie, no CORS) | A separately hosted UI must proxy `/api` to the API (for example a rewrite), not call it cross-origin |
| Generation (SLM) | 1.5–4 B models need about 1–2.5 GB of VRAM at 4-bit (docs/slm-evaluation.md); extractive needs nothing | A GPU host, a hosted model API (questions and evidence leave the premises), or extractive only |
| Latency | Retrieval and routing take tens of ms; an answer from a local model takes seconds | No special edge or CDN needs beyond static files |

## Options

| Option | Fits today's architecture? | For | Against |
|---|---|---|---|
| **This machine (docker compose / native)**: current | Yes | Nothing leaves the machine; no cost; what is tested | Only for one user at the desk; the machine's 4 GB of VRAM limits model size |
| **A campus VM or server, with the same compose file and a TLS reverse proxy** | Yes, unchanged | Data stays at the university; a GPU is possible for the SLM; one `docker compose up` | Needs a server and someone to run it (updates, backups of `pgdata` and `storage`) |
| **Render** (Docker web service + persistent disk + managed PostgreSQL) | Yes, with **one** instance (a disk attaches to one instance, no zero-downtime deploys) | Managed TLS, deploys from Git, managed backups | No GPU: extractive answers or a hosted model API; data at a third party |
| **Railway** (Docker service + volume + PostgreSQL) | Yes, one instance | Similar to Render; simple volumes | Same trade-offs as Render |
| **Vercel** | UI only | Excellent for the static UI; rewrites can proxy `/api` so the origin stays single | Cannot host the API (serverless, ephemeral disk, time limits, no background thread) |
| **Hosted vector database** (Pinecone, Qdrant Cloud, Chroma Cloud) | Not needed | Scales to millions of vectors | About 1,000 chunks need no ANN service (exact search takes ~25 ms); a third party would hold university content |
| **Object storage** (S3-compatible) | Only after the vectors move into PostgreSQL | Stateless API instances | Unnecessary with a single instance and a disk |
| **Hosted SLM API** (OpenAI-compatible) | Yes, via configuration (`GENERATION_PROVIDER=openai_compatible`) | Best answer quality; no GPU needed | Every question and its evidence leave the university; cost per token; needs an API key |

## Recommendation

1. **For the project and its defence:** keep it local (native or `docker compose`). This is
   what is built, tested and evaluated.
2. **If the university wants it hosted:** a campus VM with the existing `compose.yaml` behind a
   TLS reverse proxy is the smallest step. Nothing in the application changes, the data stays
   on campus, and a GPU can run the SLM locally.
3. **Before any hosting that more than one person uses,** close the open risks from
   `security.md`:
   - a retention period for chat history;
   - password reset and change;
   - multi-factor authentication for admins;
   - rate limits on `/search` and `/route`;
   - `COOKIE_SECURE` with TLS, and uvicorn `--proxy-headers` behind the proxy.
4. **Only if it must scale beyond one instance:** move the vectors into PostgreSQL (pgvector or
   an array column, with the same exact search), put uploads in object storage, and the API
   becomes stateless. Then a PaaS such as Render or Railway fits naturally, with the UI on
   Vercel or served by the same container.
5. **Hosted SLM API:** only by an explicit decision about sending students' questions off
   campus. The provider abstraction makes it a configuration change, not a code change.
