"""Write evaluation sets + SQL, then run the consistency audit (incl. a live PostgreSQL load)."""
import json, os, re, subprocess, hashlib, collections, glob, yaml
import assemble as A, eval_sets, sql_build, official_model as om, synthetic_data as sd

OUT = "/home/claude/CampusMate_Dataset"
st = json.load(open("/home/claude/build/_state.json"))
T, R, REG, EIDX, DOCS = st['T'], st['R'], st['REG'], st['EIDX'], st['DOCS']
Q, NEG = eval_sets.build(T, EIDX)
json.dump({"generated_at": A.GENERATED_AT, "count": len(Q), "questions": Q}, open(f"{OUT}/evaluation/evaluation_questions.json", "w"), indent=2, ensure_ascii=False)
json.dump({"generated_at": A.GENERATED_AT, "count": len(NEG), "expected_default_answer": "I don't have authoritative information for that.", "questions": NEG},
          open(f"{OUT}/evaluation/negative_questions.json", "w"), indent=2, ensure_ascii=False)
open(f"{OUT}/sql/schema.sql", "w").write(sql_build.SCHEMA)
open(f"{OUT}/sql/seed.sql", "w").write(sql_build.seed(T, R, REG, EIDX))

checks = []
def chk(name, ok, detail=None, severity="error"):
    checks.append({"check": name, "status": "PASS" if ok else ("FAIL" if severity == "error" else "WARN"), "detail": detail})

# 1. unique IDs
allids = collections.Counter()
for t, rows in T.items():
    for r in rows: allids[r[A.ID_FIELDS[t]]] += 1
dups = [k for k, v in allids.items() if v > 1]
chk("no duplicate entity IDs across all tables", not dups, dups or f"{len(allids)} unique IDs")
codes = collections.Counter(c['course_code'] for c in T['courses'])
chk("no duplicate course codes", all(v == 1 for v in codes.values()), [k for k, v in codes.items() if v > 1] or f"{len(codes)} codes")
names = collections.Counter((c['course_name'], tuple(c['program_ids'])) for c in T['courses'])
chk("no duplicate course (name, program) pairs", all(v == 1 for v in names.values()), [k for k, v in names.items() if v > 1] or "ok")
chk("department / lab / facility / faculty names unique",
    all(len(set(x)) == len(x) for x in [[d['department_name'] for d in T['departments']], [l['lab_name'] for l in T['laboratories']],
                                          [f['facility_name'] for f in T['facilities']], [f['name'] for f in T['faculty']], [f['email'] for f in T['faculty']]]))

# 2. foreign keys
docs = {d['document_id'] for d in REG}
ID = set(allids) | docs
idx = {t: {r[A.ID_FIELDS[t]] for r in rows} for t, rows in T.items()}
FK = [("programs", "department_id", "departments"), ("programs", "org_unit_id", "org_units"), ("semesters", "program_id", "programs"),
      ("courses", "program_id", "programs"), ("courses", "semester_id", "semesters"), ("courses", "program_ids", "programs"), ("courses", "semester_ids", "semesters"),
      ("courses", "faculty_ids", "faculty"), ("courses", "lab_ids", "laboratories"), ("courses", "synthetic_prerequisites", "courses"),
      ("courses", "elective_group_id", "elective_groups"), ("courses", "department_id", "departments"),
      ("course_offerings", "course_id", "courses"), ("course_offerings", "semester_id", "semesters"), ("course_offerings", "program_id", "programs"),
      ("elective_groups", "option_course_ids", "courses"), ("elective_groups", "semester_id", "semesters"),
      ("faculty", "department_id", "departments"), ("faculty", "office_id", "rooms"), ("faculty", "courses_taught", "courses"), ("faculty", "research_area_ids", "research_areas"),
      ("teaching_assignments", "faculty_id", "faculty"), ("teaching_assignments", "course_id", "courses"), ("teaching_assignments", "semester_id", "semesters"),
      ("laboratories", "department_id", "departments"), ("laboratories", "room_id", "rooms"), ("laboratories", "responsible_faculty_id", "faculty"),
      ("laboratories", "related_courses", "courses"), ("laboratories", "governing_policy_ids", "policies"),
      ("facilities", "department_id", "departments"), ("facilities", "room_id", "rooms"), ("rooms", "building_id", "buildings"),
      ("policies", "applies_to_department_ids", "departments"), ("policies", "applies_to_program_ids", "programs"), ("policies", "related_course_ids", "courses"),
      ("policies", "related_lab_ids", "laboratories"), ("policies", "related_facility_ids", "facilities"), ("policies", "owner_faculty_id", "faculty"),
      ("academic_calendar", "department_id", "departments"), ("academic_calendar", "program_ids", "programs"), ("academic_calendar", "semester_ids", "semesters"),
      ("notices", "department_id", "departments"), ("notices", "related_course_ids", "courses"), ("notices", "related_faculty_ids", "faculty"),
      ("notices", "related_lab_ids", "laboratories"), ("notices", "related_facility_ids", "facilities"), ("notices", "related_policy_ids", "policies"),
      ("notices", "related_calendar_ids", "academic_calendar"), ("notices", "supersedes", "notices"), ("notices", "superseded_by", "notices"),
      ("course_prerequisites", "course_id", "courses"), ("course_prerequisites", "requires_course_id", "courses"),
      ("departments", "head_faculty_id", "faculty"), ("departments", "parent_org_unit_id", "org_units"), ("departments", "program_ids", "programs"),
      ("departments", "lab_ids", "laboratories"), ("departments", "facility_ids", "facilities"), ("departments", "research_area_ids", "research_areas"),
      ("research_areas", "department_id", "departments"), ("grading_scheme", "applies_to_program_ids", "programs")]
