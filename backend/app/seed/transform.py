"""Step 2 of seeding: turn dataset records into rows for each table (pure Python, no database).

Each builder returns {table_name: [row_dict, ...]}. Fields that merely repeat another table
(e.g. faculty.courses_taught, laboratories.room_number) are dropped here; consistency.py later
proves they can be reproduced from the database, i.e. that nothing was lost.
"""

from decimal import Decimal

from app.seed.source import SourceData, parse_dmy_date, parse_iso_date
from app.services.storage import original_key

# Every dataset document is registered as version 1; records cite that version.
DATASET_VERSION_NO = 1

Rows = dict[str, list[dict]]


def provenance(record: dict) -> dict:
    return {
        "source_type": record["source_type"],
        "source_document_id": record["source_document"],
        "source_version_no": DATASET_VERSION_NO,
        "source_page": record.get("source_page"),
        "source_section": record.get("source_section"),
    }


def dec(value: float | None) -> Decimal | None:
    # Via str() so 4.0 becomes Decimal("4.0"), not a binary floating-point approximation.
    return None if value is None else Decimal(str(value))


def credit_scheme(scheme: dict) -> dict:
    return {
        "credit_th": dec(scheme["credit_th"]),
        "credit_pr": dec(scheme["credit_pr"]),
        "credit_total": dec(scheme["credit_total"]),
        "contact_hours": dec(scheme["contact_hours"]),
        "th_internal_max": scheme["th_internal_max"],
        "th_external_max": scheme["th_external_max"],
        "pr_internal_max": scheme["pr_internal_max"],
        "pr_external_max": scheme["pr_external_max"],
        "total_marks": scheme["total_marks"],
        "exam_raw": scheme["exam_raw"],
    }


def links(owner_col: str, owner_id: str, target_col: str, targets: list[str], **extra) -> list[dict]:
    return [{owner_col: owner_id, target_col: t, **extra} for t in targets]


def build_rows(src: SourceData) -> Rows:
    rows: Rows = {}
    for builder in (_documents, _organization, _campus, _people, _curriculum, _content):
        rows.update(builder(src))
    return rows


def _documents(src: SourceData) -> Rows:
    documents, versions, entities = [], [], []
    for doc in src.registry:
        doc_id, file = doc["document_id"], src.files[doc["document_id"]]
        documents.append({
            "document_id": doc_id,
            "title": doc["title"],
            "document_type": doc["document_type"],
            "source_type": doc["source_type"],
            "department_id": doc["department_id"],
            "source_url": doc["source_url"],
            "status": "active",
        })
        notes = [doc.get("note"), f"Origin: {doc['source_document']}",
                 f"Registry created_at: {doc['created_at']}"]
        # Registry dates that are not exact are kept here as text, and stored as NULL below.
        for field in ("effective_from", "effective_to"):
            if doc[field] and parse_iso_date(doc[field]) is None:
                notes.append(f"Registry {field} (not an exact date): {doc[field]}")
        versions.append({
            "document_id": doc_id,
            "version_no": DATASET_VERSION_NO,
            "sha256": file.sha256,
            "storage_key": original_key(file.sha256, file.path.suffix),
            "original_filename": doc["original_filename"] or doc["filename"],
            "mime_type": "application/pdf",
            "size_bytes": file.size_bytes,
            "page_count": doc["page_count"],
            "page_scope": doc.get("pages_used"),
            "version_label": doc["version"],
            "academic_year": doc["academic_year"],
            "effective_from": parse_iso_date(doc["effective_from"]),
            "effective_to": parse_iso_date(doc["effective_to"]),
            "status": "active",
            "notes": "\n".join(n for n in notes if n),
        })
        registry_pages = doc.get("entity_pages") or {}
        for entity_id in doc["entity_ids"]:
            pages = set(src.index_pages.get((doc_id, entity_id), set()))
            if entity_id in registry_pages:
                pages.add(registry_pages[entity_id])
            entities.append({
                "document_id": doc_id, "version_no": DATASET_VERSION_NO,
                "entity_id": entity_id, "pages": sorted(pages),
            })
    return {"documents": documents, "document_versions": versions, "document_entities": entities}


