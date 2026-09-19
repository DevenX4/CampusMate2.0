"""Ingestion: unit tests per stage, then the full flow API -> job -> worker -> chunks."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.routes.documents import storage_root
from app.core.db import get_db
from app.ingestion.chunking import EM_DASH, chunk_pages
from app.ingestion.clean import clean_pages
from app.ingestion.enrich import chunk_source_type, find_entity_ids
from app.ingestion.extract import Page, pages_in_scope
from app.ingestion.pipeline import claim_next_job, process_next
from app.main import app
from app.models.documents import DocumentChunk, DocumentVersion
from app.models.operations import AuditLog, IngestionJob
from app.services.ingestion_jobs import queue_missing
from tests.helpers import API, headers_for, make_indexer, text_pdf

# --- stage units (no database) -------------------------------------------------------------------


def test_page_scope_is_the_union_of_listed_pages():
    assert pages_in_scope({"A": [10, 11], "B": [104, 10]}) == [10, 11, 104]
    assert pages_in_scope(None) is None


def test_running_headers_are_removed_but_repeated_field_labels_are_kept():
    topics = ["Alpha", "Bravo", "Charlie", "Delta"]

    def page(n):  # the same labels on every page, surrounded by different amounts of real text
        before = [f"{topics[n - 1]} intro {k}" for k in "abcd"[:n]]
        after = [f"{topics[n - 1]} detail {k}" for k in "abcd"[:5 - n]]
        return Page(n, ["SYNTHETIC DATA BANNER", f"Page {n}", *before, "faculty [S]", "credits [O]", *after])

    result = clean_pages([page(n) for n in range(1, 5)])
    assert result.pages[1].lines == ["Bravo intro a", "Bravo intro b", "faculty [S]", "credits [O]",
                                     "Bravo detail a", "Bravo detail b", "Bravo detail c"]
    assert result.removed_boilerplate == ["Page #", "SYNTHETIC DATA BANNER"]


def test_garbled_text_is_repaired_during_cleaning():
    garbled = "APTITUDE SKILL BUILDING" + chr(0xE2) + chr(0x20AC) + chr(0x201C) + "II"
    result = clean_pages([Page(1, [garbled])])
    assert result.pages[0].lines == ["APTITUDE SKILL BUILDING" + chr(0x2013) + "II"]
    assert result.repaired_strings == 1


def test_chunks_never_split_a_line_and_respect_the_size_limit():
    rows = [f"ROW {i} " + "x" * 50 for i in range(40)]
    chunks = chunk_pages([Page(1, rows)], max_chars=300)
    assert all(len(c.text) <= 300 for c in chunks)
    assert [line for c in chunks for line in c.text.split("\n")] == rows  # nothing lost, nothing cut


def test_entity_headings_and_page_titles_start_new_sections():
    heading = f"COURSE-2CEIT602 {EM_DASH} 2CEIT602 ARTIFICIAL INTELLIGENCE"
    pages = [Page(1, ["intro", heading, "credits 4"]), Page(2, ["row a"]), Page(3, ["row b"])]
    chunks = chunk_pages(pages, 1000, page_titles={2: "Semester V", 3: "Semester VI"})
    assert [(c.section, c.page_start) for c in chunks] == [
        (None, 1), (heading, 1), ("Semester V", 2), ("Semester VI", 3)]


def test_table_rows_are_not_mistaken_for_numbered_headings():
    chunks = chunk_pages([Page(1, ["1.1.3 List of courses", "3.00 1.00 0/40 150 2CEIT602", "4.0 (TH 3.0)"])], 1000)
    assert len(chunks) == 1 and chunks[0].section == "1.1.3 List of courses"


@pytest.mark.parametrize("text,document_type,expected", [
    ("anything", "official", "official"),
    ("credits [O]\nfaculty [S]", "synthetic", "synthetic"),       # mixed: least trusted wins
    ("credits [O]\nalso in [DO]", "synthetic", "derived_official"),  # restated official facts only
    ("source_type: official (quoted)", "synthetic", "derived_official"),
    ("no labels at all", "synthetic", "synthetic"),
])
def test_chunk_trust_level(text, document_type, expected):
    assert chunk_source_type(text, document_type)[0] == expected


def test_entity_ids_and_printed_course_codes_are_recognised():
    known = {"COURSE-2CEIT602", "FAC-IT-002", "SEM-BTECH-IT-06"}
    text = "2CEIT602 taught by FAC-IT-002 in SEM-BTECH-IT-06; FAC-IT-999 and 9ZZZ999 are unknown"
    assert find_entity_ids(text, known) == ["COURSE-2CEIT602", "FAC-IT-002", "SEM-BTECH-IT-06"]


# --- full flow with the database -------------------------------------------------------------------


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


@pytest.fixture
def indexer(tmp_path):
    return make_indexer(tmp_path / "chroma")


FORM = {"title": "Exam Handbook", "document_type": "handbook", "source_type": "synthetic"}
PAGES = [["1.1 Examination rules", "Students must carry their ID card."],
         ["1.2 Re-evaluation", "Apply within 7 days of results."]]


def upload(client, headers, pages=PAGES, path="/documents", form=FORM):
    files = {"file": ("handbook.pdf", text_pdf(pages), "application/pdf")}
    return client.post(API + path, headers=headers, files=files, data=form).json()


def run_worker(db, storage, indexer) -> list:
    results = []
    while (result := process_next(db, storage, max_chars=1200, lease_minutes=30, indexer=indexer)) is not None:
        results.append(result)
    return results


def chunks_of(db, document_id, version_no):
    return db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id,
                                                  DocumentChunk.version_no == version_no)
                      .order_by(DocumentChunk.chunk_index)).all()


def test_upload_is_ingested_and_activated(client, db_session, storage, admin, indexer):
    doc_id = upload(client, admin)["document_id"]
    [result] = run_worker(db_session, storage, indexer)
    assert result.status == "completed"

    chunks = chunks_of(db_session, doc_id, 1)
    assert [c.section for c in chunks] == ["1.1 Examination rules", "1.2 Re-evaluation"]
    assert [c.page_start for c in chunks] == [1, 2]
    assert {c.source_type for c in chunks} == {"synthetic"}
    assert chunks[0].metadata_["document_type"] == "handbook"

    job = db_session.scalar(select(IngestionJob).where(IngestionJob.document_id == doc_id))
    assert set(job.stage_timings) == {"extract", "clean", "chunk", "enrich", "index", "store"}
    assert indexer.index.count() == 2  # one vector per chunk
    detail = client.get(f"{API}/documents/{doc_id}", headers=admin).json()
    assert detail["active_version"]["version_no"] == 1  # answerable now
    assert client.get(f"{API}/documents/stats", headers=admin).json()["total_chunks"] == 2
    assert (storage / "processed" / doc_id / "v1.json").is_file()


def test_replacement_activates_new_version_and_keeps_old_chunks_for_rollback(client, db_session, storage, admin, indexer):
    doc_id = upload(client, admin)["document_id"]
    run_worker(db_session, storage, indexer)
    upload(client, admin, pages=[["2.1 Revised rules", "New text."]], path=f"/documents/{doc_id}/versions", form={})
    run_worker(db_session, storage, indexer)
    statuses = {v.version_no: v.status for v in db_session.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id))}
    assert statuses == {1: "superseded", 2: "active"}
    assert len(chunks_of(db_session, doc_id, 1)) == 2  # kept: rollback is instant


def test_failed_new_version_leaves_the_active_one_answering(client, db_session, storage, admin, indexer):
    doc_id = upload(client, admin)["document_id"]
    run_worker(db_session, storage, indexer)
    detail = upload(client, admin, pages=[["new"]], path=f"/documents/{doc_id}/versions", form={})
    v2 = next(v for v in detail["versions"] if v["version_no"] == 2)
    (storage / "originals" / v2["sha256"][:2] / f"{v2['sha256']}.pdf").write_bytes(b"%PDF-1.4 corrupted")

    [result] = run_worker(db_session, storage, indexer)
    assert result.status == "failed"
    job = db_session.scalar(select(IngestionJob).where(IngestionJob.document_id == doc_id,
                                                       IngestionJob.version_no == 2))
    assert job.error_detail["stage"] == "extract" and job.error_message
    versions = {v.version_no: v.status for v in db_session.scalars(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id))}
    assert versions == {1: "active", 2: "failed"}
    assert db_session.scalar(select(AuditLog).where(AuditLog.action == "ingestion.failed")) is not None

    # Retry through the API puts it back in the queue.
    retried = client.post(f"{API}/ingestion/jobs/{job.id}/retry", headers=admin)
    assert retried.status_code == 200 and retried.json()["status"] == "pending"
    assert client.post(f"{API}/ingestion/jobs/{job.id}/retry", headers=admin).status_code == 409


def test_reindex_replaces_chunks_and_keeps_version_active(client, db_session, storage, admin, indexer):
    doc_id = upload(client, admin)["document_id"]
    run_worker(db_session, storage, indexer)
    before = {c.chunk_id for c in chunks_of(db_session, doc_id, 1)}
    client.post(f"{API}/documents/{doc_id}/reindex", headers=admin)
    run_worker(db_session, storage, indexer)
    after = chunks_of(db_session, doc_id, 1)
    assert len(after) == len(before) and not before & {c.chunk_id for c in after}  # rebuilt
    assert indexer.index.count() == len(after)  # the replaced chunks' vectors were removed
    assert db_session.get(DocumentVersion, (doc_id, 1)).status == "active"


def test_job_of_a_crashed_worker_is_claimed_again(client, db_session, storage, admin, indexer):
    upload(client, admin)
    job = db_session.scalar(select(IngestionJob))
    job.status, job.started_at = "processing", datetime.now(UTC) - timedelta(hours=2)
    db_session.flush()
    assert claim_next_job(db_session, lease_minutes=30).id == job.id
    assert job.attempts == 1


def test_job_endpoints_are_admin_only(client, db_session, admin):
    faculty = headers_for(client, db_session, "faculty")
    assert client.get(f"{API}/ingestion/jobs", headers=faculty).status_code == 403
    assert client.get(f"{API}/ingestion/jobs", headers=admin).status_code == 200


# --- the real dataset --------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ingested(seeded_session, tmp_path_factory):
    """The seeded dataset with every document ingested from the real PDFs."""
    from app.core.config import get_settings
    from app.seed.run import seed

    storage = tmp_path_factory.mktemp("storage")
    seed(seeded_session, get_settings().data_dir, storage)  # copies the 12 PDFs into this storage
    assert queue_missing(seeded_session) == 12
    results = run_worker(seeded_session, storage, make_indexer(storage / "chroma"))
    assert [r.status for r in results] == ["completed"] * 12
    return seeded_session


def test_official_syllabus_is_indexed_only_inside_its_page_scope(ingested):
    pages = set(ingested.scalars(select(DocumentChunk.page_start).where(
        DocumentChunk.document_id == "DOC-OFFICIAL-SYLLABUS-001")))
    assert pages <= set(range(10, 19)) | set(range(104, 109))  # never the other ~728 pages


def test_official_fact_chunk_has_page_semester_and_entity(ingested):
    chunk = ingested.scalar(select(DocumentChunk).where(
        DocumentChunk.document_id == "DOC-OFFICIAL-SYLLABUS-001",
        DocumentChunk.entity_ids.any("COURSE-2CEIT602")))
    assert (chunk.page_start, chunk.source_type) == (15, "official")
    assert chunk.metadata_["semester_ids"] == ["SEM-BTECH-IT-06"]
    assert "ARTIFICIAL INTELLIGENCE" in chunk.text


def test_synthetic_documents_never_produce_official_chunks(ingested):
    rows = ingested.execute(
        select(DocumentChunk.source_type, func.count()).where(~DocumentChunk.document_id.like("DOC-OFFICIAL-%"))
        .group_by(DocumentChunk.source_type)).all()
    assert "official" not in dict(rows)
    mixed = ingested.scalar(select(DocumentChunk).where(DocumentChunk.document_id == "DOC-COURSES-001",
                                                        DocumentChunk.section.like("COURSE-2CEIT602 %")))
    assert mixed.source_type == "synthetic"  # it also lists synthetic faculty and labs