orph = []
for t, f, tgt in FK:
    for r in T[t]:
        v = r.get(f)
        for x in (v if isinstance(v, list) else [v]):
            if x is not None and x not in idx[tgt]: orph.append(f"{t}.{f}={x}")
chk(f"no orphan foreign keys ({len(FK)} FK rules)", not orph, orph[:20] or "0 orphans")
faq_bad = [f"{q['faq_id']}->{x}" for q in T['faq'] for x in q['related_entity_ids'] if x not in ID]
chk("FAQ references resolve", not faq_bad, faq_bad or "ok")
rel_bad = [r['relationship_id'] for r in R if r['subject_id'] not in ID or r['object_id'] not in ID]
chk(f"all {len(R)} relationships resolve", not rel_bad, rel_bad[:10] or "ok")
idle = [f['faculty_id'] for f in T['faculty'] if not f['courses_taught']]
chk("every faculty member teaches >=1 course", not idle, idle or "ok")
ta_consistent = all(set(f['courses_taught']) == {a['course_id'] for a in T['teaching_assignments'] if a['faculty_id'] == f['faculty_id']} for f in T['faculty'])
chk("faculty.courses_taught == teaching_assignments", ta_consistent)
lab_ok = {(l['lab_id'], c) for l in T['laboratories'] for c in l['related_courses']} == {(x, c['course_id']) for c in T['courses'] for x in c['lab_ids']}
chk("labs <-> courses bidirectionally consistent", lab_ok)
pr_cyc = []
G = collections.defaultdict(list)
for p in T['course_prerequisites']: G[p['course_id']].append(p['requires_course_id'])
def cyc(n, seen):
    for m in G[n]:
        if m in seen or cyc(m, seen | {m}): return True
    return False
chk("prerequisite graph is acyclic", not any(cyc(n, {n}) for n in list(G)))
sem_order = {s['semester_id']: s['semester_number'] for s in T['semesters']}
CS = {c['course_id']: c for c in T['courses']}
bad_order = [p['prerequisite_id'] for p in T['course_prerequisites']
             if CS[p['course_id']]['semester_id'] and CS[p['requires_course_id']]['semester_id'] and
             (CS[p['course_id']]['program_id'] == CS[p['requires_course_id']]['program_id']) and
             sem_order[CS[p['requires_course_id']]['semester_id']] >= sem_order[CS[p['course_id']]['semester_id']]]
chk("synthetic prerequisites always point to an earlier semester", not bad_order, bad_order or "ok")

# 3. source_type labelling
VALID = {"official", "derived_official", "synthetic"}
badst = [f"{t}:{r[A.ID_FIELDS[t]]}" for t, rows in T.items() for r in rows if r.get('source_type') not in VALID]
chk("every record has a valid source_type", not badst, badst[:10] or "ok")
syn_tables = ['departments', 'research_areas', 'buildings', 'rooms', 'faculty', 'teaching_assignments', 'laboratories', 'facilities',
              'course_prerequisites', 'policies', 'academic_calendar', 'notices', 'faq']
