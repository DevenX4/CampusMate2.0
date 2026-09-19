"""Catalog API against the real seeded dataset. Expected values come from the official
GUNI syllabus (e.g. 2CEIT602 = ARTIFICIAL INTELLIGENCE, 4 credits, p.15) or the labelled
synthetic data, never from the Stitch mockups."""

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app

API = "/api/v1"


@pytest.fixture(scope="module")
def api(seeded_session):
    # Dependency injection: endpoints ask for get_db; in these tests they get the seeded session.
    app.dependency_overrides[get_db] = lambda: seeded_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def get_ok(api, path: str, **params) -> dict | list:
    response = api.get(API + path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# --- courses -------------------------------------------------------------------------------

def test_search_finds_course_by_name(api):
    page = get_ok(api, "/courses", q="artificial")
    assert [c["course_code"] for c in page["items"]] == ["2CEIT602"]
    assert page["items"][0]["course_name"] == "ARTIFICIAL INTELLIGENCE"


def test_exact_code_lookup_is_case_insensitive(api):
    page = get_ok(api, "/courses", code="2ceit602")
    assert page["total"] == 1 and page["items"][0]["course_id"] == "COURSE-2CEIT602"


def test_search_wildcards_are_literal(api):
    # "%" must not act as "match everything".
    assert get_ok(api, "/courses", q="%")["total"] == 0


def test_filter_by_semester_and_type(api):
    regular = get_ok(api, "/courses", semester_id="SEM-BTECH-IT-06", course_type="regular", limit=100)
    assert {c["course_code"] for c in regular["items"]} == {
        "2CEIT601", "2CEIT602", "2CEIT603", "2CEIT604", "2CEIT605", "2HS6101"}


def test_pagination(api):
    first = get_ok(api, "/courses", limit=5, offset=0)
    second = get_ok(api, "/courses", limit=5, offset=5)
    assert first["total"] == second["total"] == 116
    assert len(first["items"]) == len(second["items"]) == 5
    assert not {c["course_id"] for c in first["items"]} & {c["course_id"] for c in second["items"]}
    assert get_ok(api, "/courses", offset=500)["items"] == []


def test_course_detail_keeps_official_and_synthetic_apart(api):
    course = get_ok(api, "/courses/COURSE-2CEIT602")
    offering = course["offerings"][0]
    assert offering["semester"]["semester_id"] == "SEM-BTECH-IT-06"
    assert offering["credits"] == {"theory": 3.0, "practical": 1.0, "total": 4.0, "contact_hours": 5.0}
    assert offering["provenance"] == {
        "source_type": "official", "document_id": "DOC-OFFICIAL-SYLLABUS-001",
        "version_no": 1, "page": 15, "section": "B.TECH-IT Semester VI \u2013 course table"}
    # Teaching staff exist only in the synthetic demo data and must say so.
    assert {t["faculty"]["faculty_id"] for t in course["taught_by"]} == {"FAC-IT-002", "FAC-IT-004"}
    assert {t["provenance"]["source_type"] for t in course["taught_by"]} == {"synthetic"}
    assert course["description"] is None  # no official description exists; nothing is invented


# --- programmes and semesters --------------------------------------------------------------

def test_program_totals_are_computed(api):
    program = get_ok(api, "/programs/PROG-BTECH-IT-001")
    assert program["semester_count"] == 8
    assert program["total_credits"] == 174.0
    assert program["coordinator"]["source_type"] == "synthetic"
    assert [s["semester_number"] for s in program["semesters"]] == list(range(1, 9))


def test_semester_lists_regular_courses_and_elective_slots(api):
    semester = get_ok(api, "/semesters/SEM-BTECH-IT-06")
    assert semester["program"]["program_id"] == "PROG-BTECH-IT-001"
    assert len(semester["regular_courses"]) == 6
    slots = {s["group_name"]: s for s in semester["elective_slots"]}
    assert set(slots) == {"ELECTIVE-III", "ELECTIVE-IV"}
    assert all(slot["options"] for slot in slots.values())


# --- departments and faculty ---------------------------------------------------------------

def test_department_is_synthetic_with_head(api):
    department = get_ok(api, "/departments/DEPT-IT-001")
    assert department["provenance"]["source_type"] == "synthetic"
    assert department["head"]["faculty_id"] == "FAC-IT-001"


def test_faculty_list_and_head_flag(api):
    assert get_ok(api, "/faculty", department_id="DEPT-IT-001")["total"] == 20
    assert get_ok(api, "/faculty/FAC-IT-001")["is_head_of_department"] is True
    member = get_ok(api, "/faculty/FAC-IT-002")
    assert member["is_head_of_department"] is False
    assert "COURSE-2CEIT602" in {t["course"]["course_id"] for t in member["teaching"]}


def test_every_listed_item_carries_provenance(api):
    for path in ("/courses", "/faculty"):
        for item in get_ok(api, path, limit=100)["items"]:
            assert item["provenance"]["source_type"] in {"official", "derived_official", "synthetic"}
    for path in ("/programs", "/departments"):
        assert all("provenance" in item for item in get_ok(api, path))


# --- errors --------------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/courses/COURSE-NOPE", "/programs/PROG-NOPE", "/semesters/SEM-NOPE",
    "/departments/DEPT-NOPE", "/faculty/FAC-NOPE",
])
def test_unknown_ids_return_structured_404(api, path):
    response = api.get(API + path)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_invalid_query_parameters_return_structured_422(api):
    response = api.get(API + "/courses", params={"limit": 0, "course_type": "banana"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert {d["location"] for d in error["details"]} == {"query.limit", "query.course_type"}
