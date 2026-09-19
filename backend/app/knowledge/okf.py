"""OKF items: one self-describing knowledge record per entity, GENERATED from PostgreSQL.

    ---                                   YAML front-matter: machine-readable
    id: COURSE-2CEIT602
    type: course
    source_type: official
    provenance: {document_id: DOC-OFFICIAL-SYLLABUS-001, version_no: 1, page: 15, ...}
    attributes: {...}
    relationships:
      taught_by: [{id: FAC-IT-002, source_type: synthetic}, ...]
    ---
    # 2CEIT602 ARTIFICIAL INTELLIGENCE    Markdown body: human-readable, every line labelled

The files are a derived VIEW: PostgreSQL stays the source of truth, and `python -m
app.knowledge generate` rebuilds all of them. They are never edited by hand.
"""

import json
import shutil
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import yaml
from sqlalchemy import select, union_all
from sqlalchemy.orm import Session

from app.knowledge.graph import Edge, all_edges, edges_of
from app.models.base import ProvenanceMixin, TimestampMixin
from app.models.content import CalendarEvent, Faq, Notice, Policy
from app.models.curriculum import Course, ElectiveGroup, GradeBand, Program, Semester
from app.models.organization import Department, OrgUnit, ResearchArea, University
from app.models.campus import Facility, Laboratory
from app.models.people import Faculty
from app.services.entities import entity_tables

# The entity types that get their own OKF item (the same 16 types as the dataset's OKF set).
OKF_TYPES = {
    "university": (University, lambda r: r.name),
    "org_unit": (OrgUnit, lambda r: r.name),
    "department": (Department, lambda r: r.department_name),
    "research_area": (ResearchArea, lambda r: r.name),
    "program": (Program, lambda r: f"{r.program_name} ({r.short_name})"),
    "semester": (Semester, lambda r: f"{r.program_id} {r.semester_name}"),
    "course": (Course, lambda r: f"{r.course_code} {r.course_name}"),
    "elective_group": (ElectiveGroup, lambda r: f"{r.group_name} ({r.slot_title or r.slot_kind})"),
    "grade_band": (GradeBand, lambda r: f"{r.marks_range} -> {r.grade_regular}"),
    "faculty": (Faculty, lambda r: r.name),
    "laboratory": (Laboratory, lambda r: r.lab_name),
    "facility": (Facility, lambda r: r.facility_name),
    "policy": (Policy, lambda r: f"{r.policy_number} {r.title}"),
    "calendar_event": (CalendarEvent, lambda r: r.title),
    "notice": (Notice, lambda r: r.title),
    "faq": (Faq, lambda r: r.question),
}
_SKIP = {c for c in ProvenanceMixin.__annotations__} | {c for c in TimestampMixin.__annotations__} | {"field_provenance"}


def _plain(value):
    """YAML/JSON-friendly values (dates as ISO strings, exact decimals as numbers)."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _attributes(row) -> dict:
    primary = row.__table__.primary_key.columns.keys()[0]
    return {c.key: _plain(getattr(row, c.key)) for c in row.__table__.columns
            if c.key not in _SKIP and c.key != primary and getattr(row, c.key) not in (None, [], {})}


def synthetic_entity_ids(db: Session) -> set[str]:
    return set(db.scalars(union_all(*(
        select(next(iter(t.primary_key.columns))).where(t.c.source_type == "synthetic") for t in entity_tables()))))


def attribute_source_types(row, attributes: dict, synthetic_ids: set[str]) -> dict[str, str]:
    """The trust level of each attribute of a (possibly mixed) record, most specific rule first:
    1. the record's own field_provenance; 2. fields named synthetic_*; 3. a value that points
    to a synthetic entity (e.g. department_id DEPT-IT-001); 4. the record's source_type."""
    field_provenance = getattr(row, "field_provenance", None) or {}
    labels = {}
    for key, value in attributes.items():
        declared = str(field_provenance.get(key, "")).split(" ")[0]
        if declared in ("official", "derived_official", "synthetic"):
            labels[key] = declared
        elif key.startswith("synthetic_") or (isinstance(value, str) and value in synthetic_ids):
            labels[key] = "synthetic"
        else:
            labels[key] = row.source_type
    return labels