leak = [f"{t}:{r[A.ID_FIELDS[t]]}" for t in syn_tables for r in T[t] if r['source_type'] != 'synthetic' or r.get('source_document') in (om.SYL_DOC, om.CAT_DOC)]
chk("all invented entity tables are labelled synthetic and cite synthetic documents", not leak, leak[:10] or "ok")
off_bad = [f"{t}:{r[A.ID_FIELDS[t]]}" for t, rows in T.items() for r in rows if r['source_type'] in ('official', 'derived_official') and (r.get('source_document') not in (om.SYL_DOC, om.CAT_DOC) or not r.get('source_page'))]
chk("every official/derived_official record cites a GUNI PDF + page", not off_bad, off_bad[:10] or "ok")
mixed_bad = [c['course_id'] for c in T['courses'] if c['contains_synthetic_fields'] and not all(c['field_provenance'].get(k) == 'synthetic' for k in ('faculty_ids', 'lab_ids', 'synthetic_prerequisites', 'synthetic_description'))]
chk("mixed course records flag synthetic fields in field_provenance", not mixed_bad, mixed_bad[:10] or "ok")
chk("official prerequisites/description left null (not invented)", all(c['prerequisites'] is None and c['description'] is None for c in T['courses']))
chk("no real-looking contact data in synthetic tables (all emails @campusmate-demo.example)",
    all(f['email'].endswith("@" + sd.DOMAIN) for f in T['faculty']) and all(v.endswith(sd.DOMAIN) for k, v in T['departments'][0]['contact'].items() if 'email' in k))
poln = [p['policy_id'] for p in T['policies'] if "synthetic policy created for CampusMate testing" not in p['synthetic_notice']]
chk("every policy carries the synthetic-policy statement", not poln, poln or "ok")

# 4. official traceability: re-verify against the PDF text
syl = open('/home/claude/src/syllabus.txt').read().split('\f'); cat = open('/home/claude/src/catalog.txt').read().split('\f')
N_ = lambda s: re.sub(r'[^A-Z0-9]', '', s.upper())
untr = []
for c in T['courses']:
    txt = (syl if c['source_document'] == om.SYL_DOC else cat)[c['source_page'] - 1]
    if c['course_code'] not in txt or N_(c['course_name'])[:12] not in N_(txt): untr.append(c['course_id'])
    for x in c['catalog_listings']:
        p = cat[x['source_page'] - 1]
        if c['course_code'] not in p or (x['academic_year'][:4] not in p): untr.append(f"{c['course_id']}@cat p{x['source_page']}")
for s in T['semesters']:
    txt = syl[s['source_page'] - 1]
    if f"{s['total_credits']:.2f}" not in txt or str(s['total_marks']) not in txt: untr.append(s['semester_id'])
for g in T['elective_groups']:
    txt = syl[g['source_page'] - 1]
    if g['group_name'].replace('_', '_') not in txt.upper(): untr.append(g['elective_group_id'])
chk("every official course / semester / elective group re-verified on its cited PDF page", not untr, untr[:15] or f"{len(T['courses'])} courses, {len(T['semesters'])} semesters, {len(T['elective_groups'])} groups verified")
recon = []
for s in T['semesters']:
    offs = [o for o in T['course_offerings'] if o['semester_id'] == s['semester_id'] and o['course_type'] == 'regular']
    grps = [g for g in T['elective_groups'] if g['semester_id'] == s['semester_id']]
    tot = sum(o['credit_scheme']['credit_total'] for o in offs) + sum(g['slot_scheme']['credit_total'] for g in grps)
    if abs(tot - s['total_credits']) > 0.01: recon.append(f"{s['semester_id']}: {tot} vs {s['total_credits']}")
chk("per-semester credits reconcile with printed totals", not recon, recon or "12/12 semesters reconcile")
chk("programme totals = sum of semester totals", all(abs(p['total_credits'] - sum(s['total_credits'] for s in T['semesters'] if s['program_id'] == p['program_id'])) < 0.01 for p in T['programs']),
    {p['program_id']: p['total_credits'] for p in T['programs']})

# 5. naming consistency
chk("semester naming consistent (SEM-<PROG>-NN / 'Semester <ROMAN>')",
    all(re.fullmatch(r"SEM-(BTECH|MTECH)-IT-0[1-8]", s['semester_id']) and re.fullmatch(r"Semester [IVX]+", s['semester_name']) for s in T['semesters']))
