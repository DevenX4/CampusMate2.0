"""Evidence gathering: run each intent of a route decision and return uniform Evidence items,
each with its own trust level and citation. This is the context the answer is built from.

Structured and graph evidence come first (exact facts), document passages after them.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.graph import Edge, all_edges, edges_of
from app.knowledge.okf import OKF_TYPES, build_item, find_entity, synthetic_entity_ids
from app.models.curriculum import GradeBand
from app.retrieval.embeddings import Embedder
from app.retrieval.search import Bm25Cache, SearchFilters, hybrid_search
from app.retrieval.vector_index import VectorIndex
from app.routing.router import RouteDecision
from app.schemas.search import Citation
from app.services import courses as course_service
from app.services import organization
from app.services.errors import NotFoundError

MAX_GRAPH_ITEMS = 10
# Hub entities (a programme links to 100+ courses) are named in relationships, but never
# become evidence items of their own unless the question asked about them directly.
_HUBS = ("PROG-", "SEM-", "EGRP-", "DEPT-", "UNIV-", "SCHOOL-", "COLLEGE-", "DOC-")


@dataclass
class Table:
    """The same structured facts as the evidence text, as rows for the UI to show as a table."""
    title: str
    columns: list[str]
    rows: list[list[str]]


@dataclass
class Evidence:
    kind: str  # structured | graph | document
    text: str
    source_type: str
    citation: Citation
    entity_ids: list[str] = field(default_factory=list)
    score: float = 1.0
    table: Table | None = None


@dataclass
class RetrievalDeps:
    embedder: Embedder
    index: VectorIndex
    bm25: Bm25Cache


def _citation(provenance: dict, title: str, document_type: str = "structured_record") -> Citation:
    return Citation(document_id=provenance["document_id"], version_no=provenance["version_no"], title=title,
                    document_type=document_type, page_start=provenance["page"], page_end=provenance["page"],
                    section=provenance.get("section"))


def _num(value) -> str:
    return "–" if value is None else f"{value:g}"


def _credits(c) -> str:
    return (f"{c.total:g} credits (theory {c.theory:g} + practical/TW {c.practical:g}), "
            f"{c.contact_hours:g} contact hours" if c.total is not None else "credits not stated")


# --- structured -------------------------------------------------------------------------------

def course_facts(db: Session, course_ids: list[str]) -> list[Evidence]:
    evidence = []
    for course_id in course_ids[:3]:
        course = course_service.get_course(db, course_id)
        if course.offerings:
            table = Table(f"{course.course_code} {course.course_name}",
                          ["Programme", "Semester", "Type", "Credits (T + P)", "Contact hours", "Total marks"],
                          [[o.program.short_name, o.semester.semester_name,
                            o.course_type.capitalize() + (f" ({o.elective_group_id})" if o.elective_group_id else ""),
                            f"{_num(o.credits.total)} ({_num(o.credits.theory)} + {_num(o.credits.practical)})",
                            _num(o.credits.contact_hours), _num(o.marks.total)] for o in course.offerings])
        for i, o in enumerate(course.offerings):
            evidence.append(Evidence(
                "structured",
                f"{course.course_code} {course.course_name}: {_credits(o.credits)}, {o.marks.total} total marks; "
                f"{o.course_type} course in {o.program.short_name} {o.semester.semester_name}"
                + (f" (slot {o.elective_group_id})" if o.elective_group_id else "") + ".",
                o.provenance.source_type, _citation(o.provenance.model_dump(), f"{course.course_code} {course.course_name}"),
                [course.course_id, o.semester.semester_id], table=table if i == 0 else None))
        if not course.offerings:  # legacy courses: only the official catalog lists them
            for entry in course.catalog_listings[:3]:
                evidence.append(Evidence(
                    "structured", f"{course.course_code} {entry.listed_course_name} is listed in the official "
                    f"employability course list for {entry.academic_year} under programme code "
                    f"{entry.catalog_program_code}; it is not part of the 2021-2022 syllabus.",
                    entry.provenance.source_type, _citation(entry.provenance.model_dump(), course.course_name),
                    [course.course_id]))
    return evidence


def semester_courses(db: Session, semester_ids: list[str], question: str) -> list[Evidence]:
    electives_only = bool(re.search(r"\belectives?\b", question, re.I))
    evidence = []
    for semester_id in semester_ids[:2]:
        try:
            s = organization.get_semester(db, semester_id)
        except NotFoundError:
            continue
        parts = []
        if not electives_only:
            parts.append("regular courses: " + "; ".join(
                f"{r.course.course_code} {r.course.course_name} ({r.credits.total:g} cr)" for r in s.regular_courses))
        parts += [f"{slot.group_name} ({slot.slot_kind}, {slot.credits.total:g} cr), choose one of: "
                  + ", ".join(f"{c.course_code} {c.course_name}" for c in slot.options) for slot in s.elective_slots]
        rows = [] if electives_only else [
            [r.course.course_code, r.course.course_name, _num(r.credits.total), r.course_type.capitalize()] for r in s.regular_courses]
        rows += [[c.course_code, c.course_name, _num(slot.credits.total), f"{slot.group_name} (choose one)"]
                 for slot in s.elective_slots for c in slot.options]
        evidence.append(Evidence(
            "structured", f"{s.program.short_name} {s.semester_name} ({s.total_credits:g} credits in total): "
            + " | ".join(parts), s.provenance.source_type,
            _citation(s.provenance.model_dump(), f"{s.program.short_name} {s.semester_name}"),
            [semester_id] + [r.course.course_id for r in s.regular_courses]
            + [c.course_id for slot in s.elective_slots for c in slot.options],
            table=Table(f"{s.program.short_name} {s.semester_name} · {s.total_credits:g} credits in total",
                        ["Course code", "Course title", "Credits", "Classification"], rows)))
    return evidence


def program_summary(db: Session, program_ids: list[str]) -> list[Evidence]:
    evidence = []
    for program_id in program_ids[:2]:
        p = organization.get_program(db, program_id)
        per_semester = ", ".join(f"{s.semester_name.replace('Semester ', 'Sem ')}: {s.total_credits:g}" for s in p.semesters)
        evidence.append(Evidence(
            "structured", f"{p.program_name} ({p.short_name}): {p.semester_count} semesters and "
            f"{p.total_credits:g} credits in total, computed from the official semester totals ({per_semester}).",
            "derived_official", _citation(p.provenance.model_dump(), p.short_name), [program_id]
            + [s.semester_id for s in p.semesters],
            table=Table(f"{p.program_name} · {p.total_credits:g} credits in total", ["Semester", "Credits"],
                        [[s.semester_name, _num(s.total_credits)] for s in p.semesters])))
    return evidence


def elective_slot_options(db: Session, decision: RouteDecision, question: str) -> list[Evidence]:
    res = decision.resolution
    wanted = set(res.of_type("EGRP"))
    slot_name = re.search(r"\belective[-\s]*(viii|vii|vi|iv|v|iii|ii|i)\b", question, re.I)
    semesters = res.semester_ids or [g.rsplit("-", 2)[0].replace("EGRP-", "SEM-") for g in wanted]
    evidence = []
    for semester_id in dict.fromkeys(semesters):
        try:
            s = organization.get_semester(db, semester_id)
        except NotFoundError:
            continue
        for slot in s.elective_slots:
            if slot.elective_group_id in wanted or (slot_name and slot.group_name.upper() == f"ELECTIVE-{slot_name.group(1).upper()}"):
                evidence.append(Evidence(
                    "structured", f"{slot.group_name} in {s.program.short_name} {s.semester_name} has "
                    f"{len(slot.options)} options ({slot.credits.total:g} credits): "
                    + ", ".join(f"{c.course_code} {c.course_name}" for c in slot.options) + ".",
                    slot.provenance.source_type, _citation(slot.provenance.model_dump(), slot.group_name),
                    [slot.elective_group_id] + [c.course_id for c in slot.options],
                    table=Table(f"{slot.group_name} · {s.program.short_name} {s.semester_name} · choose one",
                                ["Course code", "Course title", "Credits"],
                                [[c.course_code, c.course_name, _num(slot.credits.total)] for c in slot.options])))
    return evidence


def _band_range(marks_range: str) -> tuple[float, float]:
    if m := re.fullmatch(r"\s*(\d+)\s*>=\s*", marks_range):
        return float(m.group(1)), 100.0
    if m := re.fullmatch(r"\s*(\d+)\s*to\s*(\d+)\s*", marks_range, re.I):
        return float(m.group(1)), float(m.group(2)) + 0.99
    if m := re.fullmatch(r"\s*<\s*(\d+)\s*", marks_range):
        return 0.0, float(m.group(1)) - 0.01
    raise ValueError(f"unknown marks range {marks_range!r}")


def grade_for_marks(db: Session, numbers: list[float]) -> list[Evidence]:
    evidence = []
    for band in db.scalars(select(GradeBand)):
        low, high = _band_range(band.marks_range)
        for marks in numbers:
            if low <= marks <= high:
                evidence.append(Evidence(
                    "structured", f"{marks:g} marks falls in the band '{band.marks_range}': grade {band.grade_regular} "
                    f"(grade point {band.grade_point_regular}) for regular students, {band.grade_remedial} "
                    f"({band.grade_point_remedial}) for remedial.", band.source_type,
                    _citation(band.provenance, "Examination grade range & value"), [band.grade_band_id],
                    table=Table(f"Grade for {marks:g} marks", ["Marks band", "Grade", "Grade point",
                                                              "Grade (remedial)", "Grade point (remedial)"],
                                [[band.marks_range, band.grade_regular, str(band.grade_point_regular),
                                  band.grade_remedial, str(band.grade_point_remedial)]])))
    return evidence


# --- graph ------------------------------------------------------------------------------------

def _item_text(item: dict, titles: dict[str, str]) -> str:
    overrides = item["attribute_source_types"]
    attributes = "; ".join(f"{k}: {v}" + (f" [{overrides[k]}]" if k in overrides else "")
                           for k, v in item["attributes"].items() if not isinstance(v, (dict, list)))[:600]
    relations = "; ".join(
        f"{reading}: " + ", ".join(f"{t['id']}" + (f" ({titles[t['id']]})" if t["id"] in titles else "")
                                   + f" [{t['source_type']}]" for t in targets[:8])
        for reading, targets in item["relationships"].items())
    return f"{item['title']} ({item['type']} {item['id']}, {item['source_type']}). {attributes}. Relationships: {relations}"


def graph_evidence(db: Session, entity_ids: list[str], edges: list[Edge] | None = None) -> list[Evidence]:
    """The resolved entities and their neighbourhood (up to 2 hops, hubs not expanded)."""
    edges = all_edges(db) if edges is None else edges
    synthetic = synthetic_entity_ids(db)
    order, frontier = [], [e for e in entity_ids if not e.startswith(("PROG-", "SEM-"))][:3]
    for _depth in range(3):  # the entities themselves, then 2 hops
        next_frontier = []
        for entity_id in frontier:
            if entity_id in order or len(order) >= MAX_GRAPH_ITEMS:
                continue
            order.append(entity_id)
            for edge, _ in edges_of(edges, entity_id):
                other = edge.object_id if edge.subject_id == entity_id else edge.subject_id
                # Hubs are skipped, and so are content items (notices, FAQ, calendar), which
                # document retrieval covers better.
                if not other.startswith(_HUBS + ("NOTICE-", "FAQ-", "CAL-")):
                    next_frontier.append(other)
        frontier = next_frontier
    found = {entity_id: find_entity(db, entity_id) for entity_id in order}
    titles = {i: OKF_TYPES[f[0]][1](f[1]) for i, f in found.items() if f}
    evidence = []
    for entity_id, hit in found.items():
        if hit is None:
            continue
        item = build_item(hit[1], hit[0], edges, synthetic)
        evidence.append(Evidence("graph", _item_text(item, titles), item["source_type"],
                                 _citation(item["provenance"], item["title"], "knowledge_graph"),
                                 [entity_id] + [t["id"] for ts in item["relationships"].values() for t in ts]))
    return evidence


# --- all together -------------------------------------------------------------------------------

def gather(db: Session, question: str, decision: RouteDecision, deps: RetrievalDeps, k_documents: int = 5) -> list[Evidence]:
    res, evidence = decision.resolution, []
    for intent in decision.intents:
        if intent == "course_facts":
            evidence += course_facts(db, res.of_type("COURSE"))
        elif intent == "semester_courses":
            evidence += semester_courses(db, res.semester_ids, question)
        elif intent == "program_summary":
            evidence += program_summary(db, res.program_ids)
        elif intent == "elective_slot_options":
            evidence += elective_slot_options(db, decision, question)
        elif intent == "grade_for_marks":
            evidence += grade_for_marks(db, res.numbers)
        elif intent in ("entity_relations", "entity_lookup"):
            evidence += graph_evidence(db, res.entity_ids)
        elif intent == "documents":
            filters = SearchFilters(source_types=["official"] if res.official_only else [])
            for hit in hybrid_search(db, deps.embedder, deps.index, deps.bm25, question, k_documents, filters):
                evidence.append(Evidence("document", hit.text, hit.source_type, hit.citation, hit.entity_ids, hit.score))
    return evidence
