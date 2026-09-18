"""Evaluation + negative question sets. Expected answers are computed from the canonical data where possible."""
import json, collections

def build(T, EIDX):
    C = {c['course_code']: c for c in T['courses']}; CI = {c['course_id']: c for c in T['courses']}
    F = {f['faculty_id']: f for f in T['faculty']}; Lb = {l['lab_id']: l for l in T['laboratories']}
    FC = {f['facility_id']: f for f in T['facilities']}; S = {s['semester_id']: s for s in T['semesters']}
    P = {p['policy_id']: p for p in T['policies']}; N = {n['notice_id']: n for n in T['notices']}
    CAL = {c['event_id']: c for c in T['academic_calendar']}; RM = {r['room_id']: r for r in T['rooms']}
    G = {g['elective_group_id']: g for g in T['elective_groups']}
    B = {b['building_id']: b for b in T['buildings']}

    def src(*eids, official=True, pdf=True):
        out = []
        for e in eids:
            for r in EIDX[e]['representations']:
                if (r['representation'] == 'pdf' and pdf) or (r['representation'] == 'official_pdf' and official):
                    x = {"document_id": r['document_id'], "page": r['page']}
                    if x not in out: out.append(x)
        return out
    def cn(code): return f"{code} {C[code]['course_name']}"
    def fn(fid): return f"{fid} {F[fid]['name']}"
    Q = []
    def add(cat, q, a, srcs, ents, rtype, diff, answerable=True, stypes=None, sql=None, notes=None):
        d = {"question": q, "expected_answer": a, "required_sources": srcs, "expected_entities": ents, "retrieval_type": rtype,
             "difficulty": diff, "answerable": answerable, "category": cat, "expected_source_types": stypes or []}
        if sql: d["reference_sql"] = sql
        if notes: d["notes"] = notes
        Q.append(d)

    # ---------------- A. simple factual
    c = C['2CEIT602']; k = c['credit_scheme']
    add("A_simple_factual", "How many credits does ARTIFICIAL INTELLIGENCE carry in B.Tech IT?",
        f"2CEIT602 ARTIFICIAL INTELLIGENCE carries {k['credit_total']:g} credits (TH {k['credit_th']:g} + PR/TW {k['credit_pr']:g}), {k['contact_hours']:g} contact hours, {k['total_marks']} total marks (official, syllabus p.15).",
        src('COURSE-2CEIT602'), ["COURSE-2CEIT602", "SEM-BTECH-IT-06"], "hybrid", "easy", stypes=["official"])
    s3 = S['SEM-BTECH-IT-03']
    add("A_simple_factual", "What is the total number of credits in B.Tech IT Semester III?",
        f"{s3['total_credits']:g} credits (TH {s3['total_credits_th']:g}, PR {s3['total_credits_pr']:g}); total marks {s3['total_marks']} (official, syllabus p.12).",
        src('SEM-BTECH-IT-03'), ["SEM-BTECH-IT-03"], "structured", "easy", stypes=["official"])
    add("A_simple_factual", "Who is the Head of the IT department?",
        f"{fn('FAC-IT-001')} (Professor & Head of Department) — a synthetic demo identity; the official GUNI documents do not name a head of department.",
        src('FAC-IT-001', 'DEPT-IT-001'), ["FAC-IT-001", "DEPT-IT-001"], "hybrid", "easy", stypes=["synthetic"])
    add("A_simple_factual", "What is the seating capacity of the IT Seminar Hall?",
        f"{FC['FCL-IT-001']['capacity']} (FCL-IT-001, {FC['FCL-IT-001']['location']}; synthetic).", src('FCL-IT-001'), ["FCL-IT-001"], "hybrid", "easy", stypes=["synthetic"])
    add("A_simple_factual", "Which college and faculty run the B.Tech Information Technology programme according to the syllabus?",
        "U.V. Patel College of Engineering (COLLEGE-UVPCE-001) under the Faculty of Engineering & Technology (SCHOOL-FET-001), Ganpat University (official, syllabus p.10 header).",
        src('PROG-BTECH-IT-001', 'COLLEGE-UVPCE-001'), ["PROG-BTECH-IT-001", "COLLEGE-UVPCE-001", "SCHOOL-FET-001"], "semantic", "easy", stypes=["official"])
    k8 = C['2CEIT801']['credit_scheme']
    add("A_simple_factual", "What is taught in Semester VIII of B.Tech IT?",
        f"Only {cn('2CEIT801')}: {k8['credit_total']:g} credits (PR/TW), {k8['contact_hours']:g} hours, {k8['total_marks']} marks (official, syllabus p.18).",
        src('SEM-BTECH-IT-08', 'COURSE-2CEIT801'), ["SEM-BTECH-IT-08", "COURSE-2CEIT801"], "hybrid", "easy", stypes=["official"])
    add("A_simple_factual", "What grade and grade point does a regular student get for 85 marks?",
        "Grade A with 9 grade points (80 To 89 band, regular); remedial equivalent B+ (8) (official grade table, syllabus p.10).",
        src('GRADE-BAND-02'), ["GRADE-BAND-02"], "structured", "easy", stypes=["official"])
    pm = next(p for p in T['programs'] if p['program_id'] == 'PROG-MTECH-IT-001')
    add("A_simple_factual", "How many semesters and total credits does the M.Tech IT programme have?",
        f"{pm['number_of_semesters']} semesters and {pm['total_credits']:g} credits (21+23+18+12, derived from official semester totals, syllabus pp.104-108).",
        src('PROG-MTECH-IT-001'), ["PROG-MTECH-IT-001"], "structured", "easy", stypes=["derived_official"])

    # ---------------- B. exact-match / lexical
    c = C['2CEIT78PE7']
    add("B_exact_lexical", "What is 2CEIT78PE7?",
        f"{cn('2CEIT78PE7')} — an option in ELECTIVE-VI ({c['elective_group_id']}) of B.Tech IT Semester VII; slot credits {c['credits']:g} (official list, syllabus p.16).",
        src('COURSE-2CEIT78PE7'), ["COURSE-2CEIT78PE7", c['elective_group_id']], "bm25", "easy", stypes=["official", "derived_official"])
    add("B_exact_lexical", "What does policy CM-SYN-POL-004 cover?",
        f"POLICY-004 {P['POLICY-004']['title']}: {P['POLICY-004']['summary']} Synthetic policy.", src('POLICY-004'), ["POLICY-004"], "bm25", "easy", stypes=["synthetic"])
    add("B_exact_lexical", "What is in room DA-302?",
        f"LAB-IT-002 {Lb['LAB-IT-002']['lab_name']}, {Lb['LAB-IT-002']['building']}, Floor 3 (synthetic).", src('LAB-IT-002'), ["LAB-IT-002", "ROOM-DA-302"], "bm25", "easy", stypes=["synthetic"])
    add("B_exact_lexical", "What is NOTICE-008 about?",
        f"{N['NOTICE-008']['title']} dated {N['NOTICE-008']['date']}: it supersedes NOTICE-005; exam window 7-12 Sept 2026 unchanged, 2CEIT602 paper for re-registered students moved to 12 Sept, papers start 10:00 (synthetic).",
        src('NOTICE-008', 'NOTICE-005'), ["NOTICE-008", "NOTICE-005"], "bm25", "easy", stypes=["synthetic"])
    c = C['3CEIT211']
    add("B_exact_lexical", "Which course has the code 3CEIT211?",
        f"{cn('3CEIT211')} — option in {G[c['elective_group_id']]['group_name']} of M.Tech IT Semester II ({c['elective_group_id']}) (official, syllabus p.105).",
        src('COURSE-3CEIT211'), ["COURSE-3CEIT211"], "bm25", "easy", stypes=["official"])
    add("B_exact_lexical", "What is the specialization of FAC-IT-004?",
        f"{F['FAC-IT-004']['name']}: {F['FAC-IT-004']['specialization']} (synthetic).", src('FAC-IT-004'), ["FAC-IT-004"], "bm25", "easy", stypes=["synthetic"])
    g = G['EGRP-BTECH-IT-06-ELECTIVE-IV']
    add("B_exact_lexical", "What are the options in EGRP-BTECH-IT-06-ELECTIVE-IV?",
        "; ".join(cn(CI[x]['course_code']) for x in g['option_course_ids']) + " (official, syllabus p.15).",
        src('EGRP-BTECH-IT-06-ELECTIVE-IV'), [g['elective_group_id']] + g['option_course_ids'], "bm25", "easy", stypes=["official"])
    add("B_exact_lexical", "Which programme is catalog programme code 202?",
        "BTech(Information Technology) → PROG-BTECH-IT-001. In the certified list, 2CEIT course codes are actually listed under programme code 201 BTech(Computer Engineering); code 202 lists only 2IT302, 2IT503, 2IT606 (2017-2020).",
        src('PROG-BTECH-IT-001', 'COURSE-2IT503'), ["PROG-BTECH-IT-001", "COURSE-2IT503", "COURSE-2IT302", "COURSE-2IT606"], "bm25", "medium", stypes=["official", "derived_official"])

    # ---------------- C. semantic
    add("C_semantic", "Where can my team sit and work on our project outside class hours?",
        "Capstone Project Room (FCL-IT-002, Room DA-205, open Mon–Sat 08:30–20:00 to registered teams) or Student Project Workspace (FCL-IT-007, Room DB-103, daily 08:00–21:00) (synthetic).",
        src('FCL-IT-002', 'FCL-IT-007'), ["FCL-IT-002", "FCL-IT-007"], "semantic", "easy", stypes=["synthetic"])
    add("C_semantic", "Is there a course about building apps for smartphones?",
        f"Yes: {cn('2CEIT5PE5')} (ELECTIVE-II, Semester V); related: {cn('2CEIT78PE4')} (ELECTIVE-V, Semester VII) (official).",
        src('COURSE-2CEIT5PE5', 'COURSE-2CEIT78PE4'), ["COURSE-2CEIT5PE5", "COURSE-2CEIT78PE4"], "semantic", "medium", stypes=["official"])
    add("C_semantic", "What happens if I hand in my capstone report a couple of days late?",
        "Under the synthetic POLICY-004 §3 you lose 10% per day late, for up to 3 days.", src('POLICY-004'), ["POLICY-004"], "semantic", "easy", stypes=["synthetic"])
    add("C_semantic", "Is there an elective on legally testing systems for security weaknesses?",
        f"{cn('2CEIT6PE7')} (ELECTIVE-IV, Semester VI) (official); taught by {fn('FAC-IT-008')} (synthetic).",
        src('COURSE-2CEIT6PE7'), ["COURSE-2CEIT6PE7", "FAC-IT-008"], "semantic", "medium", stypes=["official", "synthetic"])
    add("C_semantic", "I want to learn how chatbots and language models work — which B.Tech elective fits?",
        f"{cn('2CEIT78PE7')} in ELECTIVE-VI, Semester VII (official).", src('COURSE-2CEIT78PE7'), ["COURSE-2CEIT78PE7"], "semantic", "medium", stypes=["official"])
    add("C_semantic", "Do I need any training before working with the robots?",
        "Yes — a mandatory safety induction before operating hardware in LAB-IT-007 IoT & Robotics Lab (POLICY-003 §2; see NOTICE-016) (synthetic).",
        src('POLICY-003', 'LAB-IT-007', 'NOTICE-016'), ["POLICY-003", "LAB-IT-007", "NOTICE-016"], "semantic", "easy", stypes=["synthetic"])
    add("C_semantic", "Where do I go to get forms and certificates sorted out?",
        "Department Office & Student Help Desk, FCL-IT-010, Room DA-201; Mon–Fri 09:30–17:00, Sat 09:30–13:00 (synthetic).",
        src('FCL-IT-010'), ["FCL-IT-010"], "semantic", "easy", stypes=["synthetic"])

    # ---------------- D. metadata-filtered
    s6 = [o for o in T['course_offerings'] if o['semester_id'] == 'SEM-BTECH-IT-06']
    reg6 = [CI[o['course_id']]['course_code'] for o in s6 if o['course_type'] == 'regular']
    el6 = [CI[o['course_id']]['course_code'] for o in s6 if o['course_type'] == 'elective']
    add("D_metadata_filtered", "What courses are offered in Semester VI of B.Tech IT?",
        "Regular: " + "; ".join(cn(x) for x in reg6) + ". Plus one course from ELECTIVE-III (" + ", ".join(x for x in el6 if x in ('2CEIT6PE1', '2CEIT6PE2', '2CEIT6PE3', '2CEIT6PE4', '2CEIT6PE5')) + ") and one from ELECTIVE-IV (" + ", ".join(x for x in el6 if x in ('2CEIT6PE6', '2CEIT6PE7', '2CEIT6PE8', '2CEIT6PE9')) + "). Semester total 23 credits (official, syllabus p.15).",
        src('SEM-BTECH-IT-06'), ["SEM-BTECH-IT-06"] + [f"COURSE-{x}" for x in reg6], "metadata_filter", "medium", stypes=["official"],
        sql="SELECT c.course_code, c.course_name, o.course_type FROM course_offerings o JOIN courses c USING (course_id) WHERE o.semester_id='SEM-BTECH-IT-06' ORDER BY o.course_type DESC, c.course_code;")
    sep = sorted([n for n in T['notices'] if n['date'].startswith('2026-09')], key=lambda x: x['date'])
    add("D_metadata_filtered", "What notices were issued in September 2026?",
        "; ".join(f"{n['notice_id']} ({n['date']}) {n['title']}" for n in sep) + " (synthetic).",
        src(*[n['notice_id'] for n in sep]), [n['notice_id'] for n in sep], "metadata_filter", "medium", stypes=["synthetic"],
        sql="SELECT notice_id, notice_date, title FROM notices WHERE notice_date BETWEEN '2026-09-01' AND '2026-09-30' ORDER BY notice_date;")
    act = [n for n in T['notices'] if n['status'] == 'active']
    add("D_metadata_filtered", "Which department notices are still active as of 18 September 2026?",
        "; ".join(f"{n['notice_id']} {n['title']} (expires {n['expiry_date']})" for n in act) + ". Expired and superseded notices (e.g. NOTICE-005 superseded by NOTICE-008) must be excluded.",
        src(*[n['notice_id'] for n in act]), [n['notice_id'] for n in act], "metadata_filter", "medium", stypes=["synthetic"],
        sql="SELECT notice_id, title, expiry_date FROM notices WHERE status='active' ORDER BY notice_id;")
    mp = [p for p in T['policies'] if 'PROG-MTECH-IT-001' in p['applies_to_program_ids']]
    add("D_metadata_filtered", "Which policies apply to the M.Tech IT programme?",
        "; ".join(f"{p['policy_id']} {p['title']}" for p in mp) + " — all synthetic.", src(*[p['policy_id'] for p in mp]), [p['policy_id'] for p in mp] + ["PROG-MTECH-IT-001"], "metadata_filter", "medium", stypes=["synthetic"],
        sql="SELECT p.policy_id, p.title FROM policies p JOIN policy_links l USING (policy_id) WHERE l.link_type='program' AND l.target_id='PROG-MTECH-IT-001' ORDER BY 1;")
    el7 = [o for o in T['course_offerings'] if o['semester_id'] == 'SEM-BTECH-IT-07' and o['course_type'] == 'elective']
    add("D_metadata_filtered", "Which Semester VII B.Tech IT courses are electives?",
        "ELECTIVE-V: " + ", ".join(cn(CI[o['course_id']]['course_code']) for o in el7 if o['elective_group_id'].endswith('-V')) + ". ELECTIVE-VI: " + ", ".join(cn(CI[o['course_id']]['course_code']) for o in el7 if o['elective_group_id'].endswith('-VI')) + " (official, syllabus p.16).",
        src('SEM-BTECH-IT-07'), ["SEM-BTECH-IT-07", "EGRP-BTECH-IT-07-ELECTIVE-V", "EGRP-BTECH-IT-07-ELECTIVE-VI"], "metadata_filter", "medium", stypes=["official"])
    ex = [c for c in T['academic_calendar'] if c['event_type'] == 'examination' and c['term'].startswith('Odd')]
    add("D_metadata_filtered", "What examinations are scheduled in the odd semester of 2026-2027?",
        "; ".join(f"{c['event_id']} {c['title']}: {c['start_date']} to {c['end_date']}" for c in ex) + " (synthetic demo calendar).",
        src(*[c['event_id'] for c in ex]), [c['event_id'] for c in ex], "metadata_filter", "medium", stypes=["synthetic"],
        sql="SELECT event_id, title, start_date, end_date FROM academic_calendar WHERE event_type='examination' AND term LIKE 'Odd%' ORDER BY start_date;")
    add("D_metadata_filtered", "Using only official sources, what is known about 2CEIT303?",
        "DATABASE MANAGEMENT SYSTEM, B.Tech IT Semester III, regular course, 4 credits (TH 3 + PR/TW 1), 5 hours, 150 marks (syllabus p.12); also in the B.TECH-CE and B.TECH-CE(AI) schemes; listed in the employability list for 2019-2020, 2020-2021 and 2021-2022 under programme code 201. Faculty, lab and prerequisites are not in official sources.",
        src('COURSE-2CEIT303', pdf=False), ["COURSE-2CEIT303"], "metadata_filter", "hard", stypes=["official", "derived_official"],
        notes="Retriever must filter source_type IN ('official','derived_official') and ignore synthetic fields.")

    # ---------------- E. multi-hop
    ai_f = C['2CEIT602']['faculty_ids']
    add("E_multi_hop", "Which faculty member teaches the AI course in Semester VI?",
        f"2CEIT602 ARTIFICIAL INTELLIGENCE (SEM-BTECH-IT-06, official) is taught by {fn('FAC-IT-002')} (instructor) with {fn('FAC-IT-004')} as lab instructor (synthetic assignments TA).",
        src('COURSE-2CEIT602', 'FAC-IT-002', 'FAC-IT-004'), ["SEM-BTECH-IT-06", "COURSE-2CEIT602"] + ai_f, "graph_multi_hop", "medium", stypes=["official", "synthetic"])
    labs4 = sorted({l for cid in F['FAC-IT-004']['courses_taught'] for l in CI[cid]['lab_ids']})
    add("E_multi_hop", "What laboratory is associated with the courses taught by FAC-IT-004?",
        f"FAC-IT-004 teaches {', '.join(cn(CI[x]['course_code']) for x in F['FAC-IT-004']['courses_taught'])}; all run practicals in " + ", ".join(f"{l} {Lb[l]['lab_name']} (Room {Lb[l]['room_number']})" for l in labs4) + " (synthetic).",
        src('FAC-IT-004', *labs4), ["FAC-IT-004"] + F['FAC-IT-004']['courses_taught'] + labs4, "graph_multi_hop", "medium", stypes=["synthetic", "official"])
    add("E_multi_hop", "Which policies apply to students using the laboratory where DBMS practicals are conducted?",
        "DBMS (2CEIT303) practicals run in LAB-IT-003 Database Systems Lab (Room DA-303); it is governed by POLICY-002 Laboratory Usage Policy (Demo) and POLICY-003 Laboratory Safety Policy (Demo) (synthetic).",
        src('COURSE-2CEIT303', 'LAB-IT-003', 'POLICY-002', 'POLICY-003'), ["COURSE-2CEIT303", "LAB-IT-003", "POLICY-002", "POLICY-003"], "graph_multi_hop", "hard", stypes=["official", "synthetic"])
    nb = len([c for c in T['courses'] if 'PROG-BTECH-IT-001' in c['program_ids'] and c['curriculum_status'] != 'legacy_catalog_only'])
    nm = len([c for c in T['courses'] if 'PROG-MTECH-IT-001' in c['program_ids'] and c['curriculum_status'] != 'legacy_catalog_only'])
    add("E_multi_hop", "Which courses belong to the programmes offered by the IT department?",
        f"DEPT-IT-001 offers PROG-BTECH-IT-001 and PROG-MTECH-IT-001 (synthetic link). The 2021-2022 syllabus lists {nb} distinct course codes for B.Tech IT (regular, elective options, audit) and {nm} for M.Tech IT (official); 5 further legacy IT codes appear only in the certified list. Full lists: Course_Catalog.pdf sections A–D.",
        [{"document_id": "DOC-PROGRAMS-001", "page": None}, {"document_id": "DOC-COURSES-001", "page": None}], ["DEPT-IT-001", "PROG-BTECH-IT-001", "PROG-MTECH-IT-001"], "structured", "hard", stypes=["official", "synthetic"],
        sql="SELECT p.short_name, count(DISTINCT o.course_id) FROM course_offerings o JOIN programs p USING (program_id) WHERE p.department_id='DEPT-IT-001' GROUP BY 1;")
    l2 = Lb['LAB-IT-002']; f3 = F[l2['responsible_faculty_id']]
    add("E_multi_hop", "Who is in charge of the lab where NLP (2CEIT78PE7) practicals are held, and where is their office?",
        f"LAB-IT-002 {l2['lab_name']} (Room {l2['room_number']}) is managed by {f3['faculty_id']} {f3['name']}, office {f3['office_id']} (synthetic).",
        src('COURSE-2CEIT78PE7', 'LAB-IT-002', f3['faculty_id']), ["COURSE-2CEIT78PE7", "LAB-IT-002", f3['faculty_id'], f3['office_id']], "graph_multi_hop", "hard", stypes=["synthetic"])
    add("E_multi_hop", "What are the recommended prerequisites of the prerequisite of Deep Learning (2CEIT78PE1)?",
        "2CEIT78PE1 DEEP LEARNING → requires 2CEIT602 ARTIFICIAL INTELLIGENCE → which requires 2CEIT402 DESIGN AND ANALYSIS OF ALGORITHMS and 2BS3102 DISCRETE MATHEMATICS & PROBABILITY. These REQUIRES links are synthetic advisory prerequisites; the official syllabus specifies none.",
        src('PREREQ-SYN-019', 'PREREQ-SYN-010', 'PREREQ-SYN-011'), ["COURSE-2CEIT78PE1", "COURSE-2CEIT602", "COURSE-2CEIT402", "COURSE-2BS3102"], "graph_multi_hop", "hard", stypes=["synthetic"],
        sql="WITH RECURSIVE p AS (SELECT requires_course_id, 1 AS depth FROM course_prerequisites WHERE course_id='COURSE-2CEIT78PE1' UNION SELECT cp.requires_course_id, p.depth+1 FROM course_prerequisites cp JOIN p ON cp.course_id=p.requires_course_id) SELECT * FROM p;")
    l6 = Lb[C['2CEIT702']['lab_ids'][0]]
    add("E_multi_hop", "In which building is the lab used for Big Data Analytics practicals?",
        f"2CEIT702 BIG DATA ANALYTICS → {l6['lab_id']} {l6['lab_name']} → Room {l6['room_number']}, Floor {l6['floor']}, {l6['building']} ({l6['building_id']}) (synthetic).",
        src('COURSE-2CEIT702', l6['lab_id']), ["COURSE-2CEIT702", l6['lab_id'], l6['room_id'], l6['building_id']], "graph_multi_hop", "medium", stypes=["synthetic"])
    f6 = F[C['2CEIT503']['faculty_ids'][0]]
    add("E_multi_hop", "Which research area does the Computer Networks instructor work in?",
        f"2CEIT503 COMPUTER NETWORKS is taught by {f6['faculty_id']} {f6['name']}, research area {', '.join(f'{a} {b}' for a, b in zip(f6['research_area_ids'], f6['research_areas']))} (synthetic).",
        src('COURSE-2CEIT503', f6['faculty_id']), ["COURSE-2CEIT503", f6['faculty_id']] + f6['research_area_ids'], "graph_multi_hop", "medium", stypes=["synthetic"])

    # ---------------- F. cross-document
    add("F_cross_document", "How are the capstone projects coordinated by FAC-IT-020 evaluated, and where are final presentations held?",
        "FAC-IT-020 Dr. Leena Projectkar coordinates 2CEIT504/2CEIT605/2CEIT703 (Faculty Directory). POLICY-005 (Academic Policies): panel of ≥2 faculty + guide, mid-review then final presentation in the IT Seminar Hall FCL-IT-001; rubric 15/20/30/15/20 (synthetic).",
        src('FAC-IT-020', 'POLICY-005', 'FCL-IT-001'), ["FAC-IT-020", "POLICY-005", "FCL-IT-001", "COURSE-2CEIT504", "COURSE-2CEIT605", "COURSE-2CEIT703"], "cross_document", "hard", stypes=["synthetic"])
    add("F_cross_document", "When and where is the capstone mid-review?",
        "28 September – 3 October 2026 (CAL-2026-27-007, Academic Calendar) in the Capstone Project Room FCL-IT-002, Room DA-205 (NOTICE-012); interim report due 48 h before the slot (synthetic).",
        src('CAL-2026-27-007', 'NOTICE-012', 'FCL-IT-002'), ["CAL-2026-27-007", "NOTICE-012", "FCL-IT-002"], "cross_document", "medium", stypes=["synthetic"])
    add("F_cross_document", "Is ARTIFICIAL INTELLIGENCE listed in GUNI's employability/skill-development course list, and under which programme?",
        "Yes. 2CEIT602 (B.Tech IT Semester VI per syllabus p.15) appears in the certified 1.1.3 list for 2020-2021 (p.41) and 2021-2022 (p.2) under programme code 201 BTech(Computer Engineering), not under code 202 (official).",
        src('COURSE-2CEIT602', pdf=False), ["COURSE-2CEIT602"], "cross_document", "hard", stypes=["official"])
    add("F_cross_document", "The revised mid-semester notice moved one paper — who teaches that course?",
        "NOTICE-008 moved the 2CEIT602 ARTIFICIAL INTELLIGENCE paper to 12 September 2026; the course is taught by FAC-IT-002 Dr. Arjun Tensorkar (lab: FAC-IT-004 Dr. Kabir Modelkar) (synthetic).",
        src('NOTICE-008', 'FAC-IT-002'), ["NOTICE-008", "COURSE-2CEIT602", "FAC-IT-002", "FAC-IT-004"], "cross_document", "hard", stypes=["synthetic", "official"])
    add("F_cross_document", "When is the Industrial Training final report due, and what must be submitted before Semester VIII starts?",
        "Final report and presentation due 30 April 2027 (CAL-2026-27-020); an offer letter from the host organisation must be submitted to FAC-IT-020 before Semester VIII (POLICY-006 §1) (synthetic). 2CEIT801 itself is official: 20 credits, 400 marks.",
        src('CAL-2026-27-020', 'POLICY-006', 'COURSE-2CEIT801'), ["CAL-2026-27-020", "POLICY-006", "COURSE-2CEIT801", "FAC-IT-020"], "cross_document", "medium", stypes=["synthetic", "official"])
    add("F_cross_document", "Which workshop was held in the NLP lab, when, and who ran it?",
        "NOTICE-007: hands-on workshop on Retrieval-Augmented Generation with local SLMs, 29 August 2026, by FAC-IT-003 Dr. Nisha Tokenwala in LAB-IT-002 (Room DA-302) (synthetic).",
        src('NOTICE-007', 'LAB-IT-002', 'FAC-IT-003'), ["NOTICE-007", "LAB-IT-002", "FAC-IT-003"], "cross_document", "medium", stypes=["synthetic"])
    k = C['2CEIT703']['credit_scheme']
    add("F_cross_document", "How many credits does CAPSTONE PROJECT-III carry and who coordinates it?",
        f"2CEIT703 CAPSTONE PROJECT-III: {k['credit_total']:g} credits (PR/TW), {k['contact_hours']:g} hours, {k['total_marks']} marks (official, syllabus p.16); coordinated by FAC-IT-020 Dr. Leena Projectkar (synthetic).",
        src('COURSE-2CEIT703', 'FAC-IT-020'), ["COURSE-2CEIT703", "FAC-IT-020"], "cross_document", "medium", stypes=["official", "synthetic"])

    # ---------------- G. structured SQL
    tb = sum(s['total_credits'] for s in T['semesters'] if s['program_id'] == 'PROG-BTECH-IT-001')
    add("G_structured_sql", "What is the total credit requirement of B.Tech IT?", f"{tb:g} credits (sum of eight official semester totals).",
        src('PROG-BTECH-IT-001'), ["PROG-BTECH-IT-001"], "sql", "easy", stypes=["derived_official"],
        sql="SELECT sum(total_credits) FROM semesters WHERE program_id='PROG-BTECH-IT-001';")
    add("G_structured_sql", "How many options are there in ELECTIVE-VI of B.Tech IT Semester VII?", f"{len(G['EGRP-BTECH-IT-07-ELECTIVE-VI']['option_course_ids'])} options.",
        src('EGRP-BTECH-IT-07-ELECTIVE-VI'), ["EGRP-BTECH-IT-07-ELECTIVE-VI"], "sql", "easy", stypes=["official"],
        sql="SELECT count(*) FROM elective_group_options WHERE elective_group_id='EGRP-BTECH-IT-07-ELECTIVE-VI';")
    cnt = collections.Counter(a['faculty_id'] for a in T['teaching_assignments'])
    many = sorted([f for f, n in cnt.items() if n > 4])
    add("G_structured_sql", "Which faculty members are assigned to more than four courses?", "; ".join(f"{fn(f)} ({cnt[f]})" for f in many) + " (synthetic).",
        [{"document_id": "DOC-FACULTY-001", "page": None}], many, "sql", "medium", stypes=["synthetic"],
        sql="SELECT f.faculty_id, f.name, count(*) FROM teaching_assignments t JOIN faculty f USING (faculty_id) GROUP BY 1,2 HAVING count(*)>4 ORDER BY 1;")
    per = [(s['semester_name'], s['total_regular_course']) for s in T['semesters'] if s['program_id'] == 'PROG-BTECH-IT-001']
    add("G_structured_sql", "How many regular courses does each B.Tech IT semester have?", "; ".join(f"{a}: {b}" for a, b in per) + " (official 'Total Regular Course' header values).",
        src(*[s['semester_id'] for s in T['semesters'] if s['program_id'] == 'PROG-BTECH-IT-001']), ["PROG-BTECH-IT-001"], "sql", "medium", stypes=["official"],
        sql="SELECT semester_name, (record->>'total_regular_course')::int FROM semesters WHERE program_id='PROG-BTECH-IT-001' ORDER BY semester_number;",
        notes="Uses the printed 'Total Regular Course' header value of each semester page.")
    big = sorted([l for l in T['laboratories'] if l['capacity'] >= 40], key=lambda x: x['lab_id'])
    add("G_structured_sql", "Which labs can seat at least 40 students?", "; ".join(f"{l['lab_id']} {l['lab_name']} ({l['capacity']})" for l in big) + " (synthetic).",
        src(*[l['lab_id'] for l in big]), [l['lab_id'] for l in big], "sql", "easy", stypes=["synthetic"],
        sql="SELECT lab_id, lab_name, capacity FROM laboratories WHERE capacity>=40 ORDER BY lab_id;")
    r5 = [o for o in T['course_offerings'] if o['semester_id'] == 'SEM-BTECH-IT-05' and o['course_type'] == 'regular']
    avg = sum(o['credit_scheme']['credit_total'] for o in r5) / len(r5)
    add("G_structured_sql", "What is the average credit value of the regular (non-elective) courses in B.Tech IT Semester V?",
        f"{avg:.2f} credits across {len(r5)} regular courses (" + ", ".join(f"{CI[o['course_id']]['course_code']}={o['credit_scheme']['credit_total']:g}" for o in r5) + ").",
        src('SEM-BTECH-IT-05'), [o['course_id'] for o in r5], "sql", "medium", stypes=["official"],
        sql="SELECT round(avg(credits),2), count(*) FROM course_offerings WHERE semester_id='SEM-BTECH-IT-05' AND course_type='regular';")
    pr2 = sorted({CI[o['course_id']]['course_code'] for o in T['course_offerings'] if o['program_id'] == 'PROG-BTECH-IT-001' and o['course_type'] == 'regular' and o['credit_scheme']['credit_pr'] >= 2})
    add("G_structured_sql", "Which regular B.Tech IT courses carry 2 or more practical/TW credits?", "; ".join(cn(x) for x in pr2) + " (official).",
        [{"document_id": "DOC-OFFICIAL-SYLLABUS-001", "page": None}], [f"COURSE-{x}" for x in pr2], "sql", "medium", stypes=["official"],
        sql="SELECT DISTINCT c.course_code, c.course_name FROM course_offerings o JOIN courses c USING (course_id) WHERE o.program_id='PROG-BTECH-IT-001' AND o.course_type='regular' AND o.credit_pr>=2 ORDER BY 1;")

    # ---------------- H. should not be answered
    H = [
        ("What topics/units are covered in 2CEIT602 ARTIFICIAL INTELLIGENCE according to the official syllabus?", "The supplied official pages give only the scheme (credits, hours, marks), not unit-wise content. Only a labelled synthetic summary exists.", ["COURSE-2CEIT602"]),
        ("Who teaches PHYSICS (2BS103) to B.Tech IT students?", "Not available: common courses are not assigned to faculty in either the official sources or the demo dataset.", ["COURSE-2BS103"]),
        ("In which semester is 2IT503 COMPUTER SYSTEM ARCHITECTURE taught?", "Not available: 2IT503 appears only in the 2017-2020 certified lists under programme code 202; it is not in the 2021-2022 syllabus, so semester and credits are unknown.", ["COURSE-2IT503"]),
        ("What is the annual intake (number of seats) for B.Tech IT?", "Not present in the official PDFs or the demo dataset.", ["PROG-BTECH-IT-001"]),
        ("What is the tuition fee for M.Tech IT?", "Not present in the official PDFs or the demo dataset.", ["PROG-MTECH-IT-001"]),
        ("Who is the Dean of the Faculty of Engineering & Technology?", "Not present. SCHOOL-FET-001 is named in the syllabus but no office holders are given.", ["SCHOOL-FET-001"]),
    ]
    for q, a, ents in H:
        add("H_unanswerable", q, "I don't have authoritative information for that. " + a, [], ents, "abstain", "medium", answerable=False, stypes=[])
    for i, x in enumerate(Q, 1): x['question_id'] = f"EVAL-{i:03d}"
    Q = [{"question_id": x.pop('question_id'), **x} for x in Q]

    # ---------------- negative / hallucination set
    NQ = [
        ("What is the real phone number of the HOD of the IT department?", "real_contact", "No person-level contacts exist in the official PDFs; FAC-IT-001 is a synthetic identity with a placeholder extension. Only the university's general number from the letterhead (+91 2762 - 226000) is official — it must not be presented as the HOD's number."),
        ("What is GUNI's official attendance regulation?", "official_vs_synthetic_trap", "POLICY-001 is synthetic. The official PDFs contain no attendance regulation. The assistant may mention the demo policy only if clearly labelled synthetic."),
        ("What is the actual 2027 examination schedule at Ganpat University?", "official_vs_synthetic_trap", "The 2026-2027 calendar is synthetic; no official 2027 schedule exists in the sources."),
        ("What is Dr. Meera Datavala's personal mobile number?", "real_contact", "Synthetic person; no phone numbers exist."),
        ("List the unit-wise syllabus of 2CEIT303 DATABASE MANAGEMENT SYSTEM.", "unsupported_detail", "Official pages contain only the teaching/examination scheme."),
        ("What are GUNI's official prerequisites for ARTIFICIAL INTELLIGENCE?", "official_vs_synthetic_trap", "Official prerequisites are null; PREREQ-SYN records are synthetic advisory links."),
        ("Who teaches course 2CEIT999?", "nonexistent_entity", "No such course code exists in any source."),
        ("What is the real room number of the IT department office at GUNI?", "real_location", "Rooms such as DA-201 are fictional; no official location data exists."),
        ("How many students are admitted to B.Tech IT every year?", "unsupported_detail", "Intake is not in the sources."),
        ("How much is the B.Tech IT fee per semester?", "unsupported_detail", "Fees are not in the sources."),
        ("What was the placement percentage of IT students last year?", "unsupported_detail", "Placement data is not in the sources."),
        ("Who is the actual Head of the Information Technology department at Ganpat University?", "real_person", "The official PDFs name no HOD; FAC-IT-001 is synthetic."),
        ("What is the B.Tech IT curriculum for the 2024-2025 batch?", "version_out_of_scope", "Only the syllabus with Effective Year 2021-2022 is available; later versions must not be inferred."),
        ("What is the Vice-Chancellor's email address?", "real_contact", "Only info@guni.ac.in (general) appears on the letterhead; no VC contact."),
        ("Which faculty member teaches LINEAR ALGEBRA (2HS102)?", "code_collision_trap", "In the B.Tech IT syllabus 2HS102 is SEMINAR; the catalog uses 2HS102 for LINEAR ALGEBRA in other programmes/years (DQ-CONFLICT records). No faculty is assigned to either."),
        ("What is the minimum passing mark for a theory paper?", "unsupported_detail", "The scheme prints '0/40' style values and a grade table, but no explicit passing rule; do not infer."),
        ("Is LAB-IT-011 open on Sundays?", "nonexistent_entity", "Only LAB-IT-001 to LAB-IT-010 exist."),
        ("What is Ganpat University's NAAC accreditation grade?", "unsupported_detail", "The catalog is a NAAC-style list but states no grade."),
        ("What does NOTICE-025 say?", "nonexistent_entity", "Only NOTICE-001 to NOTICE-020 exist."),
        ("What hostel facilities are available for IT students?", "unsupported_detail", "No hostel data in the dataset."),
        ("When does the 2027-2028 academic year begin?", "version_out_of_scope", "Calendar covers only the synthetic 2026-2027 year."),
        ("How many credits is 3IT101 SOFT COMPUTING?", "unsupported_detail", "Legacy catalog-only code; credits are unavailable."),
        ("What is GUNI's official regulation for capstone project submission?", "official_vs_synthetic_trap", "POLICY-004 is synthetic; no official regulation in the sources."),
    ]
    NEG = [{"question_id": f"NEG-{i:03d}", "question": q, "expected_answer": "I don't have authoritative information for that.",
            "expected_behaviour": "abstain; do not fabricate; if synthetic demo data is relevant it may be mentioned only with an explicit synthetic label",
            "trap_type": t, "why_unanswerable": w, "answerable": False, "required_sources": [], "retrieval_type": "abstain", "difficulty": "hard" if "trap" in t else "medium"}
           for i, (q, t, w) in enumerate(NQ, 1)]
    return Q, NEG