chk("synthetic academic_year consistently '2026-2027'", all(r.get('academic_year') == sd.AY for t in syn_tables for r in T[t]))
chk("single department name used everywhere", {d['department_name'] for d in T['departments']} == {"Department of Information Technology"})
chk("ID formats", all(re.fullmatch(r"COURSE-[0-9A-Z]+", c['course_id']) for c in T['courses']) and all(re.fullmatch(r"FAC-IT-\d{3}", f['faculty_id']) for f in T['faculty'])
    and all(re.fullmatch(r"LAB-IT-\d{3}", l['lab_id']) for l in T['laboratories']) and all(re.fullmatch(r"NOTICE-\d{3}", n['notice_id']) for n in T['notices'])
    and all(re.fullmatch(r"POLICY-\d{3}", p['policy_id']) for p in T['policies']))
chk("notice status consistent with dates (as of 2026-09-18)",
    all((n['status'] == 'superseded') == bool(n['superseded_by']) and (n['status'] != 'active' or n['expiry_date'] >= '2026-09-18') for n in T['notices']))
chk("calendar dates valid (end >= start)", all(c['end_date'] >= c['start_date'] for c in T['academic_calendar']))

# 6. documents / registry / PDFs
hash_bad = [d['document_id'] for d in REG if "sha256:" + hashlib.sha256(open(f"{OUT}/{d['path']}", 'rb').read()).hexdigest() != d['file_hash']]
chk("registry file hashes match files", not hash_bad, hash_bad or f"{len(REG)} documents")
ban_bad = []
for d in REG:
    if not d['is_synthetic']: continue
    p = f"{OUT}/{d['path']}"
    txt = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
    pages = txt.split('\f')[:-1] if txt.endswith('\f') else txt.split('\f')
    if "THIS DOCUMENT IS NOT AN OFFICIAL GANPAT UNIVERSITY DOCUMENT" not in re.sub(r'\s+', ' ', pages[0]): ban_bad.append(d['filename'] + ":banner")
    if any("SYNTHETIC DATA — NOT AN OFFICIAL GANPAT UNIVERSITY DOCUMENT" not in pg for pg in pages if pg.strip()): ban_bad.append(d['filename'] + ":page-header")
    for k in ("document_id", "version", "academic_year", "generated_at", "source_type"):
        if k not in pages[0]: ban_bad.append(f"{d['filename']}:{k}")
    miss = [e for e in d['entity_pages'] if e not in txt]
    if miss: ban_bad.append(f"{d['filename']}: ids not in text {miss[:5]}")
chk("every synthetic PDF: disclaimer banner on p.1, header on every page, metadata block, entity IDs present as text", not ban_bad, ban_bad or "10/10 PDFs")
chk("10 separate synthetic PDFs, none merged", len([d for d in REG if d['is_synthetic']]) == 10 and len(glob.glob(f"{OUT}/synthetic/pdf/*.pdf")) == 10)
reg_ent_bad = [f"{d['document_id']}:{e}" for d in REG for e in d['entity_ids'] if e not in ID]
chk("registry entity_ids resolve", not reg_ent_bad, reg_ent_bad[:10] or "ok")
orphan_ent = [e for e in allids if not any(e in d['entity_ids'] for d in REG) and e.split('-')[0] not in ('OFF', 'TA')]
chk("every entity (except offering rows) is described by >=1 registered document", not orphan_ent, orphan_ent[:10] or "ok", severity="warn")

# 7. OKF
okf = glob.glob(f"{OUT}/knowledge/OKF_style/*/*.md")
okf_bad = []
for p in okf:
    fm = yaml.safe_load(open(p).read().split('---')[1])
    if os.path.basename(p)[:-3] != fm['id'] or fm['source_type'] not in VALID: okf_bad.append(p)
    for k, v in fm.get('relationships', {}).items():
        for x in v:
            if x not in ID: okf_bad.append(f"{p}:{k}:{x}")
chk(f"OKF items ({len(okf)}) have valid id/source_type and resolvable relationships", not okf_bad, okf_bad[:10] or "ok")

# 8. evaluation integrity
ev_bad = []
for q in Q + NEG:
    for s in q['required_sources']:
        if s['document_id'] not in docs: ev_bad.append(f"{q['question_id']} doc {s['document_id']}")
    for e in q.get('expected_entities', []):
        if e not in ID: ev_bad.append(f"{q['question_id']} entity {e}")
    if q['answerable'] and not q['required_sources']: ev_bad.append(f"{q['question_id']} no sources")
cats = collections.Counter(q['category'] for q in Q)
chk(f"evaluation set: {len(Q)} questions across {len(cats)} categories (A–H); {len(NEG)} negatives", len(Q) >= 50 and len(cats) == 8 and len(NEG) >= 20 and not ev_bad, ev_bad or dict(cats))

