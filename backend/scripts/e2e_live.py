"""Live end-to-end scenario against a RUNNING CampusMate: the API, the ingestion worker and the
real embedding model, reached through the same URL the browser uses.

    CAMPUSMATE_ADMIN_PASSWORD=... CAMPUSMATE_STUDENT_PASSWORD=... \
    python scripts/e2e_live.py --base http://127.0.0.1:5173 --admin admin@... --student student@...

Needs `uvicorn app.main:app`, `python -m app.ingestion worker` and, for the /api proxy, the Vite
dev server (or point --base at the API itself, http://127.0.0.1:8000).

For a development database only: it uploads one clearly fictitious synthetic document, checks
that answers follow its lifecycle, and deletes it again (soft delete) at the end.
"""

import argparse
import os
import sys
import time
import uuid

import httpx
from fpdf import FPDF

ABSTAIN = "I couldn't find authoritative information for that in the current CampusMate knowledge base."
QUESTION = "When does the Zephyr reading room open?"


def handbook_pdf(run_id: str) -> bytes:
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    pdf.add_page()
    for line in ("Library services (end-to-end test document, not real information)",
                 "The Zephyr reading room opens at 07:15 on weekdays.", f"Test run {run_id}"):
        pdf.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


class Scenario:
    def __init__(self):
        self.failures = 0

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.failures += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
        return ok


def login(base: str, email: str, password_env: str) -> httpx.Client:
    password = os.environ.get(password_env)
    if not password:
        sys.exit(f"Set {password_env} to the password of {email}")
    client = httpx.Client(base_url=f"{base.rstrip('/')}/api/v1", timeout=120)
    response = client.post("/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        sys.exit(f"Login failed for {email}: HTTP {response.status_code}")
    return client  # the httpOnly session cookie is kept by the client


def ask(client: httpx.Client, question: str) -> dict:
    started = time.perf_counter()
    body = client.post("/chat/query", json={"question": question}).json()
    body["_seconds"] = time.perf_counter() - started
    return body


def cited_documents(body: dict) -> set[str]:
    return {s["citation"]["document_id"] for s in body.get("sources", []) if s["cited"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5173")
    parser.add_argument("--admin", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--ingest-timeout", type=int, default=300, help="seconds to wait for the worker")
    args = parser.parse_args()
    s = Scenario()
    admin = login(args.base, args.admin, "CAMPUSMATE_ADMIN_PASSWORD")
    student = login(args.base, args.student, "CAMPUSMATE_STUDENT_PASSWORD")

    credits = ask(student, "How many credits does ARTIFICIAL INTELLIGENCE carry in B.Tech IT?")
    s.check("structured answer from the official syllabus", "4 credits" in credits.get("answer", "")
            and "DOC-OFFICIAL-SYLLABUS-001" in cited_documents(credits), f"{credits['_seconds']:.2f} s")
    s.check("personal question is unsupported", ask(student, "What are my marks?").get("answer_type") == "unsupported")
    s.check("student cannot upload", student.post("/documents").status_code == 403)

    run_id = uuid.uuid4().hex[:8]
    created = admin.post("/documents", files={"file": (f"e2e-{run_id}.pdf", handbook_pdf(run_id), "application/pdf")},
                         data={"title": f"E2E Library Handbook {run_id} (Synthetic)", "document_type": "handbook",
                               "source_type": "synthetic"})
    if not s.check("admin uploads a synthetic document", created.status_code == 201, f"HTTP {created.status_code}"):
        return 1
    document_id = created.json()["document_id"]
    try:
        started, status = time.perf_counter(), "pending"
        while status not in ("active", "failed") and time.perf_counter() - started < args.ingest_timeout:
            time.sleep(2)
            status = admin.get(f"/documents/{document_id}").json()["versions"][0]["status"]
        s.check("the worker ingests and activates it", status == "active",
                f"{status} after {time.perf_counter() - started:.0f} s")

        answer = ask(student, QUESTION)
        s.check("the answer comes from the new document", "07:15" in answer.get("answer", "")
                and document_id in cited_documents(answer), f"{answer.get('answer_type')}, {answer['_seconds']:.2f} s")
        s.check("and is labelled synthetic", answer.get("contains_synthetic") is True)

        admin.post(f"/documents/{document_id}/deactivate")
        after = ask(student, QUESTION)
        s.check("deactivated: no longer answered from", document_id not in cited_documents(after)
                and "07:15" not in after.get("answer", ""), after.get("answer_type", ""))
    finally:
        deleted = admin.delete(f"/documents/{document_id}")
        s.check("clean-up: test document deleted", deleted.status_code == 200)
    print(f"{'ALL PASSED' if s.failures == 0 else f'{s.failures} FAILED'}")
    return 1 if s.failures else 0


if __name__ == "__main__":
    sys.exit(main())
