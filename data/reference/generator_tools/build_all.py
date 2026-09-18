import json, csv, os, shutil, hashlib, collections, yaml
import assemble as A, official_model as om, synthetic_data as sd, render_pdfs as rp

OUT = "/home/claude/CampusMate_Dataset"
GEN = A.GENERATED_AT
if os.path.exists(OUT): shutil.rmtree(OUT)
for p in ["official/extracted", "synthetic/pdf", "synthetic/structured/csv", "knowledge/OKF_style", "registry", "evaluation", "sql", "audit"]:
    os.makedirs(f"{OUT}/{p}", exist_ok=True)
shutil.copy("/home/claude/src/syllabus.pdf", f"{OUT}/official/GUNI_BTech_IT_Syllabus.pdf")
shutil.copy("/home/claude/src/catalog.pdf", f"{OUT}/official/GUNI_Course_Catalog.pdf")

T = A.assemble()
R = A.relationships(T)

# ------------------------------------------------------------------ document metadata
def dm(doc_id, fn, dtype, title, counterparts, stypes, entity_ids):
    return {"document_id": doc_id, "filename": fn, "document_type": dtype, "title": title, "version": "1.0",
            "academic_year": sd.AY, "generated_at": GEN, "source_type": "synthetic", "contains_source_types": stypes,
            "department_id": "DEPT-IT-001", "status": "active", "structured_counterparts": counterparts, "entity_ids": entity_ids}
ids = lambda t: [r[A.ID_FIELDS[t]] for r in T[t]]
DOCS = [
 dm("DOC-DEPT-PROFILE-001", "Department_Profile.pdf", "department_profile", "Department Profile — Department of Information Technology (DEPT-IT-001)",
    ["departments.json", "research_areas.json"], ["official", "derived_official", "synthetic"], ["DEPT-IT-001"] + ids('research_areas') + ids('programs')),
 dm("DOC-FACULTY-001", "Faculty_Directory.pdf", "faculty_directory", "Faculty Directory — Department of Information Technology",
    ["faculty.json", "teaching_assignments.json"], ["official", "synthetic"], ids('faculty') + ids('teaching_assignments')),
 dm("DOC-PROGRAMS-001", "Programs_and_Curriculum.pdf", "programs_and_curriculum", "Programmes and Curriculum — B.Tech IT and M.Tech IT",
    ["programs.json", "semesters.json", "elective_groups.json", "course_offerings.json", "grading_scheme.json"], ["official", "derived_official", "synthetic"],
    ids('programs') + ids('semesters') + ids('elective_groups') + ids('grading_scheme')),
 dm("DOC-COURSES-001", "Course_Catalog.pdf", "course_catalog", "Course Catalog — B.Tech IT and M.Tech IT Courses",
    ["courses.json", "course_prerequisites.json", "data_quality_conflicts.json"], ["official", "derived_official", "synthetic"], ids('courses') + ids('course_prerequisites') + ids('data_quality_conflicts')),
 dm("DOC-LABS-001", "Laboratories.pdf", "laboratories", "Laboratories — Department of Information Technology", ["laboratories.json"], ["official", "synthetic"], ids('laboratories')),
 dm("DOC-FACILITIES-001", "Department_Facilities.pdf", "facilities", "Department Facilities, Buildings and Rooms", ["facilities.json", "buildings.json", "rooms.json"], ["synthetic"], ids('facilities') + ids('buildings') + ids('rooms')),
 dm("DOC-POLICIES-001", "Academic_Policies.pdf", "policies", "Academic and Department Policies (Synthetic)", ["policies.json"], ["synthetic"], ids('policies')),
 dm("DOC-CALENDAR-001", "Academic_Calendar.pdf", "academic_calendar", "Academic Calendar 2026-2027 (Synthetic)", ["academic_calendar.json"], ["synthetic"], ids('academic_calendar')),
 dm("DOC-NOTICES-001", "Department_Notices.pdf", "notices", "Department Notices — June to September 2026 (Synthetic)", ["notices.json"], ["synthetic"], ids('notices')),
 dm("DOC-FAQ-001", "Student_Services_and_FAQ.pdf", "student_services_faq", "Student Services and FAQ (Synthetic)", ["faq.json"], ["official", "synthetic"], ids('faq')),
]
PAGES = {}
for m in DOCS:
    PAGES[m['document_id']] = rp.render(m, T, f"{OUT}/synthetic/pdf/{m['filename']}")
    print("rendered", m['filename'], len(PAGES[m['document_id']]), "entity markers")