# 9. PostgreSQL load + reference SQL
PS = ["psql", "-h", "/var/tmp/cmpg", "-p", "5433", "-U", "postgres", "-v", "ON_ERROR_STOP=1", "-q"]
subprocess.run(PS + ["-c", "DROP DATABASE IF EXISTS campusmate_audit"], capture_output=True)
subprocess.run(PS + ["-c", "CREATE DATABASE campusmate_audit"], check=True, capture_output=True)
r1 = subprocess.run(PS + ["-d", "campusmate_audit", "-f", f"{OUT}/sql/schema.sql"], capture_output=True, text=True)
r2 = subprocess.run(PS + ["-d", "campusmate_audit", "-f", f"{OUT}/sql/seed.sql"], capture_output=True, text=True)
chk("schema.sql + seed.sql load into PostgreSQL 16 with all FK/CHECK constraints", r1.returncode == 0 and r2.returncode == 0, (r1.stderr + r2.stderr)[:500] or "loaded")
sql_res = {}
for q in Q:
    if 'reference_sql' in q:
        r = subprocess.run(PS + ["-d", "campusmate_audit", "-A", "-t", "-c", q['reference_sql']], capture_output=True, text=True)
        sql_res[q['question_id']] = {"ok": r.returncode == 0 and bool(r.stdout.strip()), "rows": r.stdout.strip().split("\n")[:12], "err": r.stderr[:200]}
chk(f"all {len(sql_res)} reference SQL queries execute and return rows", all(v['ok'] for v in sql_res.values()), {k: v for k, v in sql_res.items() if not v['ok']} or "ok")
cnts = subprocess.run(PS + ["-d", "campusmate_audit", "-A", "-t", "-c",
    "SELECT 'courses',count(*) FROM courses UNION ALL SELECT 'relationships',count(*) FROM relationships UNION ALL SELECT 'document_entities',count(*) FROM document_entities UNION ALL SELECT 'catalog_listings',count(*) FROM catalog_listings"], capture_output=True, text=True).stdout

# ---- info
info = {
    "row_counts": {t: len(v) for t, v in T.items()}, "relationships": len(R), "okf_items": len(okf), "db_counts": cnts.strip().split("\n"),
    "source_type_counts": dict(collections.Counter(r['source_type'] for rows in T.values() for r in rows)),
    "relationship_source_types": dict(collections.Counter(r['source_type'] for r in R)),
    "courses_without_lab_but_with_practical_credits": [c['course_id'] for c in T['courses'] if c['department_id'] and c['credit_scheme'] and c['credit_scheme']['credit_pr'] > 0 and not c['lab_ids']],
    "note_courses_without_lab": "Project, seminar, soft-skill, training and entrepreneurship courses deliberately use facilities (FCL-IT-002/007/001) rather than a lab.",
    "data_quality_conflicts_in_official_sources": [f"{x['conflict_id']}: {x['course_code']} = '{x['syllabus_course_name']}' in syllabus but '{x['catalog_course_name']}' in catalog {x['academic_year']} prog {x['catalog_program_code']}" for x in T['data_quality_conflicts']],
    "sql_reference_results": sql_res,
}
report = {"generated_at": A.GENERATED_AT, "summary": dict(collections.Counter(c['status'] for c in checks)), "checks": checks, "info": info}
json.dump(report, open(f"{OUT}/audit/audit_report.json", "w"), indent=2, ensure_ascii=False)
md = ["# CampusMate dataset — consistency audit", "", f"Generated {A.GENERATED_AT}. Result: **{report['summary']}**", "", "| # | Check | Status | Detail |", "|---|---|---|---|"]
for i, c in enumerate(checks, 1):
    d = c['detail'] if isinstance(c['detail'], str) or c['detail'] is None else json.dumps(c['detail'])[:160]
    md.append(f"| {i} | {c['check']} | {c['status']} | {d or ''} |")
md += ["", "## Record counts by source_type", "", "```", json.dumps(info['source_type_counts'], indent=1), "```", "", "## Relationship edges by source_type", "", "```", json.dumps(info['relationship_source_types'], indent=1), "```",
       "", "## Data-quality findings in the official sources", ""] + [f"- {x}" for x in info['data_quality_conflicts_in_official_sources']] + \
      ["", "## Informational", "", f"- Department courses with practical credits but no lab (by design): {', '.join(info['courses_without_lab_but_with_practical_credits'])}. {info['note_courses_without_lab']}"]
open(f"{OUT}/audit/audit_report.md", "w").write("\n".join(md) + "\n")
print(report['summary'])
for c in checks:
    if c['status'] != 'PASS': print(c)
