"""Document management: uploads, validation, versions, lifecycle, reindex, download, permissions."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes.documents import storage_root
from app.core.db import get_db
from app.main import app
from app.models.documents import DocumentVersion
from app.models.operations import AuditLog, IngestionJob
from tests.helpers import API, headers_for, make_pdf

FORM = {"title": "Examination Rules 2026", "document_type": "examination", "source_type": "synthetic"}


@pytest.fixture
def storage(tmp_path):
    return tmp_path


@pytest.fixture
def client(db_session, storage):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[storage_root] = lambda: storage
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def admin(client, db_session):
    return headers_for(client, db_session, "admin")


def upload(client, headers, content: bytes | None = None, *, filename="rules.pdf",
           content_type="application/pdf", form=FORM, path="/documents"):
    files = {"file": (filename, content if content is not None else make_pdf(), content_type)}
    return client.post(API + path, headers=headers, files=files, data=form)


def make_ready(db, document_id: str, version_no: int) -> None:
    """Stand-in for Phase 7's ingestion, which is what moves a version from pending to ready."""
    db.get(DocumentVersion, (document_id, version_no)).status = "ready"
    db.flush()


# --- upload ------------------------------------------------------------------------------------

def test_upload_registers_version_1_stores_file_and_queues_job(client, db_session, admin, storage):
    content = make_pdf(pages=3)
    response = upload(client, admin, content)
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["document_id"].startswith("DOC-") and doc["status"] == "active"
    version = doc["versions"][0]
    assert (version["version_no"], version["status"], version["page_count"]) == (1, "pending", 3)
    assert doc["active_version"] is None  # nothing answerable until ingested and activated
    # Stored under its content address, not under the client's filename.
    stored = storage / "originals" / version["sha256"][:2] / f"{version['sha256']}.pdf"
    assert stored.read_bytes() == content
    assert list((storage / "tmp").iterdir()) == []  # temporary file cleaned up
    job = db_session.scalar(select(IngestionJob).where(IngestionJob.document_id == doc["document_id"]))
    assert (job.job_type, job.status, job.version_no) == ("ingest", "pending", 1)
    assert db_session.scalar(select(AuditLog).where(AuditLog.action == "document.upload")) is not None


def test_same_file_twice_is_rejected_as_duplicate(client, admin):
    content = make_pdf()
    first = upload(client, admin, content).json()
    again = upload(client, admin, content)
    assert again.status_code == 409
    assert first["document_id"] in again.json()["error"]["message"]


@pytest.mark.parametrize("content,filename,content_type,expected_status", [
    (b"just some text", "notes.pdf", "application/pdf", 415),       # content is not a PDF
    (None, "rules.docx", "application/pdf", 415),                   # wrong extension
    (None, "rules.pdf", "text/plain", 415),                         # wrong declared type
    (b"%PDF-1.7 truncated garbage", "broken.pdf", "application/pdf", 422),  # unreadable PDF
    (b"", "empty.pdf", "application/pdf", 422),                     # empty file
])
def test_invalid_files_are_rejected_and_nothing_is_kept(client, admin, storage, content, filename,
                                                        content_type, expected_status):
    response = upload(client, admin, content, filename=filename, content_type=content_type)
    assert response.status_code == expected_status, response.text
    assert response.json()["error"]["code"].startswith("upload_")
    assert not (storage / "originals").exists()
    assert not (storage / "tmp").exists() or list((storage / "tmp").iterdir()) == []


