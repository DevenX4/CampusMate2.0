"""Build official / derived_official entities from the two GUNI PDFs.
Page numbers are 1-indexed PHYSICAL PDF pages."""
import json, re, collections

SYL_DOC = "DOC-OFFICIAL-SYLLABUS-001"
CAT_DOC = "DOC-OFFICIAL-CATALOG-001"
SYL_FILE = "official/GUNI_BTech_IT_Syllabus.pdf"
CAT_FILE = "official/GUNI_Course_Catalog.pdf"
SYL_TITLE = "GUNI Structured Syllabus – Syllabus Details, Effective Year 2021-2022 (university-wide; B.Tech IT on pp.10-18, M.Tech IT on pp.104-108)"
CAT_TITLE = "GUNI 1.1.3 List of courses having focus on employability/entrepreneurship/skill development year-wise during the last five years (2017-18 to 2021-22)"
SYL_VERSION = "Syllabus Details dated 28/09/2022; Effective Year 2021-2022"
CAT_VERSION = "Certified list covering academic years 2017-2018 to 2021-2022"

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']

def prov(doc, page, section, stype="official", version=None):
    return {"source_type": stype, "source_document": doc, "source_page": page,
            "source_section": section,
            "document_version": version or (SYL_VERSION if doc == SYL_DOC else CAT_VERSION)}

def norm(s):
    return re.sub(r'[^A-Z0-9]', '', s.upper())