def build_item(row, okf_type: str, edges: list[Edge], synthetic_ids: set[str]) -> dict:
    entity_id = getattr(row, row.__table__.primary_key.columns.keys()[0])
    attributes = _attributes(row)
    labels = attribute_source_types(row, attributes, synthetic_ids)
    relationships: dict[str, list[dict]] = {}
    for edge, reading in edges_of(edges, entity_id):
        other = edge.object_id if edge.subject_id == entity_id else edge.subject_id
        relationships.setdefault(reading, []).append({"id": other, "source_type": edge.source_type})
    return {
        "id": entity_id,
        "type": okf_type,
        "title": OKF_TYPES[okf_type][1](row),
        "source_type": row.source_type,
        "provenance": row.provenance,
        **({"field_provenance": row.field_provenance} if getattr(row, "field_provenance", None) else {}),
        "attributes": attributes,
        # Only the attributes whose trust level differs from the record's own source_type.
        "attribute_source_types": {k: v for k, v in labels.items() if v != row.source_type},
        "relationships": {k: sorted(v, key=lambda x: x["id"]) for k, v in sorted(relationships.items())},
        "last_updated": _plain(row.updated_at),
        "generated_from": "postgresql",
    }


def build_items(db: Session, edges: list[Edge] | None = None) -> list[dict]:
    edges = all_edges(db) if edges is None else edges
    synthetic_ids = synthetic_entity_ids(db)
    items = [build_item(row, okf_type, edges, synthetic_ids)
             for okf_type, (model, _) in OKF_TYPES.items() for row in db.scalars(select(model))]
    return sorted(items, key=lambda i: (i["type"], i["id"]))


def find_entity(db: Session, entity_id: str) -> tuple[str, object] | None:
    """(OKF type, database row) for an entity ID, or None if it is not an OKF entity."""
    for okf_type, (model, _) in OKF_TYPES.items():
        row = db.get(model, entity_id)
        if row is not None:
            return okf_type, row
    return None


def render_markdown(item: dict) -> str:
    """Front-matter + a readable body in which every fact carries its trust label."""
    front = yaml.safe_dump(item, sort_keys=False, allow_unicode=True, width=100)
    label = f"[{item['source_type']}]"
    lines = [f"# {item['title']}", "", f"{label} {item['type']} `{item['id']}`, "
             f"from {item['provenance']['document_id']} v{item['provenance']['version_no']}"
             + (f" p.{item['provenance']['page']}" if item["provenance"]["page"] else "") + ".", ""]
    if item["source_type"] == "synthetic":
        lines += ["> Synthetic demo data: NOT a Ganpat University fact.", ""]
    overrides = item["attribute_source_types"]
    lines += [f"- [{overrides.get(key, item['source_type'])}] **{key}**: {value}"
              for key, value in item["attributes"].items()]
    if item["relationships"]:
        lines += ["", "## Relationships", ""]
        for reading, targets in item["relationships"].items():
            lines.append(f"- **{reading}**: " + ", ".join(f"{t['id']} [{t['source_type']}]" for t in targets))
    return f"---\n{front}---\n\n" + "\n".join(lines) + "\n"


def write_items(db: Session, out_dir: Path) -> dict:
    """Regenerate the whole OKF folder atomically: build into a temporary folder, then swap,
    so a reader never sees half an old and half a new knowledge base."""
    edges = all_edges(db)
    items = build_items(db, edges)
    staging = out_dir.with_name(out_dir.name + ".new")
    shutil.rmtree(staging, ignore_errors=True)
    for item in items:
        path = staging / item["type"] / f"{item['id']}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(item), encoding="utf-8")
    (staging / "index.json").write_text(json.dumps(
        [{"id": i["id"], "type": i["type"], "title": i["title"], "source_type": i["source_type"],
          "path": f"{i['type']}/{i['id']}.md"} for i in items], indent=1, ensure_ascii=False), encoding="utf-8")
    with (staging / "relationships.jsonl").open("w", encoding="utf-8") as f:
        for e in edges:
            f.write(json.dumps(e.__dict__, ensure_ascii=False) + "\n")
    _swap_in(staging, out_dir)
    return {"items": len(items), "edges": len(edges), "folder": str(out_dir)}


def _swap_in(staging: Path, target: Path, attempts: int = 10) -> None:
    """Replace `target` with `staging`. On Windows a folder with freshly written files can be
    briefly locked (e.g. by an antivirus scan), so the swap is retried for a few seconds."""
    for attempt in range(1, attempts + 1):
        try:
            shutil.rmtree(target, ignore_errors=True)
            staging.rename(target)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(0.3 * attempt)