# ------------------------------------------------------------------ structured JSON / CSV
def flat(v):
    if isinstance(v, list): return "|".join(json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x) for x in v)
    if isinstance(v, dict): return json.dumps(v, ensure_ascii=False)
    return "" if v is None else v
for t, rows in T.items():
    json.dump({"table": t, "generated_at": GEN, "record_count": len(rows),
               "note": "Every record carries source_type (official | derived_official | synthetic). Records mixing sources carry field_provenance.",
               "records": rows}, open(f"{OUT}/synthetic/structured/{t}.json", "w"), indent=2, ensure_ascii=False)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(f"{OUT}/synthetic/structured/csv/{t}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: flat(r.get(k)) for k in keys})
json.dump({"table": "relationships", "record_count": len(R), "records": R}, open(f"{OUT}/synthetic/structured/relationships.json", "w"), indent=2)
with open(f"{OUT}/synthetic/structured/csv/relationships.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)

# ------------------------------------------------------------------ registry
def sha(p): return "sha256:" + hashlib.sha256(open(p, "rb").read()).hexdigest()
REG = [
 {"document_id": om.SYL_DOC, "filename": "GUNI_BTech_IT_Syllabus.pdf", "path": "official/GUNI_BTech_IT_Syllabus.pdf",
  "original_filename": "1.2.2._1_GUNI_A_STRUCTURED_SYLLABUS.pdf", "document_type": "official_structured_syllabus", "title": om.SYL_TITLE,
  "source_type": "official", "is_synthetic": False, "source_url": None, "source_document": "Supplied by the CampusMate team (official Ganpat University PDF)",
  "academic_year": "2021-2022", "version": om.SYL_VERSION, "page_count": 742,
  "pages_used": {"PROG-BTECH-IT-001": [10, 11, 12, 13, 14, 15, 16, 17, 18], "PROG-MTECH-IT-001": [104, 105, 106, 107, 108]},
  "file_hash": sha(f"{OUT}/official/GUNI_BTech_IT_Syllabus.pdf"), "created_at": "2023-03-17 (PDF metadata)", "effective_from": "2021-06-01 (Effective Year 2021-2022; exact date not stated)",
  "effective_to": None, "status": "active", "department_id": None,
  "entity_ids": ["UNIV-GUNI-001", "SCHOOL-FET-001", "COLLEGE-UVPCE-001"] + ids('programs') + ids('semesters') + ids('elective_groups') + ids('grading_scheme') + [c['course_id'] for c in T['courses'] if c['source_document'] == om.SYL_DOC],
  "note": "University-wide structured syllabus (742 pages). Filename follows the CampusMate package convention; only the B.Tech IT and M.Tech IT pages were extracted."},
 {"document_id": om.CAT_DOC, "filename": "GUNI_Course_Catalog.pdf", "path": "official/GUNI_Course_Catalog.pdf",
  "original_filename": "1.1.3_Certified_Document.pdf", "document_type": "official_certified_course_list", "title": om.CAT_TITLE,
  "source_type": "official", "is_synthetic": False, "source_url": None, "source_document": "Supplied by the CampusMate team (official Ganpat University PDF)",
  "academic_year": "2017-2018 to 2021-2022", "version": om.CAT_VERSION, "page_count": 137,
  "file_hash": sha(f"{OUT}/official/GUNI_Course_Catalog.pdf"), "created_at": "2023-05-26 (PDF metadata)", "effective_from": None, "effective_to": None,
  "status": "active", "department_id": None,
  "entity_ids": ["UNIV-GUNI-001"] + [c['course_id'] for c in T['courses'] if c['catalog_listings']] + ids('data_quality_conflicts'),
  "note": "Not a descriptive course catalogue: it is the certified NAAC-style list 1.1.3 of courses with employability/entrepreneurship/skill-development focus, by year and programme code. B.Tech IT courses with 2CEIT codes are listed under programme code 201 BTech(Computer Engineering)."},
]
for m in DOCS:
    p = f"{OUT}/synthetic/pdf/{m['filename']}"
    REG.append({"document_id": m['document_id'], "filename": m['filename'], "path": f"synthetic/pdf/{m['filename']}", "original_filename": None,
        "document_type": m['document_type'], "title": m['title'], "source_type": "synthetic", "is_synthetic": True,
        "contains_source_types": m['contains_source_types'], "source_url": None,
        "source_document": "Generated by the CampusMate synthetic data generator from structured files" + ("; official fields traced to DOC-OFFICIAL-SYLLABUS-001 / DOC-OFFICIAL-CATALOG-001" if "official" in m['contains_source_types'] else ""),
        "academic_year": sd.AY, "version": "1.0", "page_count": None, "file_hash": sha(p), "created_at": GEN,
        "effective_from": "2026-07-01", "effective_to": "2027-06-30", "status": "active", "department_id": "DEPT-IT-001",
        "structured_counterparts": [f"synthetic/structured/{x}" for x in m['structured_counterparts']],
        "entity_ids": m['entity_ids'], "entity_pages": PAGES[m['document_id']]})
from pypdf import PdfReader
for r in REG:
    if r['page_count'] is None: r['page_count'] = len(PdfReader(f"{OUT}/{r['path']}").pages)
json.dump({"generated_at": GEN, "documents": REG}, open(f"{OUT}/registry/document_registry.json", "w"), indent=2, ensure_ascii=False)
cols = ["document_id", "filename", "path", "document_type", "title", "source_type", "is_synthetic", "contains_source_types", "source_url", "source_document",
        "academic_year", "version", "page_count", "file_hash", "created_at", "effective_from", "effective_to", "status", "department_id", "entity_count", "entity_ids"]
with open(f"{OUT}/registry/document_registry.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in REG:
        w.writerow({k: (flat(r.get(k)) if k not in ("entity_count",) else len(r['entity_ids'])) for k in cols})

# ------------------------------------------------------------------ entity index (one entity -> many representations)
TYPE = {'university': 'university', 'org_units': 'org_unit', 'departments': 'department', 'research_areas': 'research_area', 'buildings': 'building',
        'rooms': 'room', 'programs': 'program', 'semesters': 'semester', 'elective_groups': 'elective_group', 'course_offerings': 'course_offering',
        'grading_scheme': 'grade_band', 'faculty': 'faculty', 'teaching_assignments': 'teaching_assignment', 'laboratories': 'laboratory',
        'facilities': 'facility', 'course_prerequisites': 'course_prerequisite', 'courses': 'course', 'policies': 'policy',
        'academic_calendar': 'calendar_event', 'notices': 'notice', 'faq': 'faq', 'data_quality_conflicts': 'data_quality_conflict'}
OKF_DIR = {'university': 'university', 'org_units': 'org_units', 'departments': 'departments', 'research_areas': 'research_areas', 'programs': 'programs',
           'semesters': 'semesters', 'elective_groups': 'elective_groups', 'grading_scheme': 'grading', 'faculty': 'faculty', 'laboratories': 'laboratories',
           'facilities': 'facilities', 'courses': 'courses', 'policies': 'policies', 'academic_calendar': 'calendar', 'notices': 'notices', 'faq': 'services'}
EIDX = {}
for t, rows in T.items():
    for r in rows:
        eid = r[A.ID_FIELDS[t]]
        reps = [{"representation": "structured_json", "path": f"synthetic/structured/{t}.json"},
                {"representation": "sql_row", "table": t}]
        if t in OKF_DIR: reps.append({"representation": "okf", "path": f"knowledge/OKF_style/{OKF_DIR[t]}/{eid}.md"})
        for m in DOCS:
            if eid in PAGES[m['document_id']]:
                reps.append({"representation": "pdf", "document_id": m['document_id'], "path": f"synthetic/pdf/{m['filename']}", "page": PAGES[m['document_id']][eid]})
        if r.get('source_document') in (om.SYL_DOC, om.CAT_DOC):
            reps.append({"representation": "official_pdf", "document_id": r['source_document'], "page": r.get('source_page')})
        for cl in r.get('catalog_listings', []) or []:
            reps.append({"representation": "official_pdf", "document_id": om.CAT_DOC, "page": cl['source_page'], "academic_year": cl['academic_year']})
        EIDX[eid] = {"entity_id": eid, "entity_type": TYPE[t], "table": t, "source_type": r.get('source_type'), "representations": reps}
json.dump({"generated_at": GEN, "entity_count": len(EIDX), "entities": EIDX}, open(f"{OUT}/registry/entity_index.json", "w"), indent=1, ensure_ascii=False)

# ------------------------------------------------------------------ OKF knowledge layer
rel_out = collections.defaultdict(lambda: collections.defaultdict(list))
rel_in = collections.defaultdict(lambda: collections.defaultdict(list))
for r in R:
    if r['object_id'] not in rel_out[r['subject_id']][r['predicate']]:
        rel_out[r['subject_id']][r['predicate']].append(r['object_id'])
    if r['subject_id'] not in rel_in[r['object_id']][r['predicate']]:
        rel_in[r['object_id']][r['predicate']].append(r['subject_id'])
INV = {"CONTAINS": "contained_in", "OFFERED_IN": "offers", "BELONGS_TO": "has_course", "TEACHES": "taught_by", "REQUIRES": "required_by",
       "HAS_LAB": "lab_of", "HAS_FACILITY": "facility_of", "WORKS_IN": "has_faculty", "OFFERS": "offered_by", "APPLIES_TO": "governed_or_scheduled_by",
       "GOVERNS": "governed_by", "MENTIONS": "mentioned_in_notice", "REFERENCES": "referenced_by_faq", "PRACTICALS_IN": "hosts_practicals_of",
       "MANAGED_BY": "manages", "LOCATED_IN": "hosts", "HAS_OPTION": "option_of", "HAS_ELECTIVE_GROUP": "elective_group_of", "SUPERSEDES": "superseded_by",
       "HOSTED_BY": "hosts_program", "HAS_ORG_UNIT": "part_of", "HAS_DEPARTMENT": "department_of", "HEADS": "headed_by", "RESEARCHES": "researched_by",
       "HAS_RESEARCH_AREA": "research_area_of", "COORDINATED_BY": "coordinates", "OWNED_BY": "owns_policy", "HAS_OFFICE": "office_of", "IN_BUILDING": "contains_room"}

C = {c['course_id']: c for c in T['courses']}; S = {s['semester_id']: s for s in T['semesters']}
F = {f['faculty_id']: f for f in T['faculty']}
def title_of(t, r):
    return {'university': lambda: r['name'], 'org_units': lambda: r['name'], 'departments': lambda: r['department_name'],
            'research_areas': lambda: r['name'], 'programs': lambda: r['program_name'], 'semesters': lambda: f"{r['program_id'].split('-')[1]} IT {r['semester_name']}",
            'elective_groups': lambda: f"{r['group_name']} ({r['semester_id']})", 'grading_scheme': lambda: f"Grade band {r['marks_range']} → {r['grade_regular']}",
            'faculty': lambda: r['name'], 'laboratories': lambda: r['lab_name'], 'facilities': lambda: r['facility_name'],
            'courses': lambda: f"{r['course_code']} {r['course_name']}", 'policies': lambda: f"{r['policy_number']} {r['title']}",
            'academic_calendar': lambda: r['title'], 'notices': lambda: r['title'], 'faq': lambda: r['question']}[t]()

def body_of(t, r):
    L = []
    if t == 'courses':
        k = r['credit_scheme']
        L += [f"**{r['course_code']} — {r['course_name']}** is a {r['course_type'] or 'legacy'} course of {', '.join(r['program_ids'])}"
              + (f", offered in {', '.join(S[x]['semester_name'] + ' (' + x + ')' for x in r['semester_ids'])}." if r['semester_ids'] else ".")]
        if k: L.append(f"Credits: {r['credits']} (TH {k['credit_th']}, PR/TW {k['credit_pr']}); contact hours {k['contact_hours']}; total marks {k['total_marks']}. Basis: {r.get('credits_basis')}.")
        L.append(f"Official prerequisites: not specified in official sources.")
        if r['synthetic_prerequisites']: L.append(f"[synthetic] Recommended prior courses: {', '.join(x + ' ' + C[x]['course_name'] for x in r['synthetic_prerequisites'])}.")
        if r['faculty_ids']: L.append(f"[synthetic] Taught by: {', '.join(x + ' ' + F[x]['name'] for x in r['faculty_ids'])}.")
        if r['lab_ids']: L.append(f"[synthetic] Practicals in: {', '.join(r['lab_ids'])}.")
        if r['synthetic_description']: L.append(f"[synthetic] {r['synthetic_description']}")
        if r['catalog_listings']: L.append("[official] Listed in the GUNI 1.1.3 employability/skill course list for: " + "; ".join(f"{x['academic_year']} (programme code {x['catalog_program_code']}, p.{x['source_page']})" for x in r['catalog_listings']) + ".")
        if r.get('curriculum_note'): L.append(r['curriculum_note'])
    elif t == 'faculty':
        L += [f"**{r['name']}** ({r['faculty_id']}) is {r['designation']} in DEPT-IT-001. Qualification: {r['qualification']}. Specialization: {r['specialization']}.",
              f"Research areas: {', '.join(r['research_areas'])}. Email: {r['email']}. Office: {r['office_id']}. Consultation: {r['consultation_hours']}.",
              f"Courses taught: {', '.join(x + ' ' + C[x]['course_name'] for x in r['courses_taught'])}.", f"_{r['identity_note']}_"]
    elif t == 'semesters':
        offs = [o for o in T['course_offerings'] if o['semester_id'] == r['semester_id'] and o['course_type'] == 'regular']
        L += [f"**{title_of(t, r)}** ({r['semester_id']}): total credits {r['total_credits']} (TH {r['total_credits_th']}, PR {r['total_credits_pr']}), contact hours {r['total_contact_hours']}, total marks {r['total_marks']}.",
              "Regular courses: " + "; ".join(f"{C[o['course_id']]['course_code']} {C[o['course_id']]['course_name']}" for o in offs) + "."]
        for g in [g for g in T['elective_groups'] if g['semester_id'] == r['semester_id']]:
            L.append(f"{g['group_name']} ({g['elective_group_id']}, {g['slot_scheme']['credit_total']} credits): choose one of " + "; ".join(f"{C[c]['course_code']} {C[c]['course_name']}" for c in g['option_course_ids']) + ".")
    elif t == 'policies':
        L += [f"_{r['synthetic_notice']}_", r['summary']] + [f"- {r['policy_number']} §{i}. {c}" for i, c in enumerate(r['clauses'], 1)]
    elif t == 'notices':
        L += [f"Issued {r['date']} · effective {r['effective_date']} · expires {r['expiry_date']} · status **{r['status']}**.", r['content']]
    elif t == 'faq':
        L += [f"**Q:** {r['question']}", f"**A:** {r['answer']}"]
    elif t == 'laboratories':
        L += [f"**{r['lab_name']}** ({r['lab_id']}) — {r['building']}, Floor {r['floor']}, Room {r['room_number']}; capacity {r['capacity']}; open {r['opening_hours']}.",
              f"Responsible faculty: {r['responsible_faculty_id']} {F[r['responsible_faculty_id']]['name']}. Equipment: {'; '.join(r['equipment'])}.",
              f"Supports: {', '.join(x + ' ' + C[x]['course_name'] for x in r['related_courses'])}."]
    elif t == 'facilities':
        L += [f"**{r['facility_name']}** ({r['facility_id']}) — {r['location']}; capacity {r['capacity']}. {r['description']} Availability: {r['availability']}"]
    elif t == 'academic_calendar':
        L += [f"{r['title']}: {r['start_date']}" + (f" to {r['end_date']}" if r['end_date'] != r['start_date'] else "") + f" ({r['term']}). _{r['synthetic_notice']}_"]
    elif t == 'programs':
        L += [f"**{r['program_name']}** ({r['short_name']}, {r['program_id']}): {r['number_of_semesters']} semesters, {r['total_credits']} total credits, effective year {r['effective_year']}, hosted by U.V. Patel College of Engineering (Faculty of Engineering & Technology).",
              f"Catalog programme code {r['catalog_program_code']} ({r['catalog_program_name']}).", f"[synthetic] {r['synthetic_program_description']}"]
    elif t == 'departments':
        L += [r['overview'], f"Vision: {r['vision']}", "Mission: " + " ".join(r['mission']), f"_{r['parent_link_note']}_"]
    elif t == 'grading_scheme':
        L += [f"Marks {r['marks_range']}: grade {r['grade_regular']} ({r['grade_point_regular']} points) regular; {r['grade_remedial']} ({r['grade_point_remedial']}) remedial."]
    elif t == 'elective_groups':
        L += [f"{r['slot_title']} in {r['semester_id']}: options " + "; ".join(f"{C[c]['course_code']} {C[c]['course_name']}" for c in r['option_course_ids']) + f". Slot credits {r['slot_scheme']['credit_total']}."]
    else:
        L += [f"{title_of(t, r)}"]
    return "\n\n".join(L)

okf_index = []
for t, d in OKF_DIR.items():
    os.makedirs(f"{OUT}/knowledge/OKF_style/{d}", exist_ok=True)
    for r in T[t]:
        eid = r[A.ID_FIELDS[t]]
        rels = {k.lower(): v for k, v in rel_out[eid].items()}
        for k, v in rel_in[eid].items(): rels[INV.get(k, k.lower() + "_of")] = v
        prog = r.get('program_id') or (r.get('program_ids') or r.get('applies_to_program_ids') or [None])[0]
        pdfs = [x for x in EIDX[eid]['representations'] if x['representation'] in ('pdf',)]
        fm = {"id": eid, "type": TYPE[t], "title": title_of(t, r), "department": r.get('department_id') or (r.get('applies_to_department_ids') or [None])[0],
              "program": prog, "semester": r.get('semester_id'), "academic_year": r.get('academic_year') or ("2021-2022" if r.get('source_document') == om.SYL_DOC else sd.AY),
              "source_type": r.get('source_type'), "source_document": r.get('source_document'), "source_page": r.get('source_page'),
              "field_provenance": r.get('field_provenance'), "rendered_in": [f"{x['document_id']}#page={x['page']}" for x in pdfs],
              "structured_record": f"synthetic/structured/{t}.json#{eid}", "version": r.get('version') or "1.0",
              "status": r.get('status') or r.get('curriculum_status') or "active", "last_updated": GEN[:10], "relationships": rels}
        fm = {k: v for k, v in fm.items() if v not in (None, [], {})}
        with open(f"{OUT}/knowledge/OKF_style/{d}/{eid}.md", "w", encoding="utf-8") as f:
            f.write("---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=200) + "---\n\n")
            f.write(f"# {title_of(t, r)}\n\n")
            if r.get('source_type') == 'synthetic':
                f.write("> SYNTHETIC DATA — for CampusMate development and testing only. Not an official Ganpat University fact.\n\n")
            f.write(body_of(t, r) + "\n")
        okf_index.append({"id": eid, "type": TYPE[t], "path": f"{d}/{eid}.md", "source_type": r.get('source_type')})
json.dump({"generated_at": GEN, "items": okf_index}, open(f"{OUT}/knowledge/OKF_style/index.json", "w"), indent=1)
with open(f"{OUT}/knowledge/OKF_style/relationships.jsonl", "w") as f:
    for r in R: f.write(json.dumps(r) + "\n")

# ------------------------------------------------------------------ official extracted inventory
off = {t: [r for r in rows if r.get('source_type') in ('official', 'derived_official')] for t, rows in T.items()}
off = {t: v for t, v in off.items() if v}
json.dump({"generated_at": GEN, "note": "Only records whose record-level source_type is official or derived_official. Synthetic enrichment fields inside course records are listed in field_provenance.",
           "tables": off}, open(f"{OUT}/official/extracted/official_inventory.json", "w"), indent=1, ensure_ascii=False)

json.dump({"T": T, "R": R, "REG": REG, "EIDX": EIDX, "DOCS": DOCS}, open("/home/claude/build/_state.json", "w"), ensure_ascii=False)
print("done", {t: len(v) for t, v in T.items()}, "relationships", len(R), "okf", len(okf_index))
