"""Step 5 of seeding: prove that normalization lost nothing.

For every dataset field we chose NOT to store (because it repeats other data), rebuild it
from the database and compare it with the original JSON value. A mismatch means our schema
dropped real information, and the seed is rolled back.
"""

from collections import defaultdict
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.seed.source import SourceData

# The dataset's notice statuses were computed "as of" its generation date (audit check 27).
DATASET_AS_OF = date(2026, 9, 18)

# How a notice's status is computed from stored facts (also the rule the API will use).
NOTICE_STATUS_SQL = """
    SELECT n.notice_id,
           CASE WHEN EXISTS (SELECT 1 FROM notices newer WHERE newer.supersedes_notice_id = n.notice_id)
                     THEN 'superseded'
                WHEN n.expiry_date < :as_of THEN 'expired'
                ELSE 'active' END
    FROM notices n
"""


def check_consistency(session: Session, src: SourceData) -> list[str]:
    t = src.tables
    problems: list[str] = []

    def db_pairs(sql: str, **params) -> dict[str, set]:
        """Run a 2-column query and group it: {first column: {second column values}}."""
        grouped = defaultdict(set)
        for key, value in session.execute(text(sql), params):
            grouped[key].add(value)
        return dict(grouped)

    def db_values(sql: str, **params) -> dict:
        return {key: value for key, value in session.execute(text(sql), params)}

    def compare(label: str, from_json: dict, from_db: dict) -> None:
        # Empty collections in JSON correspond to "no rows" in the database.
        from_json = {k: v for k, v in from_json.items() if v not in (set(), None)}
        diffs = sorted(k for k in from_json.keys() | from_db.keys() if from_json.get(k) != from_db.get(k))
        if diffs:
            problems.append(f"{label}: {len(diffs)} mismatches, e.g. {diffs[:3]}")

    # --- courses: programme, semesters, staff, labs, prerequisites, credits --------------
    compare("courses.semester_ids",
            {c["course_id"]: set(c["semester_ids"]) for c in t["courses"]},
            db_pairs("SELECT course_id, semester_id FROM course_offerings"))
    compare("courses.program_ids (via offering -> semester)",
            {c["course_id"]: set(c["program_ids"]) for c in t["courses"] if c["semester_ids"]},
            db_pairs("SELECT o.course_id, s.program_id FROM course_offerings o JOIN semesters s USING (semester_id)"))
    compare("courses.program_ids of legacy courses (via catalog programme code)",
            {c["course_id"]: set(c["program_ids"]) for c in t["courses"] if not c["semester_ids"]},
            db_pairs("SELECT DISTINCT cl.course_id, p.program_id FROM catalog_listings cl "
                     "JOIN programs p ON p.catalog_program_code = cl.catalog_program_code "
                     "WHERE cl.course_id NOT IN (SELECT course_id FROM course_offerings)"))
    offered_as = defaultdict(set)
    for course_id, credits, course_type in session.execute(
            text("SELECT course_id, credit_total, course_type FROM course_offerings")):
        offered_as[course_id].add((float(credits), course_type))
    compare("courses.credits + course_type (via offerings)",
            {c["course_id"]: {(float(c["credits"]), c["course_type"])} for c in t["courses"] if c["semester_ids"]},
            dict(offered_as))
    compare("courses.faculty_ids",
            {c["course_id"]: set(c["faculty_ids"]) for c in t["courses"]},
            db_pairs("SELECT course_id, faculty_id FROM teaching_assignments"))
    compare("courses.lab_ids",
            {c["course_id"]: set(c["lab_ids"]) for c in t["courses"]},
            db_pairs("SELECT course_id, lab_id FROM lab_courses"))
    compare("courses.synthetic_prerequisites",
            {c["course_id"]: set(c["synthetic_prerequisites"]) for c in t["courses"]},
            db_pairs("SELECT course_id, requires_course_id FROM course_prerequisites"))

    # --- programmes, semesters, elective slots -------------------------------------------
    compare("programs.semester_ids",
            {p["program_id"]: set(p["semester_ids"]) for p in t["programs"]},
            db_pairs("SELECT program_id, semester_id FROM semesters"))
    compare("programs.total_credits + number_of_semesters",
            {p["program_id"]: (float(p["total_credits"]), p["number_of_semesters"]) for p in t["programs"]},
            {k: (float(total), n) for k, total, n in session.execute(text(
                "SELECT program_id, SUM(total_credits), COUNT(*) FROM semesters GROUP BY program_id"))})
    compare("course_offerings.program_id (via semester)",
            {o["offering_id"]: o["program_id"] for o in t["course_offerings"]},
            db_values("SELECT o.offering_id, s.program_id FROM course_offerings o JOIN semesters s USING (semester_id)"))
    compare("elective_groups.program_id (via semester)",
            {g["elective_group_id"]: g["program_id"] for g in t["elective_groups"]},
            db_values("SELECT g.elective_group_id, s.program_id FROM elective_groups g JOIN semesters s USING (semester_id)"))
    compare("elective_groups.option_course_ids (via offerings)",
            {g["elective_group_id"]: set(g["option_course_ids"]) for g in t["elective_groups"]},
            db_pairs("SELECT elective_group_id, course_id FROM course_offerings WHERE elective_group_id IS NOT NULL"))

    # --- faculty and department ----------------------------------------------------------
    compare("faculty.courses_taught",
            {f["faculty_id"]: set(f["courses_taught"]) for f in t["faculty"]},
            db_pairs("SELECT faculty_id, course_id FROM teaching_assignments"))
    compare("faculty.is_hod (via departments.head_faculty_id)",
            {f["faculty_id"]: f["is_hod"] for f in t["faculty"]},
            db_values("SELECT f.faculty_id, EXISTS (SELECT 1 FROM departments d "
                      "WHERE d.head_faculty_id = f.faculty_id) FROM faculty f"))
    compare("faculty.research_areas (names)",
            {f["faculty_id"]: set(f["research_areas"]) for f in t["faculty"]},
            db_pairs("SELECT fra.faculty_id, ra.name FROM faculty_research_areas fra "
                     "JOIN research_areas ra USING (research_area_id)"))
    department_lists = {
        "program_ids": "SELECT department_id, program_id FROM programs",
        "research_area_ids": "SELECT department_id, research_area_id FROM research_areas",
        "lab_ids": "SELECT department_id, lab_id FROM laboratories",
        "facility_ids": "SELECT department_id, facility_id FROM facilities",
    }
    for field, sql in department_lists.items():
        compare(f"departments.{field}",
                {d["department_id"]: set(d[field]) for d in t["departments"]}, db_pairs(sql))

    # --- laboratories and facilities: location follows from the room ----------------------
    compare("laboratories building/floor/room_number (via room)",
            {lab["lab_id"]: (lab["building_id"], lab["building"], lab["floor"], lab["room_number"])
             for lab in t["laboratories"]},
            {k: (b, bn, fl, rn) for k, b, bn, fl, rn in session.execute(text(
                "SELECT l.lab_id, r.building_id, b.name, r.floor, r.room_number FROM laboratories l "
                "JOIN rooms r USING (room_id) JOIN buildings b USING (building_id)"))})
    compare("laboratories.governing_policy_ids",
            {lab["lab_id"]: set(lab["governing_policy_ids"]) for lab in t["laboratories"]},
            db_pairs("SELECT target_id, policy_id FROM policy_links WHERE relation = 'governs' "
                     "AND target_id IN (SELECT lab_id FROM laboratories)"))
    compare("facilities.location (via room)",
            {f["facility_id"]: f["location"] for f in t["facilities"]},
            db_values("SELECT f.facility_id, b.name || ', Floor ' || r.floor || ', Room ' || r.room_number "
                      "FROM facilities f JOIN rooms r USING (room_id) JOIN buildings b USING (building_id)"))

    # --- calendar and notices --------------------------------------------------------------
    compare("academic_calendar.program_ids (via semesters)",
            {e["event_id"]: set(e["program_ids"]) for e in t["academic_calendar"]},
            db_pairs("SELECT ces.event_id, s.program_id FROM calendar_event_semesters ces "
                     "JOIN semesters s USING (semester_id)"))
    compare("notices.superseded_by (reverse of supersedes)",
            {n["notice_id"]: n["superseded_by"] for n in t["notices"]},
            db_values("SELECT supersedes_notice_id, notice_id FROM notices WHERE supersedes_notice_id IS NOT NULL"))
    compare(f"notices.status (computed as of {DATASET_AS_OF})",
            {n["notice_id"]: n["status"] for n in t["notices"]},
            db_values(NOTICE_STATUS_SQL, as_of=DATASET_AS_OF))
    return problems