def _organization(src: SourceData) -> Rows:
    t = src.tables
    universities = [{
        "university_id": u["university_id"], "name": u["name"], "short_name": u["short_name"],
        "address": u["address"], "phone": u["phone"], "fax": u["fax"],
        "toll_free": u["toll_free"], "email": u["email"], "website": u["website"],
        "note": u["note"], **provenance(u),
    } for u in t["university"]]
    university_ids = {u["university_id"] for u in universities}

    # In the dataset `parent_id` is either the university or another org unit.
    org_units = []
    for o in t["org_units"]:
        parent_is_university = o["parent_id"] in university_ids
        org_units.append({
            "org_unit_id": o["org_unit_id"], "unit_type": o["unit_type"], "name": o["name"],
            "university_id": o["parent_id"] if parent_is_university else _university_of(o["parent_id"], t),
            "parent_org_unit_id": None if parent_is_university else o["parent_id"],
            **provenance(o),
        })

    departments = [{
        "department_id": d["department_id"], "department_name": d["department_name"],
        "short_name": d["short_name"], "university_id": d["university_id"],
        "parent_org_unit_id": d["parent_org_unit_id"], "parent_link_note": d["parent_link_note"],
        "head_faculty_id": d["head_faculty_id"], "office_room_id": d["office_room_id"],
        "overview": d["overview"], "vision": d["vision"], "mission": d["mission"],
        "focus_areas": d["focus_areas"], "contact": d["contact"], "status": d["status"],
        **provenance(d),
    } for d in t["departments"]]

    research_areas = [{
        "research_area_id": r["research_area_id"], "name": r["name"],
        "department_id": r["department_id"], **provenance(r),
    } for r in t["research_areas"]]
    return {"universities": universities, "org_units": org_units,
            "departments": departments, "research_areas": research_areas}


def _university_of(org_unit_id: str, t: dict) -> str:
    """Walk up the org-unit chain until the parent is the university."""
    units = {o["org_unit_id"]: o for o in t["org_units"]}
    parent = units[org_unit_id]["parent_id"]
    return parent if parent not in units else _university_of(parent, t)


def _campus(src: SourceData) -> Rows:
    t = src.tables
    return {
        "buildings": [{
            "building_id": b["building_id"], "code": b["code"], "name": b["name"],
            "floors": b["floors"], "description": b["description"], **provenance(b),
        } for b in t["buildings"]],
        "rooms": [{
            "room_id": r["room_id"], "room_number": r["room_number"], "building_id": r["building_id"],
            "floor": r["floor"], "room_type": r["room_type"], "label": r["label"], **provenance(r),
        } for r in t["rooms"]],
        "laboratories": [{
            "lab_id": lab["lab_id"], "lab_name": lab["lab_name"], "department_id": lab["department_id"],
            "room_id": lab["room_id"], "capacity": lab["capacity"], "equipment": lab["equipment"],
            "responsible_faculty_id": lab["responsible_faculty_id"],
            "opening_hours": lab["opening_hours"], "booking_contact": lab["booking_contact"],
            "status": lab["status"], **provenance(lab),
        } for lab in t["laboratories"]],
        "lab_courses": [
            row for lab in t["laboratories"]
            for row in links("lab_id", lab["lab_id"], "course_id", lab["related_courses"])
        ],
        "facilities": [{
            "facility_id": f["facility_id"], "facility_name": f["facility_name"],
            "facility_type": f["facility_type"], "department_id": f["department_id"],
            "room_id": f["room_id"], "description": f["description"], "capacity": f["capacity"],
            "availability": f["availability"], "status": f["status"], **provenance(f),
        } for f in t["facilities"]],
    }


def _people(src: SourceData) -> Rows:
    t = src.tables
    return {
        "faculty": [{
            "faculty_id": f["faculty_id"], "name": f["name"], "designation": f["designation"],
            "department_id": f["department_id"], "qualification": f["qualification"],
            "specialization": f["specialization"], "email": f["email"],
            "office_room_id": f["office_id"], "consultation_hours": f["consultation_hours"],
            "joining_year": f["joining_year"], "status": f["status"], **provenance(f),
        } for f in t["faculty"]],
        "faculty_research_areas": [
            row for f in t["faculty"]
            for row in links("faculty_id", f["faculty_id"], "research_area_id", f["research_area_ids"])
        ],
        "teaching_assignments": [{
            "assignment_id": a["assignment_id"], "faculty_id": a["faculty_id"],
            "course_id": a["course_id"], "semester_id": a["semester_id"], "role": a["role"],
            "academic_year": a["academic_year"], **provenance(a),
        } for a in t["teaching_assignments"]],
    }