def build():
    parsed = json.load(open('/home/claude/build/official_parsed.json'))
    occ = json.load(open('/home/claude/build/catalog_occ.json'))
    cat_rows = json.load(open('/home/claude/src/catalog_rows.json'))

    E = collections.defaultdict(list)   # entity lists
    conflicts = []

    # ---------------- university / org units ----------------
    E['university'].append({
        "university_id": "UNIV-GUNI-001", "name": "Ganpat University", "short_name": "GUNI",
        "address": "Ganpat Vidyanagar - 384 012, Mehsana-Gandhinagar Highway, District: Mehsana, Gujarat, INDIA",
        "phone": "+91 2762 - 226000", "fax": "+91 2762 - 286080", "toll_free": "1800 233 12345",
        "email": "info@guni.ac.in", "website": "www.guni.ac.in",
        "note": "General university contact block printed on the letterhead of the certified course list. No department- or person-level contacts are present in either PDF.",
        **prov(CAT_DOC, 1, "Letterhead / cover page")})
    E['org_units'] += [
        {"org_unit_id": "SCHOOL-FET-001", "unit_type": "faculty_school", "name": "Faculty of Engineering & Technology",
         "parent_id": "UNIV-GUNI-001", **prov(SYL_DOC, 10, "Page header (B.TECH-IT Semester I)")},
        {"org_unit_id": "COLLEGE-UVPCE-001", "unit_type": "college", "name": "U.V. Patel College of Engineering",
         "parent_id": "SCHOOL-FET-001", **prov(SYL_DOC, 10, "Page header (B.TECH-IT Semester I)")},
    ]

    # ---------------- grading scheme ----------------
    grades = [("90>=", "A+", 10, "A", 9), ("80 To 89", "A", 9, "B+", 8), ("70 To 79", "B+", 8, "B", 7),
              ("60 To 69", "B", 7, "C+", 6), ("50 To 59", "C+", 6, "C", 5), ("40 To 49", "C", 5, "C", 5),
              ("<40", "F", 0, "F", 0)]
    for i, (rng, g, gp, rg, rgp) in enumerate(grades, 1):
        E['grading_scheme'].append({"grade_band_id": f"GRADE-BAND-{i:02d}", "marks_range": rng,
            "grade_regular": g, "grade_point_regular": gp, "grade_remedial": rg, "grade_point_remedial": rgp,
            "applies_to_program_ids": ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"],
            **prov(SYL_DOC, 10, "Examination Grade Range & Value")})

    # ---------------- programs ----------------
    progmeta = {
        "B.TECH-IT": dict(program_id="PROG-BTECH-IT-001", sem_prefix="SEM-BTECH-IT",
            program_name="Bachelor of Technology in Information Technology", short_name="B.TECH-IT",
            degree_type="Bachelor of Technology (B.Tech)", catalog_program_code="202",
            catalog_program_name="BTech(Information Technology)", first_page=10, code_series="2CEIT"),
        "M.TECH-IT": dict(program_id="PROG-MTECH-IT-001", sem_prefix="SEM-MTECH-IT",
            program_name="Master of Technology in Information Technology", short_name="M.TECH-IT",
            degree_type="Master of Technology (M.Tech)", catalog_program_code="402",
            catalog_program_name="Mtech(Information Technology)", first_page=104, code_series="3CEIT"),
    }
    courses = {}           # code -> course record
    offerings = []
    egroups = []
    for pkey, sems in parsed.items():
        pm = progmeta[pkey]
        total_credits = sum(s['totals']['credit_total'] for s in sems)
        E['programs'].append({
            "program_id": pm['program_id'], "program_name": pm['program_name'], "short_name": pm['short_name'],
            "degree_type": pm['degree_type'], "university_id": "UNIV-GUNI-001",
            "org_unit_id": "COLLEGE-UVPCE-001", "department_id": "DEPT-IT-001",
            "number_of_semesters": len(sems), "duration": f"{len(sems)} semesters",
            "total_credits": total_credits, "effective_year": "2021-2022",
            "catalog_program_code": pm['catalog_program_code'], "catalog_program_name": pm['catalog_program_name'],
            "semester_ids": [f"{pm['sem_prefix']}-{s['semester_no']:02d}" for s in sems],
            "program_description": None,
            "field_provenance": {
                "program_name": "official", "short_name": "official", "degree_type": "derived_official",
                "org_unit_id": "official", "number_of_semesters": "derived_official", "duration": "derived_official",
                "total_credits": "derived_official", "catalog_program_code": "official",
                "department_id": "synthetic (the PDFs name no department; DEPT-IT-001 is a CampusMate demo entity)",
                "program_description": "unavailable in official sources"},
            **prov(SYL_DOC, pm['first_page'], "Page header / Program field"),
            "additional_sources": [{"source_document": CAT_DOC, "note": f"Catalog program code {pm['catalog_program_code']} = {pm['catalog_program_name']}"}]})
        for s in sems:
            sid = f"{pm['sem_prefix']}-{s['semester_no']:02d}"
            h = s['header']; t = s['totals']
            E['semesters'].append({
                "semester_id": sid, "program_id": pm['program_id'], "semester_number": s['semester_no'],
                "semester_name": f"Semester {s['semester']}", "semester_roman": s['semester'],
                "total_course": h['total_course'], "total_regular_course": h['total_regular'],
                "total_elective_course": h['total_elective'], "total_open_course": h['total_open'],
                "total_audit_course": h['total_audit'],
                "total_credits_th": t['credit_th'], "total_credits_pr": t['credit_pr'], "total_credits": t['credit_total'],
                "total_contact_hours": t['contact_hours'], "total_marks": t['total_marks'],
                "effective_year": h['effective_year'], "syllabus_date": h['date'],
                "source_pages": s['source_pages'],
                **prov(SYL_DOC, s['source_page'], f"{pm['short_name']} Semester {s['semester']} – Syllabus Details")})
            # slots
            groups_on_page = collections.defaultdict(list)
            for kind, lst in s['lists'].items():
                for x in lst:
                    groups_on_page[(kind, x['group'])].append(x)
            for r in s['rows']:
                scheme = {k: r[k] for k in ('credit_th', 'credit_pr', 'credit_total', 'contact_hours',
                          'th_internal_max', 'th_external_max', 'pr_internal_max', 'pr_external_max', 'total_marks')}
                scheme['exam_raw'] = r['exam_raw']
                if r['course_code']:
                    code = r['course_code']
                    ctype = "regular"
                    add_course(courses, code, r['title'], pm, sid, s, ctype, None, scheme, "official", offerings)
                else:
                    title = r['title']
                    m = re.search(r'\((.+?)\)', title)
                    if title.startswith('ELECTIVE'):
                        kind, gname = 'elective', m.group(1).upper()
                    elif title.startswith('AUDIT'):
                        kind, gname = 'audit', 'AUDIT'
                    else:
                        kind, gname = 'open', 'OPEN'
                    gid = f"EGRP-{pm['short_name'].replace('.', '').replace('-', '-')}-{s['semester_no']:02d}-{gname.replace('_', '-')}"
                    gid = gid.replace('BTECH-IT', 'BTECH-IT').replace('MTECH-IT', 'MTECH-IT')
                    opts = groups_on_page.get((kind, gname), [])
                    egroups.append({"elective_group_id": gid, "group_name": gname, "slot_kind": kind,
                        "slot_title": title, "program_id": pm['program_id'], "semester_id": sid,
                        "slot_no": r['slot_no'], "slot_scheme": scheme,
                        "option_course_ids": [f"COURSE-{o['course_code']}" for o in opts],
                        **prov(SYL_DOC, s['source_page'], f"{pm['short_name']} Semester {s['semester']} – slot {r['slot_no']} and List of {kind.title()} Subjects")})
                    for o in opts:
                        add_course(courses, o['course_code'], o['title'], pm, sid, s, kind, gid, scheme,
                                   "derived_official", offerings)
    # ---------------- catalog listings ----------------
    for code, c in courses.items():
        good, bad = [], []
        for o in occ.get(code, []):
            rec = {"academic_year": o['academic_year'], "catalog_program_code": o['program_code'],
                   "catalog_program_name": o['program_name'], "listed_course_name": o['listed_name'],
                   "catalog_sr_no": o['sr_no'], "source_document": CAT_DOC, "source_page": o['source_page'],
                   "source_type": "official"}
            if o['listed_name'] and norm(o['listed_name']) == norm(c['course_name']):
                good.append(rec)
            elif o['listed_name']:
                bad.append(rec)
        # dedupe
        seen = set(); g2 = []
        for x in good:
            k = (x['academic_year'], x['catalog_program_code'])
            if k not in seen: seen.add(k); g2.append(x)
        c['catalog_listings'] = sorted(g2, key=lambda x: (x['academic_year'], x['catalog_program_code']))
        c['listed_in_employability_catalog'] = bool(g2)
        for x in bad:
            conflicts.append({"conflict_id": None, "course_code": code, "syllabus_course_name": c['course_name'],
                "catalog_course_name": x['listed_course_name'], "academic_year": x['academic_year'],
                "catalog_program_code": x['catalog_program_code'], "catalog_program_name": x['catalog_program_name'],
                "source_page": x['source_page'], "source_document": CAT_DOC,
                "interpretation": "Same course code appears with a different course name in another program/year of the catalog. Codes are not globally unique across programs/years; CampusMate must key catalog lookups on (code, program, year).",
                "source_type": "derived_official"})
    # dedupe conflicts
    uniq = {}
    for x in conflicts:
        uniq[(x['course_code'], x['academic_year'], x['catalog_program_code'], x['source_page'])] = x
    conflicts = list(uniq.values())
    for i, x in enumerate(sorted(conflicts, key=lambda z: (z['course_code'], z['academic_year'])), 1):
        x['conflict_id'] = f"DQ-CONFLICT-{i:03d}"
    conflicts.sort(key=lambda z: z['conflict_id'])

    # ---------------- legacy IT courses found only in catalog (program codes 202 / 402) ----------------
    legacy = collections.OrderedDict()
    for r in cat_rows:
        if r['prog_code'] in ('202', '402'):
            legacy.setdefault(r['code'], {"name": r['name'], "prog_code": r['prog_code'], "prog": r['prog'], "list": []})
            legacy[r['code']]['list'].append(r)
    for code, L in legacy.items():
        pid = "PROG-BTECH-IT-001" if L['prog_code'] == '202' else "PROG-MTECH-IT-001"
        listings = [{"academic_year": x['year'], "catalog_program_code": x['prog_code'], "catalog_program_name": x['prog'],
                     "listed_course_name": x['name'], "catalog_sr_no": x['sr'], "source_document": CAT_DOC,
                     "source_page": x['page'], "source_type": "official"} for x in L['list']]
        listings.sort(key=lambda x: x['academic_year'])
        courses[code] = {"course_id": f"COURSE-{code}", "course_code": code, "course_name": L['name'],
            "program_id": pid, "program_ids": [pid], "semester_id": None, "semester_ids": [],
            "course_type": None, "elective_group_id": None, "credits": None, "credit_scheme": None,
            "curriculum_status": "legacy_catalog_only",
            "curriculum_note": "Listed under catalog program code %s (%s) in %s; not present in the 2021-2022 structured syllabus for this program. Semester, credits and scheme are unavailable." % (L['prog_code'], L['prog'], ", ".join(sorted({x['year'] for x in L['list']}))),
            "prerequisites": None, "description": None,
            "catalog_listings": listings, "listed_in_employability_catalog": True,
            **prov(CAT_DOC, listings[0]['source_page'], "Year-wise course list", "official")}
    return E, courses, offerings, egroups, conflicts


