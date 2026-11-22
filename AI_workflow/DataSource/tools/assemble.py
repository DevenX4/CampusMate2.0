"""Assemble all canonical tables (official + derived_official + synthetic) with stable IDs."""
import collections
import official_model as om
import synthetic_data as sd

GENERATED_AT = "2026-09-18T12:00:00+05:30"

def assemble():
    E, courses, offerings, egroups, conflicts = om.build()
    shared = om.shared_with_other_programs({k: v['course_name'] for k, v in courses.items()})
    T = collections.OrderedDict()

    T['university'] = E['university']
    T['org_units'] = E['org_units']
    T['departments'] = [sd.DEPARTMENT]
    T['research_areas'] = [dict(research_area_id=r, name=n, department_id="DEPT-IT-001", source_type="synthetic",
                                source_document="DOC-DEPT-PROFILE-001", academic_year=sd.AY) for r, n in sd.RESEARCH_AREAS]
    T['buildings'] = [dict(b, source_type="synthetic", source_document="DOC-FACILITIES-001", academic_year=sd.AY) for b in sd.BUILDINGS]
    T['rooms'] = [dict(r, source_type="synthetic", source_document="DOC-FACILITIES-001", academic_year=sd.AY) for r in sd.ROOMS]
    rooms = {r['room_id']: r for r in T['rooms']}

    # programs: add synthetic enrichment in explicitly-named fields
    syn_prog = {
        "PROG-BTECH-IT-001": ("Synthetic summary: an eight-semester undergraduate programme combining engineering foundations (Semesters I–II), core computing (III–IV), specialisation electives and a three-stage capstone project (V–VII) and a full semester of industrial training (VIII).", "FAC-IT-020"),
        "PROG-MTECH-IT-001": ("Synthetic summary: a four-semester postgraduate programme with advanced core courses and electives in Semesters I–II followed by a two-part major project and seminar in Semesters III–IV.", "FAC-IT-013"),
    }
    for p in E['programs']:
        d, c = syn_prog[p['program_id']]
        p['synthetic_program_description'] = d
        p['synthetic_program_coordinator_faculty_id'] = c
        p['field_provenance']['synthetic_program_description'] = "synthetic"
        p['field_provenance']['synthetic_program_coordinator_faculty_id'] = "synthetic"
    T['programs'] = E['programs']
    T['semesters'] = E['semesters']
    T['elective_groups'] = egroups
    T['course_offerings'] = offerings
    T['grading_scheme'] = E['grading_scheme']

    # teaching / labs / prereqs
    course_sem = {c['course_id']: c['semester_id'] for c in courses.values()}
    T['faculty'] = sd.faculty_records()
    T['teaching_assignments'] = sd.teaching_assignments(course_sem)
    T['laboratories'] = sd.lab_records(rooms)
    T['facilities'] = sd.facility_records(rooms)
    T['course_prerequisites'] = sd.prerequisite_records()
    fac_by_course = collections.defaultdict(list)
    for a in T['teaching_assignments']:
        if a['faculty_id'] not in fac_by_course[a['course_id']]:
            fac_by_course[a['course_id']].append(a['faculty_id'])
    lab_by_course = collections.defaultdict(list)
    for l in T['laboratories']:
        for c in l['related_courses']:
            lab_by_course[c].append(l['lab_id'])
    pre_by_course = collections.defaultdict(list)
    for p in T['course_prerequisites']:
        pre_by_course[p['course_id']].append(p['requires_course_id'])

    clist = []
    for code, c in sorted(courses.items(), key=lambda kv: (kv[1]['semester_id'] or 'ZZZ', kv[0])):
        c = dict(c)
        cid = c['course_id']
        c['shared_with_other_syllabus_programs'] = [x for x in shared.get(code, []) if x['title_matches']]
        c['faculty_ids'] = fac_by_course.get(cid, [])
        c['lab_ids'] = lab_by_course.get(cid, [])
        c['synthetic_prerequisites'] = pre_by_course.get(cid, [])
        c['synthetic_description'] = sd.synthetic_description(code, c['course_name'], c['course_type'],
                                        (c['elective_group_id'] or '').split('-', 4)[-1] if c['elective_group_id'] else None)
        c['field_provenance'] = {
            "course_code": "official", "course_name": "official",
            "program_id": "official" if c['curriculum_status'] != 'legacy_catalog_only' else "derived_official (catalog program code)",
            "semester_id": "official" if c['course_type'] == 'regular' else ("derived_official" if c['semester_id'] else "unavailable"),
            "course_type": "official (Regular/Elective/Audit/Open slot categories)" if c['course_type'] else "unavailable",
            "credits": "official" if c['course_type'] == 'regular' else ("derived_official (inherited from slot)" if c['credits'] is not None else "unavailable"),
            "prerequisites": "unavailable in official sources (null)", "description": "unavailable in official sources (null)",
            "catalog_listings": "official", "shared_with_other_syllabus_programs": "derived_official",
            "faculty_ids": "synthetic", "lab_ids": "synthetic", "synthetic_prerequisites": "synthetic",
            "synthetic_description": "synthetic"}
        c['contains_synthetic_fields'] = bool(c['faculty_ids'] or c['lab_ids'] or c['synthetic_prerequisites'] or c['synthetic_description'])
        c['department_id'] = "DEPT-IT-001" if code.startswith(("2CEIT", "3CEIT", "2IT", "3IT")) else None
        c['delivered_by_note'] = None if c['department_id'] else "Common/basic course shared across many programmes; teaching department not identified in official sources and not assigned in this demo dataset."
        c['academic_year'] = "2021-2022 (syllabus effective year)"
        c.pop('additional_source_pages', None)
        clist.append(c)
    T['courses'] = clist
    T['policies'] = sd.policy_records()
    T['academic_calendar'] = sd.calendar_records()
    T['notices'] = sd.notice_records()
    T['faq'] = sd.faq_records()
    T['data_quality_conflicts'] = conflicts
    return T