def _curriculum(src: SourceData) -> Rows:
    t = src.tables
    return {
        "programs": [{
            "program_id": p["program_id"], "program_name": p["program_name"],
            "short_name": p["short_name"], "degree_type": p["degree_type"],
            "university_id": p["university_id"], "org_unit_id": p["org_unit_id"],
            "department_id": p["department_id"], "effective_year": p["effective_year"],
            "catalog_program_code": p["catalog_program_code"],
            "catalog_program_name": p["catalog_program_name"],
            "description": p["program_description"],
            "synthetic_description": p["synthetic_program_description"],
            "coordinator_faculty_id": p["synthetic_program_coordinator_faculty_id"],
            "field_provenance": p["field_provenance"], "additional_sources": p["additional_sources"],
            **provenance(p),
        } for p in t["programs"]],
        "semesters": [{
            "semester_id": s["semester_id"], "program_id": s["program_id"],
            "semester_number": s["semester_number"], "semester_name": s["semester_name"],
            "total_course": s["total_course"], "total_regular_course": s["total_regular_course"],
            "total_elective_course": s["total_elective_course"],
            "total_open_course": s["total_open_course"],
            "total_audit_course": s["total_audit_course"],
            "total_credits_th": dec(s["total_credits_th"]),
            "total_credits_pr": dec(s["total_credits_pr"]),
            "total_credits": dec(s["total_credits"]),
            "total_contact_hours": dec(s["total_contact_hours"]),
            "total_marks": s["total_marks"], "effective_year": s["effective_year"],
            "syllabus_date": parse_dmy_date(s["syllabus_date"]),
            "source_page_end": max(s["source_pages"]) if len(s["source_pages"]) > 1 else None,
            **provenance(s),
        } for s in t["semesters"]],
        "courses": [{
            "course_id": c["course_id"], "course_code": c["course_code"],
            "course_name": c["course_name"], "department_id": c["department_id"],
            "curriculum_status": c["curriculum_status"], "description": c["description"],
            "synthetic_description": c["synthetic_description"],
            "delivered_by_note": c["delivered_by_note"], "curriculum_note": c.get("curriculum_note"),
            "field_provenance": c["field_provenance"], **provenance(c),
        } for c in t["courses"]],
        "elective_groups": [{
            "elective_group_id": g["elective_group_id"], "semester_id": g["semester_id"],
            "group_name": g["group_name"], "slot_kind": g["slot_kind"],
            "slot_title": g["slot_title"], "slot_no": g["slot_no"],
            **credit_scheme(g["slot_scheme"]), **provenance(g),
        } for g in t["elective_groups"]],
        "course_offerings": [{
            "offering_id": o["offering_id"], "course_id": o["course_id"],
            "semester_id": o["semester_id"], "course_type": o["course_type"],
            "elective_group_id": o["elective_group_id"], "credit_basis": o["credit_scheme_basis"],
            **credit_scheme(o["credit_scheme"]), **provenance(o),
        } for o in t["course_offerings"]],
        "course_prerequisites": [{
            "prerequisite_id": p["prerequisite_id"], "course_id": p["course_id"],
            "requires_course_id": p["requires_course_id"], "strength": p["strength"],
            "academic_year": p["academic_year"], **provenance(p),
        } for p in t["course_prerequisites"]],
        "catalog_listings": [{
            "course_id": c["course_id"], "academic_year": entry["academic_year"],
            "catalog_program_code": entry["catalog_program_code"],
            "catalog_program_name": entry["catalog_program_name"],
            "listed_course_name": entry["listed_course_name"],
            "catalog_sr_no": entry["catalog_sr_no"], **provenance(entry),
        } for c in t["courses"] for entry in c["catalog_listings"]],
        "course_shared_listings": [{
            "course_id": c["course_id"], "program_short_name": entry["program_short_name"],
            "listed_line": entry["listed_line"], "title_matches": entry["title_matches"],
            **provenance(entry),
        } for c in t["courses"] for entry in c["shared_with_other_syllabus_programs"]],
        "grade_bands": [{
            "grade_band_id": g["grade_band_id"], "marks_range": g["marks_range"],
            "grade_regular": g["grade_regular"], "grade_point_regular": g["grade_point_regular"],
            "grade_remedial": g["grade_remedial"], "grade_point_remedial": g["grade_point_remedial"],
            **provenance(g),
        } for g in t["grading_scheme"]],
        "grade_band_programs": [
            row for g in t["grading_scheme"]
            for row in links("grade_band_id", g["grade_band_id"], "program_id", g["applies_to_program_ids"])
        ],
        "data_quality_conflicts": [{
            "conflict_id": d["conflict_id"], "course_code": d["course_code"],
            "syllabus_course_name": d["syllabus_course_name"],
            "catalog_course_name": d["catalog_course_name"], "academic_year": d["academic_year"],
            "catalog_program_code": d["catalog_program_code"],
            "catalog_program_name": d["catalog_program_name"],
            "interpretation": d["interpretation"], **provenance(d),
        } for d in t["data_quality_conflicts"]],
    }