def test_oversized_upload_is_rejected(client, admin, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert upload(client, admin).status_code == 413


def test_invalid_metadata_is_422_and_temp_file_is_removed(client, admin, storage):
    response = upload(client, admin, form={**FORM, "source_type": "rumour"})
    assert response.status_code == 422
    # Metadata is validated before the file is touched: not even the tmp folder was created.
    assert not (storage / "tmp").exists()


def test_client_filename_is_never_used_as_a_path(client, admin, storage):
    response = upload(client, admin, filename="../../etc/evil.pdf")
    assert response.status_code == 201
    assert response.json()["versions"][0]["original_filename"] == "evil.pdf"
    assert {p.parent.parent.name for p in storage.rglob("*.pdf")} == {"originals"}


# --- versions and activation ----------------------------------------------------------------------

def test_replace_activate_and_roll_back(client, db_session, admin):
    doc_id = upload(client, admin).json()["document_id"]
    make_ready(db_session, doc_id, 1)
    assert client.post(f"{API}/documents/{doc_id}/versions/1/activate", headers=admin).status_code == 200

    v2 = upload(client, admin, path=f"/documents/{doc_id}/versions", form={"version_label": "Revised"})
    assert v2.status_code == 201
    assert v2.json()["active_version"]["version_no"] == 1  # v1 keeps answering meanwhile

    blocked = client.post(f"{API}/documents/{doc_id}/versions/2/activate", headers=admin)
    assert blocked.status_code == 409 and "pending" in blocked.json()["error"]["message"]

    make_ready(db_session, doc_id, 2)
    activated = client.post(f"{API}/documents/{doc_id}/versions/2/activate", headers=admin).json()
    statuses = {v["version_no"]: v["status"] for v in activated["versions"]}
    assert statuses == {1: "superseded", 2: "active"}

    rolled_back = client.post(f"{API}/documents/{doc_id}/versions/1/activate", headers=admin).json()
    assert {v["version_no"]: v["status"] for v in rolled_back["versions"]} == {1: "active", 2: "superseded"}


def test_new_version_of_identical_content_is_refused(client, admin):
    content = make_pdf()
    doc_id = upload(client, admin, content).json()["document_id"]
    response = upload(client, admin, content, path=f"/documents/{doc_id}/versions", form={})
    assert response.status_code == 409


# --- lifecycle ----------------------------------------------------------------------------------

def test_lifecycle_transitions(client, admin):
    doc_id = upload(client, admin).json()["document_id"]
    post = lambda action: client.post(f"{API}/documents/{doc_id}/{action}", headers=admin)  # noqa: E731
    assert post("deactivate").json()["status"] == "inactive"
    assert post("deactivate").status_code == 409  # already inactive
    assert post("archive").json()["status"] == "archived"
    assert post("activate").json()["status"] == "active"
    assert client.delete(f"{API}/documents/{doc_id}", headers=admin).json()["status"] == "deleted"
    assert post("activate").status_code == 409  # deleted is final
    listed = client.get(f"{API}/documents", headers=admin).json()["items"]
    assert doc_id not in {d["document_id"] for d in listed}  # hidden by default
    deleted = client.get(f"{API}/documents", headers=admin, params={"status": "deleted"}).json()["items"]
    assert doc_id in {d["document_id"] for d in deleted}


def test_reindex_needs_an_active_version_and_no_open_job(client, db_session, admin):
    doc_id = upload(client, admin).json()["document_id"]
    assert client.post(f"{API}/documents/{doc_id}/reindex", headers=admin).status_code == 409  # no active version
    make_ready(db_session, doc_id, 1)
    client.post(f"{API}/documents/{doc_id}/versions/1/activate", headers=admin)
    db_session.execute(IngestionJob.__table__.update().values(status="completed"))  # the initial ingest finished
    assert client.post(f"{API}/documents/{doc_id}/reindex", headers=admin).status_code == 200
    assert client.post(f"{API}/documents/{doc_id}/reindex", headers=admin).status_code == 409  # already queued


# --- download and permissions --------------------------------------------------------------------

def test_admin_downloads_the_exact_original(client, admin):
    content = make_pdf()
    doc_id = upload(client, admin, content, filename="Exam Rules.pdf").json()["document_id"]
    response = client.get(f"{API}/documents/{doc_id}/versions/1/file", headers=admin)
    assert response.status_code == 200 and response.content == content
    # RFC 5987 encoding keeps spaces and non-ASCII names safe in the header.
    assert response.headers["content-disposition"] == "attachment; filename*=utf-8''Exam%20Rules.pdf"


def test_permissions(client, db_session, admin):
    doc_id = upload(client, admin).json()["document_id"]
    faculty = headers_for(client, db_session, "faculty")
    student = headers_for(client, db_session, "student")
    assert client.get(f"{API}/documents", headers=faculty).status_code == 200      # documents:read
    assert client.get(f"{API}/documents/{doc_id}/versions/1/file", headers=faculty).status_code == 403
    assert upload(client, faculty).status_code == 403
    assert client.get(f"{API}/documents", headers=student).status_code == 403
    assert client.get(f"{API}/documents").status_code == 401


def test_stats_on_the_seeded_registry(seeded_session):
    from app.services.documents import stats
    numbers = stats(seeded_session)
    assert (numbers.active_documents, numbers.total_documents) == (12, 12)
    assert numbers.total_chunks == 0 and numbers.pending_jobs == 0  # nothing ingested yet