ID_FIELDS = {
    'university': 'university_id', 'org_units': 'org_unit_id', 'departments': 'department_id',
    'research_areas': 'research_area_id', 'buildings': 'building_id', 'rooms': 'room_id',
    'programs': 'program_id', 'semesters': 'semester_id', 'elective_groups': 'elective_group_id',
    'course_offerings': 'offering_id', 'grading_scheme': 'grade_band_id', 'faculty': 'faculty_id',
    'teaching_assignments': 'assignment_id', 'laboratories': 'lab_id', 'facilities': 'facility_id',
    'course_prerequisites': 'prerequisite_id', 'courses': 'course_id', 'policies': 'policy_id',
    'academic_calendar': 'event_id', 'notices': 'notice_id', 'faq': 'faq_id',
    'data_quality_conflicts': 'conflict_id'}


def relationships(T):
    R = []
    def add(s, p, o, st, src=None, page=None):
        R.append({"subject_id": s, "predicate": p, "object_id": o, "source_type": st,
                  "source_document": src, "source_page": page})
    SY, CA = om.SYL_DOC, om.CAT_DOC
    add("UNIV-GUNI-001", "HAS_ORG_UNIT", "SCHOOL-FET-001", "official", SY, 10)
    add("SCHOOL-FET-001", "HAS_ORG_UNIT", "COLLEGE-UVPCE-001", "official", SY, 10)
    add("COLLEGE-UVPCE-001", "HAS_DEPARTMENT", "DEPT-IT-001", "synthetic", "DOC-DEPT-PROFILE-001")
    for p in T['programs']:
        add(p['program_id'], "HOSTED_BY", "COLLEGE-UVPCE-001", "official", SY, p['source_page'])
        add("DEPT-IT-001", "OFFERS", p['program_id'], "synthetic", "DOC-DEPT-PROFILE-001")
        add(p['program_id'], "COORDINATED_BY", p['synthetic_program_coordinator_faculty_id'], "synthetic", "DOC-PROGRAMS-001")
    for s in T['semesters']:
        add(s['program_id'], "CONTAINS", s['semester_id'], "official", SY, s['source_page'])
    for o in T['course_offerings']:
        add(o['semester_id'], "CONTAINS", o['course_id'], o['source_type'], SY, o['source_page'])
        add(o['course_id'], "OFFERED_IN", o['semester_id'], o['source_type'], SY, o['source_page'])
    seen = set()
    for c in T['courses']:
        for pid in c['program_ids']:
            if (c['course_id'], pid) not in seen:
                seen.add((c['course_id'], pid))
                add(c['course_id'], "BELONGS_TO", pid, "official" if c['curriculum_status'] != 'legacy_catalog_only' else "derived_official",
                    c['source_document'], c['source_page'])
        for l in c['lab_ids']:
            add(c['course_id'], "PRACTICALS_IN", l, "synthetic", "DOC-LABS-001")
    for g in T['elective_groups']:
        add(g['semester_id'], "HAS_ELECTIVE_GROUP", g['elective_group_id'], "official", SY, g['source_page'])
        for c in g['option_course_ids']:
            add(g['elective_group_id'], "HAS_OPTION", c, "official", SY, g['source_page'])
    for gb in T['grading_scheme']:
        for pid in gb['applies_to_program_ids']:
            add(gb['grade_band_id'], "APPLIES_TO", pid, "official", SY, gb['source_page'])
    for f in T['faculty']:
        add(f['faculty_id'], "WORKS_IN", "DEPT-IT-001", "synthetic", "DOC-FACULTY-001")
        add(f['faculty_id'], "HAS_OFFICE", f['office_id'], "synthetic", "DOC-FACULTY-001")
        for r in f['research_area_ids']:
            add(f['faculty_id'], "RESEARCHES", r, "synthetic", "DOC-FACULTY-001")
    add("FAC-IT-001", "HEADS", "DEPT-IT-001", "synthetic", "DOC-DEPT-PROFILE-001")
    for a in T['teaching_assignments']:
        add(a['faculty_id'], "TEACHES", a['course_id'], "synthetic", "DOC-FACULTY-001")
    for p in T['course_prerequisites']:
        add(p['course_id'], "REQUIRES", p['requires_course_id'], "synthetic", "DOC-COURSES-001")
    for l in T['laboratories']:
        add("DEPT-IT-001", "HAS_LAB", l['lab_id'], "synthetic", "DOC-LABS-001")
        add(l['lab_id'], "MANAGED_BY", l['responsible_faculty_id'], "synthetic", "DOC-LABS-001")
        add(l['lab_id'], "LOCATED_IN", l['room_id'], "synthetic", "DOC-LABS-001")
    for f in T['facilities']:
        add("DEPT-IT-001", "HAS_FACILITY", f['facility_id'], "synthetic", "DOC-FACILITIES-001")
        add(f['facility_id'], "LOCATED_IN", f['room_id'], "synthetic", "DOC-FACILITIES-001")
    for r in T['rooms']:
        add(r['room_id'], "IN_BUILDING", r['building_id'], "synthetic", "DOC-FACILITIES-001")
    for r in T['research_areas']:
        add("DEPT-IT-001", "HAS_RESEARCH_AREA", r['research_area_id'], "synthetic", "DOC-DEPT-PROFILE-001")
    for p in T['policies']:
        for d in p['applies_to_department_ids']: add(p['policy_id'], "APPLIES_TO", d, "synthetic", "DOC-POLICIES-001")
        for d in p['applies_to_program_ids']: add(p['policy_id'], "APPLIES_TO", d, "synthetic", "DOC-POLICIES-001")
        for x in p['related_course_ids'] + p['related_lab_ids'] + p['related_facility_ids']:
            add(p['policy_id'], "GOVERNS", x, "synthetic", "DOC-POLICIES-001")
        add(p['policy_id'], "OWNED_BY", p['owner_faculty_id'], "synthetic", "DOC-POLICIES-001")
    for e in T['academic_calendar']:
        for x in e['program_ids'] + e['semester_ids']:
            add(e['event_id'], "APPLIES_TO", x, "synthetic", "DOC-CALENDAR-001")
    for n in T['notices']:
        add(n['notice_id'], "APPLIES_TO", n['department_id'], "synthetic", "DOC-NOTICES-001")
        for k in ('related_course_ids', 'related_faculty_ids', 'related_lab_ids', 'related_facility_ids', 'related_policy_ids', 'related_calendar_ids'):
            for x in n[k]: add(n['notice_id'], "MENTIONS", x, "synthetic", "DOC-NOTICES-001")
        if n['supersedes']: add(n['notice_id'], "SUPERSEDES", n['supersedes'], "synthetic", "DOC-NOTICES-001")
    for q in T['faq']:
        for x in q['related_entity_ids']:
            add(q['faq_id'], "REFERENCES", x, "synthetic", "DOC-FAQ-001")
    for i, r in enumerate(R, 1):
        r['relationship_id'] = f"REL-{i:05d}"
    return [{"relationship_id": r['relationship_id'], **{k: v for k, v in r.items() if k != 'relationship_id'}} for r in R]