def add_course(courses, code, title, pm, sid, s, ctype, gid, scheme, stype, offerings):
    oid = f"OFF-{sid.replace('SEM-', '')}-{code}"
    section = f"{pm['short_name']} Semester {s['semester']} – " + ("course table" if ctype == 'regular' else f"List of {ctype.title()} Subjects ({gid.split('-')[-1] if gid else ''})")
    offerings.append({"offering_id": oid, "course_id": f"COURSE-{code}", "program_id": pm['program_id'],
        "semester_id": sid, "course_type": ctype, "elective_group_id": gid, "credit_scheme": scheme,
        "credit_scheme_basis": "course row" if ctype == 'regular' else "inherited from the elective/audit/open slot row (derived)",
        **prov(SYL_DOC, s['source_page'], section, stype)})
    if code in courses:
        c = courses[code]
        if pm['program_id'] not in c['program_ids']: c['program_ids'].append(pm['program_id'])
        c['semester_ids'].append(sid)
        c['additional_source_pages'].append(s['source_page'])
        return
    courses[code] = {"course_id": f"COURSE-{code}", "course_code": code, "course_name": title,
        "program_id": pm['program_id'], "program_ids": [pm['program_id']],
        "semester_id": sid, "semester_ids": [sid], "course_type": ctype, "elective_group_id": gid,
        "credits": scheme['credit_total'], "credit_scheme": scheme,
        "credits_basis": "course row" if ctype == 'regular' else "slot credits inherited by each option (derived_official)",
        "curriculum_status": "active_in_2021_2022_syllabus",
        "prerequisites": None, "description": None, "additional_source_pages": [],
        **prov(SYL_DOC, s['source_page'], (f"{pm['short_name']} Semester {s['semester']} – course table") if ctype == 'regular' else f"{pm['short_name']} Semester {s['semester']} – List of {ctype.title()} Subjects", stype)}


def shared_with_other_programs(codes):
    # codes: dict code -> title
    """Which other programs in the syllabus PDF list the same code (derived_official)."""
    syl = open('/home/claude/src/syllabus.txt').read().split('\f')
    res = collections.defaultdict(list)
    for i, p in enumerate(syl):
        m = re.search(r'Program\s*:\s*(\S+(?: \S+)?)\s{2,}', p)
        if not m: continue
        prog = m.group(1).strip()
        if prog in ('B.TECH-IT', 'M.TECH-IT'): continue
        for c in codes:
            for ln in p.split('\n'):
                if re.search(r'(?<![0-9A-Z])' + re.escape(c) + r'(?![0-9A-Z])', ln):
                    ok = norm(codes[c])[:10] in norm(ln)
                    if prog not in [x['program_short_name'] for x in res[c]]:
                        res[c].append({"program_short_name": prog, "source_page": i + 1, "source_document": SYL_DOC,
                                       "title_matches": ok, "listed_line": re.sub(r'\s+', ' ', ln.strip())[:120],
                                       "source_type": "derived_official"})
    return res
