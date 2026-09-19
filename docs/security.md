# Security review (Phase 19)

CampusMate runs **locally**: one API process (FastAPI, with the ingestion worker as a thread),
PostgreSQL, the built UI, and an optional local model server. This review lists what is protected
against which threat, the test that proves it, and what is left open.

## What is worth protecting

| Asset | Why |
|---|---|
| Integrity of answers | Students act on them. A wrong credit value, or demo data presented as official GUNI information, does real harm |
| Accounts and sessions | Admins can change what CampusMate knows |
| The knowledge base | Only admins may add, replace or deactivate documents |
| Chat history | Students' questions are personal data |
| Secrets | The database password; an API key if a hosted model is ever used |

## Controls

| Threat | Control | Tested in |
|---|---|---|
| Invented facts (hallucination) | Answers only from retrieved sources. A deterministic grounding check requires that cited sources exist and that every number, code and name occurs in them; a failed check falls back to quoting the sources. A reference to an ID that does not exist ("LAB-IT-011") makes CampusMate abstain | `test_chat.py`, `test_hallucination.py` (all 23 trap questions) |
| Demo data passed off as official | Trust level (`official`, `derived_official`, `synthetic`) on every row, chunk, graph edge and source; synthetic sources are labelled in the answer and in the UI. A question that asks for "official" information drops synthetic sources. An upload must declare its trust level; there is no default | `test_generation.py`, `test_chat.py`, `test_hallucination.py`, `admin.test.tsx` |
| A misleading quotation | Quoted relationship clauses keep their subject; a sentence wrapped over two PDF lines is never quoted in half | `test_generation.py`, `test_hallucination.py` |
| Password guessing | Argon2id hashes (verification runs even for unknown emails, so timing reveals nothing). After 5 failures for an account, or 30 from one client IP, within 15 minutes: 429 with Retry-After, **before** the password is checked. Counted from the audit log | `test_auth.py`, `test_security.py` |
| Demo accounts with public passwords (`admin` / `admin@123`, `student` / `student@123`) | Created only by `python -m app.accounts demo`, which refuses when `APP_ENV=production`. They are marked `is_demo`, and the API refuses their logins in production even if they exist. `/auth/demo` shows them to the login page only outside production | `test_ui_api.py` |
| Session theft or replay | 256-bit random tokens, stored only as SHA-256. httpOnly `SameSite=Lax` cookie, `Secure` required in production. Logout and deactivation revoke sessions at once; dead sessions are purged | `test_auth.py`, `test_security.py` |
| Privilege escalation | The role is always read from the database, never from the client. Every endpoint checks a permission; UI guards are only a convenience | `test_auth.py`, `test_documents.py`, `test_chat.py`, `App.test.tsx` |
| Reading or rating someone else's answers | Feedback only on one's own answers. Query ids are random UUIDs, and another user's query looks like a missing one (404) | `test_chat.py` |
| Cross-site request forgery | `SameSite=Lax` cookies are not sent on cross-site POSTs; the API has no CORS, so other origins cannot read responses | `test_auth.py` |
| Cross-site scripting | The UI renders answers and sources as React text (no `dangerouslySetInnerHTML` anywhere). API responses carry `Content-Security-Policy: default-src 'none'` and `nosniff` | `AnswerText.test.tsx`, `test_security.py` |
| Malicious or huge uploads | Admins only; size limit while streaming; PDF signature check; the stored name is the content's SHA-256 (no user-controlled paths); duplicates are refused; downloads are sent as attachments | `test_documents.py` |
| Resource exhaustion | JSON bodies limited to 64 KB (also without Content-Length); 20 questions per minute per user; uploads limited to 50 MB | `test_security.py` |
| SQL injection | SQLAlchemy with bound parameters only; the raw SQL is fixed text | code review |
| Leaking internals | Unexpected errors return a generic message (details go to the log only). Config errors never print the input (a `DB_PASSWORD` leak found and fixed in Phase 15). API docs are disabled in production | `test_system.py`, `test_generation.py` |
| Tampering with history | `audit_logs` is append-only: a trigger rejects UPDATE, DELETE and TRUNCATE | `test_constraints.py` |
| Secrets in the repository | `.env` is ignored; `SecretStr` for passwords and keys; history scanned: placeholders only | `test_config.py` |
| Remote model provider | Key sent only as a header to the configured URL; URLs in errors drop `user:password@`; a warning is logged when questions would leave the machine | `test_generation.py` |

## Dependency audit (2026-09-19)

- `npm audit` (frontend): 0 vulnerabilities.
- `pip-audit` (backend): **chromadb 1.5.9 has five advisories, and no fixed version exists.**
  The most severe is CVE-2026-45829 (PYSEC-2026-311): pre-authentication remote code execution
  through the **Chroma server's** collection endpoint. The others concern the server's
  multi-tenant authorization.

  **Mitigation:** CampusMate does not run a Chroma server. The vector store is embedded, with no
  network endpoint, and only the API process uses it: ingestion runs as a thread of the API.
  The Chroma server introduced in Phase 18 was removed again for this reason. `CHROMA_URL`
  remains possible, with a warning that such a server must never be reachable by anything but
  CampusMate.

  **Recommended follow-up:** store the vectors in PostgreSQL (the search is already exact and
  done in numpy). This would remove chromadb, and with it these advisories and the one-process
  restriction. It changes the stack you specified, so it is your decision.

## Open risks (accepted for a local deployment)

- **Account lockout as denial of service:** anyone who knows an email can lock that account for
  15 minutes. This is the usual trade-off of per-account throttling.
- **Behind a reverse proxy,** uvicorn must run with `--proxy-headers`; otherwise every client
  shares the proxy's IP and the per-IP login limit becomes global.
- **`/search` and `/route` have no rate limit** (the chat has one). They are cheap without a
  model, but should be limited if CampusMate is exposed.
- **Prompt injection through documents:** a document could contain text addressed to the model.
  Only admins can upload; the prompt presents sources as data; the grounding check rejects
  invented numbers, codes and names. A model persuaded to *omit* something is not caught.
- **Wrong statements made only of words from the sources** are not caught by the grounding
  check (for example "closed" instead of "open", or a number from the wrong table row). A model
  judge or human review would be needed.
- **No retention period for chat history** and no account self-service (password change,
  deletion). Needed before real students use it.
- **No multi-factor authentication** for admins.
- **The demo accounts** are real accounts on a development machine: anyone who can reach the
  local UI can sign in as `admin`. Keep the servers on 127.0.0.1 (as the scripts do), and
  deactivate the demo accounts in **Users** before showing CampusMate on a shared network.
