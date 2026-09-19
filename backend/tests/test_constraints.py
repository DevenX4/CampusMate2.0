"""Each test tries to store invalid data and checks that PostgreSQL itself refuses it.
All data here is invented test data and is rolled back after every test."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models.auth import Role, User
from app.models.campus import Building
from app.models.content import CalendarEvent
from app.models.curriculum import Course, CourseOffering, ElectiveGroup, Program, Semester
from app.models.documents import Document, DocumentVersion
from app.models.operations import AuditLog
from app.models.organization import Department, University
from app.models.people import Faculty, TeachingAssignment

DOC = "DOC-TEST-001"
PROVENANCE = {"source_type": "synthetic", "source_document_id": DOC, "source_version_no": 1}


def version(document_id=DOC, version_no=1, sha="a" * 64, status="active") -> DocumentVersion:
    return DocumentVersion(
        document_id=document_id, version_no=version_no, sha256=sha,
        storage_key=f"originals/{sha}.pdf", original_filename="test.pdf",
        mime_type="application/pdf", size_bytes=1024, status=status,
    )


@pytest.fixture
def db(db_session):
    """A session that already has one test document (DOC-TEST-001, version 1)."""
    db_session.add(Document(
        document_id=DOC, title="Test document", document_type="test", source_type="synthetic"
    ))
    db_session.add(version())
    db_session.flush()
    return db_session


def add_in_order(db, *rows) -> None:
    """Insert rows one by one. SQLAlchemy orders INSERTs by relationship() links only;
    for plain foreign-key columns we must insert parents before children ourselves."""
    for row in rows:
        db.add(row)
        db.flush()


@pytest.fixture
def curriculum(db):
    """University -> programme -> semester, a course, and an elective slot."""
    add_in_order(
        db,
        University(university_id="UNIV-TEST", name="Test University", **PROVENANCE),
        Program(program_id="PROG-TEST", program_name="Test Programme", short_name="T",
                university_id="UNIV-TEST", **PROVENANCE),
        Semester(semester_id="SEM-TEST-01", program_id="PROG-TEST", semester_number=1,
                 semester_name="Semester I", **PROVENANCE),
        Course(course_id="COURSE-T1", course_code="T1", course_name="Test Course",
               curriculum_status="test", **PROVENANCE),
        ElectiveGroup(elective_group_id="EGRP-TEST", semester_id="SEM-TEST-01",
                      group_name="ELECTIVE-I", slot_kind="elective", **PROVENANCE),
    )
    return db


def test_valid_row_with_provenance_is_accepted(db):
    db.add(Building(building_id="BLDG-T", code="T", name="Test Block", **PROVENANCE))
    db.flush()


def test_unknown_source_type_is_rejected(db):
    db.add(Building(building_id="BLDG-T", code="T", name="Test Block",
                    **{**PROVENANCE, "source_type": "rumour"}))
    with pytest.raises(IntegrityError, match="ck_buildings_source_type"):
        db.flush()


def test_fact_must_cite_an_existing_document_version(db):
    db.add(Building(building_id="BLDG-T", code="T", name="Test Block",
                    **{**PROVENANCE, "source_version_no": 99}))
    with pytest.raises(IntegrityError, match="fk_buildings_source_document_id"):
        db.flush()


def test_same_file_cannot_be_registered_twice(db):
    db.add(Document(document_id="DOC-TEST-002", title="Copy", document_type="test",
                    source_type="synthetic"))
    db.add(version(document_id="DOC-TEST-002", sha="a" * 64))  # same bytes as DOC-TEST-001 v1
    with pytest.raises(IntegrityError, match="uq_document_versions_sha256"):
        db.flush()


def test_only_one_active_version_per_document(db):
    db.add(version(version_no=2, sha="b" * 64, status="active"))
    with pytest.raises(IntegrityError, match="uq_document_versions_one_active"):
        db.flush()


def test_new_active_version_allowed_once_old_one_is_superseded(db):
    v1 = db.get(DocumentVersion, (DOC, 1))
    v1.status = "superseded"
    db.flush()
    db.add(version(version_no=2, sha="b" * 64, status="active"))
    db.flush()


def test_calendar_event_cannot_end_before_it_starts(db):
    db.add(CalendarEvent(event_id="CAL-T", title="Backwards", start_date=date(2026, 7, 10),
                         end_date=date(2026, 7, 1), **PROVENANCE))
    with pytest.raises(IntegrityError, match="ck_calendar_events_date_range"):
        db.flush()


def test_regular_offering_cannot_sit_in_an_elective_slot(curriculum):
    curriculum.add(CourseOffering(offering_id="OFF-T", course_id="COURSE-T1",
                                  semester_id="SEM-TEST-01", course_type="regular",
                                  elective_group_id="EGRP-TEST", **PROVENANCE))
    with pytest.raises(IntegrityError, match="ck_course_offerings_slot_matches_type"):
        curriculum.flush()


def test_teaching_requires_the_course_to_be_offered_that_semester(curriculum):
    add_in_order(
        curriculum,
        Department(department_id="DEPT-T", department_name="Test Dept",
                   university_id="UNIV-TEST", **PROVENANCE),
        Faculty(faculty_id="FAC-T", name="Test Teacher", department_id="DEPT-T", **PROVENANCE),
    )
    # COURSE-T1 has no offering in SEM-TEST-01.
    curriculum.add(TeachingAssignment(assignment_id="TA-T", faculty_id="FAC-T",
                                      course_id="COURSE-T1", semester_id="SEM-TEST-01",
                                      role="instructor", **PROVENANCE))
    with pytest.raises(IntegrityError, match="fk_teaching_assignments_course_id"):
        curriculum.flush()


def test_department_and_its_head_can_be_inserted_together(curriculum):
    # The department names its head before the faculty row exists: allowed because the
    # foreign key is DEFERRED, i.e. only checked when the transaction commits.
    curriculum.add(Department(department_id="DEPT-T", department_name="Test Dept",
                              university_id="UNIV-TEST", head_faculty_id="FAC-T", **PROVENANCE))
    curriculum.flush()
    curriculum.add(Faculty(faculty_id="FAC-T", name="Head", department_id="DEPT-T", **PROVENANCE))
    curriculum.flush()
    curriculum.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))  # force the check now: passes


def test_deferred_check_still_catches_a_missing_head(curriculum):
    curriculum.add(Department(department_id="DEPT-T", department_name="Test Dept",
                              university_id="UNIV-TEST", head_faculty_id="FAC-MISSING",
                              **PROVENANCE))
    curriculum.flush()  # not checked yet...
    with pytest.raises(IntegrityError, match="fk_departments_head_faculty_id"):
        curriculum.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))  # ...but checked here


def test_email_is_unique_regardless_of_case(db):
    db.add(Role(code="student", name="Student"))
    db.add(User(email="Asha@Example.com", password_hash="x", role_code="student"))
    db.flush()
    db.add(User(email="asha@example.com", password_hash="x", role_code="student"))
    with pytest.raises(IntegrityError, match="uq_users_email_lower"):
        db.flush()


@pytest.mark.parametrize("statement", [
    "UPDATE audit_logs SET action = 'tampered'",
    "DELETE FROM audit_logs",
    "TRUNCATE audit_logs",
])
def test_audit_log_is_append_only(db, statement):
    db.add(AuditLog(action="document.upload", entity_type="document", entity_id=DOC))
    db.flush()
    with pytest.raises(DBAPIError, match="audit_logs is append-only"):
        db.execute(text(statement))
