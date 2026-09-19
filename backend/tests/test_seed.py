from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.curriculum import CatalogListing, Course, CourseOffering
from app.models.documents import DocumentVersion
from app.models.people import TeachingAssignment
from app.seed.run import seed
from app.seed.source import TextRepairs, load_source, parse_dmy_date, parse_iso_date
from app.seed.transform import build_rows
from app.services.storage import sha256_of
from tests.conftest import requires_dataset

GARBLED = "APTITUDE SKILL BUILDING\u00e2\u20ac\u201cII"  # garbled en dash, see app/seed/source.py
FIXED = "APTITUDE SKILL BUILDING\u2013II"


# --- value cleaning (no database) -----------------------------------------------------

def test_repairs_utf8_text_that_was_decoded_as_cp1252():
    repairs = TextRepairs()
    assert repairs.repair(GARBLED) == FIXED
    assert repairs.count == 1


@pytest.mark.parametrize("value", ["Mon\u2013Sat 09:00\u201318:00", "Caf\u00e9", "2CEIT602", ""])
def test_leaves_correct_text_alone(value):
    repairs = TextRepairs()
    assert repairs.repair(value) == value
    assert repairs.count == 0


def test_only_exact_dates_are_parsed():
    assert parse_iso_date("2026-07-01") == date(2026, 7, 1)
    assert parse_iso_date("2021-06-01 (Effective Year 2021-2022; exact date not stated)") is None
    assert parse_iso_date(None) is None
    assert parse_dmy_date("28/09/2022") == date(2022, 9, 28)


@requires_dataset
def test_transform_produces_expected_row_counts():
    rows = build_rows(load_source(get_settings().data_dir))
    counts = {name: len(r) for name, r in rows.items()}
    assert counts["courses"] == 116
    assert counts["course_offerings"] == 112
    assert counts["catalog_listings"] == 291
    assert counts["document_entities"] == 733
    assert counts["policy_links"] == 77
    assert counts["notice_links"] == 56
    assert sum(counts.values()) == 2360


# --- seeding a real database ------------------------------------------------------------

@pytest.fixture(scope="module")
def seeded(migrated_engine, tmp_path_factory):
    """Seed campusmate_test once for this module inside a transaction, roll back at the end."""
    storage = tmp_path_factory.mktemp("storage")
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        report = seed(session, get_settings().data_dir, storage)
        yield session, report, storage
        session.close()
        transaction.rollback()



@requires_dataset
def test_first_run_is_valid_and_inserts_everything(seeded):
    _, report, _ = seeded
    assert report.problems == []
    assert all(s.inserted == s.rows for s in report.tables)
    assert len(report.text_repairs) == 2


@requires_dataset
def test_second_run_changes_nothing(seeded):
    session, _, storage = seeded
    again = seed(session, get_settings().data_dir, storage)
    assert again.problems == []
    assert [(s.table, s.inserted, s.updated, s.deleted) for s in again.tables if
            s.inserted or s.updated or s.deleted] == []


@requires_dataset
def test_official_fact_keeps_its_citation(seeded):
    session, _, _ = seeded
    offering = session.scalars(
        select(CourseOffering).join(Course).where(Course.course_code == "2CEIT602")
    ).one()
    assert offering.course.course_name == "ARTIFICIAL INTELLIGENCE"
    assert offering.semester_id == "SEM-BTECH-IT-06"
    assert offering.credit_total == Decimal("4.00")
    assert (offering.source_type, offering.source_document_id,
            offering.source_version_no, offering.source_page) == (
            "official", "DOC-OFFICIAL-SYLLABUS-001", 1, 15)


@requires_dataset
def test_synthetic_teaching_stays_labelled_synthetic(seeded):
    session, _, _ = seeded
    rows = session.execute(
        select(TeachingAssignment.faculty_id, TeachingAssignment.source_type)
        .where(TeachingAssignment.course_id == "COURSE-2CEIT602")
    ).all()
    assert set(rows) == {("FAC-IT-002", "synthetic"), ("FAC-IT-004", "synthetic")}


@requires_dataset
def test_garbled_catalog_name_is_stored_repaired(seeded):
    session, _, _ = seeded
    names = session.scalars(
        select(CatalogListing.listed_course_name).where(CatalogListing.course_id == "COURSE-2HS6101")
    ).all()
    assert FIXED in names
    assert not any("\u00e2\u20ac" in n for n in names)


@requires_dataset
def test_vague_registry_date_is_not_invented(seeded):
    session, _, _ = seeded
    syllabus = session.get(DocumentVersion, ("DOC-OFFICIAL-SYLLABUS-001", 1))
    assert syllabus.effective_from is None
    assert "exact date not stated" in syllabus.notes
    assert syllabus.page_scope["PROG-BTECH-IT-001"] == list(range(10, 19))


@requires_dataset
def test_pdfs_are_stored_under_their_content_address(seeded):
    session, _, storage = seeded
    versions = session.scalars(select(DocumentVersion)).all()
    assert len(versions) == 12
    for version in versions:
        stored = storage / version.storage_key
        assert stored.is_file() and sha256_of(stored) == version.sha256


@requires_dataset
def test_seed_repairs_drift(seeded):
    session, _, storage = seeded
    session.execute(text("UPDATE courses SET course_name = 'CLOUD COMPUTING ARCHITECTURE' "
                         "WHERE course_id = 'COURSE-2CEIT602'"))
    session.execute(text("INSERT INTO lab_courses VALUES ('LAB-IT-001', 'COURSE-2BS101')"))
    report = seed(session, get_settings().data_dir, storage)
    stats = {s.table: s for s in report.tables}
    assert stats["courses"].updated == 1
    assert stats["lab_courses"].deleted == 1
    assert session.get(Course, "COURSE-2CEIT602").course_name == "ARTIFICIAL INTELLIGENCE"
