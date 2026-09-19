"""Relationship edges, DERIVED from the relational data (foreign keys and link tables).

There is no stored "relationships" table: each predicate below is one SQL query over the
tables that already hold the fact. An edge's trust level (source_type) and citation come
from the row that states it, e.g. TEACHES from the (synthetic) teaching assignment,
OFFERED_IN from the (official or derived) course offering.

Validated against the dataset's 1,202-edge fixture (data/structured/relationships.json) by
`python -m app.knowledge validate` and the test suite.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Edge:
    subject_id: str
    predicate: str
    object_id: str
    source_type: str
    source_document_id: str | None
    source_page: int | None


def _p(alias: str = "") -> str:
    """The provenance columns of a row, as the last three columns of an edge query."""
    a = f"{alias}." if alias else ""
    return f"{a}source_type, {a}source_document_id, {a}source_page"


# predicate -> SQL returning (subject_id, object_id, source_type, source_document_id, source_page)
EDGE_QUERIES: dict[str, str] = {
    "HAS_ORG_UNIT": f"""
        SELECT university_id, org_unit_id, {_p()} FROM org_units WHERE parent_org_unit_id IS NULL
        UNION ALL
        SELECT parent_org_unit_id, org_unit_id, {_p()} FROM org_units WHERE parent_org_unit_id IS NOT NULL""",
    "HAS_DEPARTMENT": f"SELECT parent_org_unit_id, department_id, {_p()} FROM departments WHERE parent_org_unit_id IS NOT NULL",
    "HAS_RESEARCH_AREA": f"SELECT department_id, research_area_id, {_p()} FROM research_areas",
    "HAS_LAB": f"SELECT department_id, lab_id, {_p()} FROM laboratories",
    "HAS_FACILITY": f"SELECT department_id, facility_id, {_p()} FROM facilities",
    # The department link of a programme is part of the (synthetic) department data.
    "OFFERS": f"SELECT p.department_id, p.program_id, {_p('d')} FROM programs p JOIN departments d USING (department_id)",
    "HOSTED_BY": f"SELECT program_id, org_unit_id, {_p()} FROM programs WHERE org_unit_id IS NOT NULL",
    "COORDINATED_BY": f"""SELECT p.program_id, p.coordinator_faculty_id, {_p('f')}
                          FROM programs p JOIN faculty f ON f.faculty_id = p.coordinator_faculty_id""",
    "CONTAINS": f"""
        SELECT program_id, semester_id, {_p()} FROM semesters
        UNION ALL
        SELECT semester_id, course_id, {_p()} FROM course_offerings""",
    "OFFERED_IN": f"SELECT course_id, semester_id, {_p()} FROM course_offerings",
    # Official when the course is printed on its programme's syllabus pages; derived_official
    # for legacy courses, whose programme is inferred from the catalog programme code.
    "BELONGS_TO": """
        SELECT DISTINCT ON (o.course_id, s.program_id)
               o.course_id, s.program_id, 'official', c.source_document_id, c.source_page
        FROM course_offerings o JOIN semesters s USING (semester_id) JOIN courses c USING (course_id)
        UNION ALL
        SELECT DISTINCT ON (cl.course_id, p.program_id)
               cl.course_id, p.program_id, 'derived_official', cl.source_document_id, cl.source_page
        FROM catalog_listings cl JOIN programs p ON p.catalog_program_code = cl.catalog_program_code
        WHERE cl.course_id NOT IN (SELECT course_id FROM course_offerings)""",
    "HAS_ELECTIVE_GROUP": f"SELECT semester_id, elective_group_id, {_p()} FROM elective_groups",
    # The option list is printed in the official syllabus, so the slot's provenance applies.
    "HAS_OPTION": f"""SELECT o.elective_group_id, o.course_id, {_p('g')}
                      FROM course_offerings o JOIN elective_groups g USING (elective_group_id)""",
    "REQUIRES": f"SELECT course_id, requires_course_id, {_p()} FROM course_prerequisites",
    "WORKS_IN": f"SELECT faculty_id, department_id, {_p()} FROM faculty",
    "HEADS": f"SELECT head_faculty_id, department_id, {_p()} FROM departments WHERE head_faculty_id IS NOT NULL",
    "TEACHES": f"SELECT faculty_id, course_id, {_p()} FROM teaching_assignments",
    "RESEARCHES": f"""SELECT fra.faculty_id, fra.research_area_id, {_p('f')}
                      FROM faculty_research_areas fra JOIN faculty f USING (faculty_id)""",
    "HAS_OFFICE": f"SELECT faculty_id, office_room_id, {_p()} FROM faculty WHERE office_room_id IS NOT NULL",
    "PRACTICALS_IN": f"SELECT lc.course_id, lc.lab_id, {_p('l')} FROM lab_courses lc JOIN laboratories l USING (lab_id)",
    "MANAGED_BY": f"SELECT lab_id, responsible_faculty_id, {_p()} FROM laboratories WHERE responsible_faculty_id IS NOT NULL",
    "LOCATED_IN": f"""
        SELECT lab_id, room_id, {_p()} FROM laboratories WHERE room_id IS NOT NULL
        UNION ALL
        SELECT facility_id, room_id, {_p()} FROM facilities WHERE room_id IS NOT NULL""",
    "IN_BUILDING": f"SELECT room_id, building_id, {_p()} FROM rooms",
    "APPLIES_TO": f"""
        SELECT DISTINCT ces.event_id, s.program_id, {_p('e')}
        FROM calendar_event_semesters ces JOIN semesters s USING (semester_id) JOIN calendar_events e USING (event_id)
        UNION ALL
        SELECT ces.event_id, ces.semester_id, {_p('e')} FROM calendar_event_semesters ces JOIN calendar_events e USING (event_id)
        UNION ALL
        SELECT gbp.grade_band_id, gbp.program_id, {_p('g')} FROM grade_band_programs gbp JOIN grade_bands g USING (grade_band_id)
        UNION ALL
        SELECT notice_id, department_id, {_p()} FROM notices
        UNION ALL
        SELECT pl.policy_id, pl.target_id, {_p('p')} FROM policy_links pl JOIN policies p USING (policy_id)
        WHERE pl.relation = 'applies_to'""",
    "GOVERNS": f"""SELECT pl.policy_id, pl.target_id, {_p('p')} FROM policy_links pl JOIN policies p USING (policy_id)
                   WHERE pl.relation = 'governs'""",
    "OWNED_BY": f"SELECT policy_id, owner_faculty_id, {_p()} FROM policies WHERE owner_faculty_id IS NOT NULL",
    "MENTIONS": f"SELECT nl.notice_id, nl.target_id, {_p('n')} FROM notice_links nl JOIN notices n USING (notice_id)",
    "REFERENCES": f"SELECT fl.faq_id, fl.target_id, {_p('f')} FROM faq_links fl JOIN faq f USING (faq_id)",
    "SUPERSEDES": f"SELECT notice_id, supersedes_notice_id, {_p()} FROM notices WHERE supersedes_notice_id IS NOT NULL",
}

# How each relationship reads in both directions (used for OKF front-matter keys).
READINGS: dict[str, tuple[str, str]] = {
    "HAS_ORG_UNIT": ("has_org_unit", "part_of"), "HAS_DEPARTMENT": ("has_department", "part_of"),
    "HAS_RESEARCH_AREA": ("has_research_area", "research_area_of"), "HAS_LAB": ("has_lab", "lab_of"),
    "HAS_FACILITY": ("has_facility", "facility_of"), "OFFERS": ("offers", "offered_by"),
    "HOSTED_BY": ("hosted_by", "hosts"), "COORDINATED_BY": ("coordinated_by", "coordinates"),
    "CONTAINS": ("contains", "contained_in"), "OFFERED_IN": ("offered_in", "offers_course"),
    "BELONGS_TO": ("belongs_to", "has_course"), "HAS_ELECTIVE_GROUP": ("has_elective_group", "in_semester"),
    "HAS_OPTION": ("has_option", "option_of"), "REQUIRES": ("requires", "required_by"),
    "WORKS_IN": ("works_in", "has_member"), "HEADS": ("heads", "headed_by"), "TEACHES": ("teaches", "taught_by"),
    "RESEARCHES": ("researches", "researched_by"), "HAS_OFFICE": ("has_office", "office_of"),
    "PRACTICALS_IN": ("practicals_in", "practicals_for"), "MANAGED_BY": ("managed_by", "manages"),
    "LOCATED_IN": ("located_in", "houses"), "IN_BUILDING": ("in_building", "has_room"),
    "APPLIES_TO": ("applies_to", "subject_to"), "GOVERNS": ("governs", "governed_by"),
    "OWNED_BY": ("owned_by", "owns"), "MENTIONS": ("mentions", "mentioned_in"),
    "REFERENCES": ("references", "referenced_by"), "SUPERSEDES": ("supersedes", "superseded_by"),
}


def all_edges(db: Session) -> list[Edge]:
    edges = []
    for predicate, sql in EDGE_QUERIES.items():
        for subject_id, object_id, source_type, document_id, page in db.execute(text(sql)):
            edges.append(Edge(subject_id, predicate, object_id, source_type, document_id, page))
    return edges


def edges_of(edges: list[Edge], entity_id: str) -> list[tuple[Edge, str]]:
    """The edges touching one entity, each with its reading from that entity's side."""
    out = []
    for e in edges:
        if e.subject_id == entity_id:
            out.append((e, READINGS[e.predicate][0]))
        elif e.object_id == entity_id:
            out.append((e, READINGS[e.predicate][1]))
    return out