def _content(src: SourceData) -> Rows:
    t = src.tables
    policy_links = []
    for p in t["policies"]:
        applies = p["applies_to_department_ids"] + p["applies_to_program_ids"]
        governs = p["related_course_ids"] + p["related_lab_ids"] + p["related_facility_ids"]
        policy_links += links("policy_id", p["policy_id"], "target_id", applies, relation="applies_to")
        policy_links += links("policy_id", p["policy_id"], "target_id", governs, relation="governs")

    notice_link_fields = ("related_course_ids", "related_faculty_ids", "related_lab_ids",
                          "related_facility_ids", "related_policy_ids", "related_calendar_ids")
    return {
        "policies": [{
            "policy_id": p["policy_id"], "policy_number": p["policy_number"], "title": p["title"],
            "category": p["category"], "owner_faculty_id": p["owner_faculty_id"],
            "summary": p["summary"], "clauses": p["clauses"],
            "effective_from": parse_iso_date(p["effective_from"]),
            "effective_to": parse_iso_date(p["effective_to"]),
            "status": p["status"], "academic_year": p["academic_year"], **provenance(p),
        } for p in t["policies"]],
        "policy_links": policy_links,
        "calendar_events": [{
            "event_id": e["event_id"], "title": e["title"], "event_type": e["event_type"],
            "start_date": parse_iso_date(e["start_date"]), "end_date": parse_iso_date(e["end_date"]),
            "term": e["term"], "department_id": e["department_id"],
            "academic_year": e["academic_year"], **provenance(e),
        } for e in t["academic_calendar"]],
        "calendar_event_semesters": [
            row for e in t["academic_calendar"]
            for row in links("event_id", e["event_id"], "semester_id", e["semester_ids"])
        ],
        "notices": [{
            "notice_id": n["notice_id"], "title": n["title"], "notice_date": parse_iso_date(n["date"]),
            "department_id": n["department_id"], "category": n["category"],
            "target_audience": n["target_audience"], "content": n["content"],
            "effective_date": parse_iso_date(n["effective_date"]),
            "expiry_date": parse_iso_date(n["expiry_date"]),
            "supersedes_notice_id": n["supersedes"], "academic_year": n["academic_year"],
            **provenance(n),
        } for n in t["notices"]],
        "notice_links": [
            row for n in t["notices"]
            for row in links("notice_id", n["notice_id"], "target_id",
                             sorted({x for f in notice_link_fields for x in n[f]}))
        ],
        "faq": [{
            "faq_id": q["faq_id"], "category": q["category"], "question": q["question"],
            "answer": q["answer"], "department_id": q["department_id"], "status": q["status"],
            "academic_year": q["academic_year"], **provenance(q),
        } for q in t["faq"]],
        "faq_links": [
            row for q in t["faq"]
            for row in links("faq_id", q["faq_id"], "target_id", q["related_entity_ids"])
        ],
    }
