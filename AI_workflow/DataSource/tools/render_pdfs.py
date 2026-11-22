"""Render the 10 synthetic PDFs (one per document) with reportlab. Records the PDF page of every entity."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                KeepTogether, Flowable, PageBreak, CondPageBreak)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape
import synthetic_data as sd

pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVM", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB"); addMapping("DV", 0, 1, "DV"); addMapping("DV", 1, 1, "DVB")

SS = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=SS["BodyText"], fontName="DV", fontSize=9, leading=12.5)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=7.5, leading=9.5)
CELL = ParagraphStyle("c", parent=BODY, fontSize=7.5, leading=9.2)
CELLB = ParagraphStyle("cb", parent=CELL, fontName="DVB")
H1 = ParagraphStyle("h1", parent=BODY, fontName="DVB", fontSize=16, leading=20, spaceAfter=6, textColor=colors.HexColor("#14213d"))
H2 = ParagraphStyle("h2", parent=BODY, fontName="DVB", fontSize=12, leading=15, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#14213d"))
H3 = ParagraphStyle("h3", parent=BODY, fontName="DVB", fontSize=10, leading=13, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#1d3557"))
BANNER = ParagraphStyle("ban", parent=BODY, fontName="DVB", fontSize=9.5, leading=12.5, textColor=colors.HexColor("#8b0000"), alignment=1)
SRC = {"official": "O", "derived_official": "DO", "synthetic": "S"}

def P(t, st=BODY): return Paragraph(t, st)
def e(x): return escape(str(x)) if x is not None else "—"

class Marker(Flowable):
    """Zero-size flowable that records which page an entity starts on."""
    def __init__(self, reg, eid):
        super().__init__(); self.reg = reg; self.eid = eid
    def wrap(self, *a): return (0, 0)
    def draw(self):
        self.reg.setdefault(self.eid, self.canv.getPageNumber())

def table(rows, widths, header=True, font=7.5):
    data = [[c if isinstance(c, Flowable) else P(e(c), CELLB if (header and i == 0) else CELL)
             for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9aa5b1")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header: st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7ecf3")))
    t.setStyle(TableStyle(st)); return t

def kv(pairs, w1=42 * mm, w2=128 * mm):
    return table([[P(f"<b>{e(k)}</b>", CELL), P(v if isinstance(v, str) and v.startswith("<") else e(v), CELL)] for k, v in pairs], [w1, w2], header=False)

def src_line(st, extra=""):
    lab = {"official": "official (GUNI PDF)", "derived_official": "derived_official (structured from GUNI PDF)", "synthetic": "synthetic (CampusMate demo data)"}[st]
    return P(f"<font color='#555555'>source_type: <b>{lab}</b>{(' · ' + extra) if extra else ''}</font>", SMALL)

class Doc:
    def __init__(self, path, meta):
        self.path, self.meta, self.story, self.pages = path, meta, [], {}
    def mark(self, eid): self.story.append(Marker(self.pages, eid))
    def build(self):
        m = self.meta
        def onpage(c, d):
            c.saveState()
            c.setFont("DVB", 7); c.setFillColor(colors.HexColor("#8b0000"))
            c.drawString(15 * mm, 290 * mm, "SYNTHETIC DATA — NOT AN OFFICIAL GANPAT UNIVERSITY DOCUMENT")
            c.setFillColor(colors.HexColor("#444444")); c.setFont("DV", 7)
            c.drawRightString(195 * mm, 290 * mm, f"{m['document_id']} · v{m['version']} · AY {m['academic_year']}")
            c.drawString(15 * mm, 10 * mm, f"{m['filename']} · CampusMate development dataset · generated {m['generated_at'][:10]}")
            c.drawRightString(195 * mm, 10 * mm, f"Page {d.page}")
            c.restoreState()
        doc = BaseDocTemplate(self.path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                              title=m['title'], author="CampusMate synthetic data generator", subject=m['document_id'],
                              keywords=f"synthetic, CampusMate, {m['document_id']}")
        doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(15 * mm, 16 * mm, 180 * mm, 265 * mm, id="f")], onPage=onpage)])
        doc.build(self.story)
        return self.pages

def header(d, entity_ids, intro):
    m = d.meta
    ban = Table([[P(sd.DISCLAIMER, BANNER)]], colWidths=[180 * mm])
    ban.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.4, colors.HexColor("#8b0000")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdecec")),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    d.story += [ban, Spacer(1, 6), P(e(m['title']), H1)]
    ids = ", ".join(entity_ids) if len(entity_ids) <= 40 else ", ".join(entity_ids[:40]) + f" … (+{len(entity_ids) - 40} more; full list in registry/document_registry.json)"
    d.story.append(kv([("document_id", m['document_id']), ("title", m['title']), ("version", m['version']),
        ("academic_year", m['academic_year']), ("generated_at", m['generated_at']), ("source_type", m['source_type']),
        ("contains_source_types", ", ".join(m['contains_source_types'])), ("department_id", m['department_id']),
        ("status", m['status']), ("structured_counterparts", ", ".join(m['structured_counterparts'])),
        ("entity IDs", ids)]))
    d.story += [Spacer(1, 4), P("Source-type legend used in tables: <b>O</b> = official (quoted from a GUNI PDF), <b>DO</b> = derived_official (structured/transformed from a GUNI PDF), <b>S</b> = synthetic (invented for CampusMate testing). Official page numbers refer to physical PDF pages of DOC-OFFICIAL-SYLLABUS-001 (GUNI structured syllabus) or DOC-OFFICIAL-CATALOG-001 (GUNI 1.1.3 course list).", SMALL),
                Spacer(1, 4), P(intro), Spacer(1, 6)]

# ----------------------------------------------------------------- per-document builders
def dept_profile(d, T, L):
    D = T['departments'][0]; F = {f['faculty_id']: f for f in T['faculty']}
    header(d, [D['department_id']] + D['program_ids'] + D['research_area_ids'], "This profile describes the synthetic Department of Information Technology (DEPT-IT-001). Only the programme names, the Faculty/College hierarchy and curriculum figures are taken from official GUNI documents; everything else is synthetic.")
    d.mark(D['department_id'])
    d.story += [P("1. Department identity — DEPT-IT-001", H2), src_line("synthetic"),
                kv([("department_id", D['department_id']), ("department_name", D['department_name']), ("short_name", D['short_name']),
                    ("parent org unit", "COLLEGE-UVPCE-001 U.V. Patel College of Engineering (official name) — link to DEPT-IT-001 is synthetic"),
                    ("Head of Department", f"{F[D['head_faculty_id']]['name']} ({D['head_faculty_id']})"),
                    ("office", "ROOM-DA-201, Demo Academic Block A (synthetic)")]),
                P("2. Overview", H2), src_line("synthetic"), P(e(D['overview'])),
                P("3. Vision", H2), src_line("synthetic"), P(e(D['vision'])),
                P("4. Mission", H2), src_line("synthetic")] + [P(f"M{i}. {e(x)}") for i, x in enumerate(D['mission'], 1)] + [
                P("5. Focus areas", H2), src_line("synthetic"), P("; ".join(e(x) for x in D['focus_areas']) + ".")]
    d.story += [P("6. Institutional context (official)", H2), src_line("official", "DOC-OFFICIAL-SYLLABUS-001 p.10, DOC-OFFICIAL-CATALOG-001 p.1"),
                table([["Entity ID", "Name", "Type", "Src", "Source"],
                       ["UNIV-GUNI-001", "Ganpat University", "university", "O", "Catalog p.1 letterhead; syllabus page headers"],
                       ["SCHOOL-FET-001", "Faculty of Engineering & Technology", "faculty/school", "O", "Syllabus p.10 header"],
                       ["COLLEGE-UVPCE-001", "U.V. Patel College of Engineering", "college", "O", "Syllabus p.10 header"],
                       ["DEPT-IT-001", "Department of Information Technology", "department", "S", "CampusMate demo entity"]],
                      [34 * mm, 58 * mm, 24 * mm, 10 * mm, 54 * mm])]
    d.story += [P("7. Programmes offered", H2), src_line("derived_official", "names/credits from the GUNI syllabus; DEPT-IT-001 OFFERS link is synthetic")]
    for p in T['programs']: d.mark(p['program_id'])
    d.story.append(table([["Program ID", "Programme (official name)", "Short", "Semesters", "Total credits", "Official pages"]] +
        [[p['program_id'], p['program_name'], p['short_name'], p['number_of_semesters'], p['total_credits'],
          f"Syllabus pp.{p['semester_ids'] and ', '.join(str(s['source_page']) for s in T['semesters'] if s['program_id'] == p['program_id'])}"] for p in T['programs']],
        [34 * mm, 56 * mm, 20 * mm, 18 * mm, 20 * mm, 32 * mm]))
    d.story += [P("8. Research areas", H2), src_line("synthetic")]
    for r in T['research_areas']: d.mark(r['research_area_id'])
    fac_by_ra = {}
    for f in T['faculty']:
        for r in f['research_area_ids']: fac_by_ra.setdefault(r, []).append(f['faculty_id'])
    d.story.append(table([["Research area ID", "Research area", "Faculty IDs"]] + [[r['research_area_id'], r['name'], ", ".join(fac_by_ra.get(r['research_area_id'], []))] for r in T['research_areas']],
                         [30 * mm, 70 * mm, 80 * mm]))
    d.story += [P("9. Laboratories and facilities (summary)", H2), src_line("synthetic", "details in DOC-LABS-001 and DOC-FACILITIES-001")]
    d.story.append(table([["ID", "Name", "Room", "Capacity"]] + [[l['lab_id'], l['lab_name'], l['room_number'], l['capacity']] for l in T['laboratories']] +
                         [[f['facility_id'], f['facility_name'], f['room_id'].replace('ROOM-', ''), f['capacity']] for f in T['facilities']],
                         [30 * mm, 90 * mm, 30 * mm, 30 * mm]))
    c = D['contact']
    d.story += [P("10. Contact placeholders", H2), src_line("synthetic", "no real contact details"),
                kv([("Department office email", c['office_email']), ("HOD office email", c['hod_office_email']), ("Projects email", c['projects_email']),
                    ("Laboratory bookings", c['labs_email']), ("Phone", c['phone']), ("Office hours", c['office_hours'])]),
                Spacer(1, 4), P("All e-mail addresses use the reserved <b>.example</b> domain and are not deliverable. For real Ganpat University contacts see the official university letterhead (UNIV-GUNI-001, catalog p.1); no department-level contacts exist in the official sources.", SMALL)]

def faculty_dir(d, T, L):
    C = {c['course_id']: c for c in T['courses']}; S = {s['semester_id']: s for s in T['semesters']}
    header(d, [f['faculty_id'] for f in T['faculty']], "Directory of 20 fictional faculty members of DEPT-IT-001. Names, designations, qualifications, e-mails, offices and teaching assignments are synthetic. Course codes and course names in the 'courses taught' tables are official (GUNI syllabus); the assignment of a faculty member to a course is synthetic.")
    d.story += [P("1. Directory summary", H2), src_line("synthetic"),
                table([["Faculty ID", "Name", "Designation", "Specialization", "Office"]] +
                      [[f['faculty_id'], f['name'], f['designation'], f['specialization'], f['office_id'].replace('ROOM-', '')] for f in T['faculty']],
                      [22 * mm, 38 * mm, 38 * mm, 64 * mm, 18 * mm]), PageBreak(), P("2. Faculty profiles", H2)]
    TA = T['teaching_assignments']
    for f in T['faculty']:
        rows = [["Course ID", "Code", "Course name (official)", "Semester", "Role (S)"]]
        for a in [x for x in TA if x['faculty_id'] == f['faculty_id']]:
            c = C[a['course_id']]; s = S.get(c['semester_id'])
            rows.append([c['course_id'], c['course_code'], c['course_name'], f"{s['program_id'].split('-')[1]} IT {s['semester_name']}" if s else "—", a['role']])
        blk = [Marker(d.pages, f['faculty_id']), P(f"{f['faculty_id']} — {e(f['name'])}", H3), src_line("synthetic", f['identity_note']),
               kv([("faculty_id", f['faculty_id']), ("designation", f['designation']), ("department_id", f['department_id']),
                   ("qualification", f['qualification']), ("specialization", f['specialization']),
                   ("research areas", "; ".join(f"{r} {n}" for r, n in zip(f['research_area_ids'], f['research_areas']))),
                   ("email", f['email']), ("office_id", f"{f['office_id']} (Demo Academic Block A)"),
                   ("consultation hours", f['consultation_hours']), ("joining_year", f['joining_year'])]),
               Spacer(1, 3), table(rows, [30 * mm, 24 * mm, 70 * mm, 36 * mm, 20 * mm]), Spacer(1, 6)]
        d.story.append(KeepTogether(blk))

def programs_doc(d, T, L):
    C = {c['course_id']: c for c in T['courses']}
    header(d, [p['program_id'] for p in T['programs']] + [s['semester_id'] for s in T['semesters']] + [g['elective_group_id'] for g in T['elective_groups']],
           "Semester-wise curriculum of B.Tech IT (PROG-BTECH-IT-001) and M.Tech IT (PROG-MTECH-IT-001). All course codes, titles, credits, hours and marks are transcribed from the official GUNI structured syllabus (Effective Year 2021-2022, dated 28/09/2022) and verified against the printed semester totals. Synthetic content is limited to the labelled programme summaries.")
    for p in T['programs']:
        d.story.append(PageBreak()) if p['program_id'] != 'PROG-BTECH-IT-001' else None
        d.mark(p['program_id'])
        d.story += [P(f"{p['program_id']} — {e(p['program_name'])} ({p['short_name']})", H2), src_line("official", f"DOC-OFFICIAL-SYLLABUS-001 p.{p['source_page']}"),
                    kv([("program_id", p['program_id']), ("programme name", p['program_name'] + " [O]"), ("short name", p['short_name'] + " [O]"),
                        ("degree type", p['degree_type'] + " [DO]"), ("hosted by", "COLLEGE-UVPCE-001 U.V. Patel College of Engineering, SCHOOL-FET-001 Faculty of Engineering & Technology [O]"),
                        ("department", "DEPT-IT-001 Department of Information Technology [S]"),
                        ("semesters", f"{p['number_of_semesters']} ({', '.join(p['semester_ids'])}) [DO]"),
                        ("total credits", f"{p['total_credits']} (sum of official semester totals) [DO]"),
                        ("effective year", p['effective_year'] + " [O]"), ("catalog program code", f"{p['catalog_program_code']} = {p['catalog_program_name']} (DOC-OFFICIAL-CATALOG-001) [O]"),
                        ("programme description", "Not available in official sources."),
                        ("synthetic summary", p['synthetic_program_description'] + " [S]"),
                        ("programme coordinator", p['synthetic_program_coordinator_faculty_id'] + " [S]")])]
        for s in [x for x in T['semesters'] if x['program_id'] == p['program_id']]:
            rows = [["Course ID", "Code", "Title", "Type", "TH", "PR", "Cr", "Hrs", "Marks", "Src"]]
            for o in [x for x in T['course_offerings'] if x['semester_id'] == s['semester_id'] and x['course_type'] == 'regular']:
                c = C[o['course_id']]; k = o['credit_scheme']
                rows.append([c['course_id'], c['course_code'], c['course_name'], "Regular", k['credit_th'], k['credit_pr'], k['credit_total'], k['contact_hours'], k['total_marks'], "O"])
            for g in [x for x in T['elective_groups'] if x['semester_id'] == s['semester_id']]:
                k = g['slot_scheme']
                rows.append([g['elective_group_id'], "—", f"{g['slot_title']}: choose one of " + ", ".join(C[c]['course_code'] for c in g['option_course_ids']),
                             g['slot_kind'].title(), k['credit_th'], k['credit_pr'], k['credit_total'], k['contact_hours'], k['total_marks'], "O"])
            rows.append(["", "", "SEMESTER TOTAL (printed in syllabus)", "", s['total_credits_th'], s['total_credits_pr'], s['total_credits'], s['total_contact_hours'], s['total_marks'], "O"])
            blk = [Marker(d.pages, s['semester_id']), P(f"{s['semester_id']} — {p['short_name']} {s['semester_name']}", H3),
                   src_line("official", f"DOC-OFFICIAL-SYLLABUS-001 p.{', '.join(map(str, s['source_pages']))} · Total Course {s['total_course']}, Regular {s['total_regular_course']}, Elective {s['total_elective_course']}, Open {s['total_open_course']}, Audit {s['total_audit_course']}"),
                   table(rows, [30 * mm, 18 * mm, 58 * mm, 14 * mm, 9 * mm, 9 * mm, 9 * mm, 9 * mm, 12 * mm, 8 * mm])]
            gl = [x for x in T['elective_groups'] if x['semester_id'] == s['semester_id']]
            if gl:
                er = [["Group ID", "Group", "Option course ID", "Code", "Course name", "Src"]]
                for g in gl:
                    d.mark(g['elective_group_id'])
                    for c in g['option_course_ids']:
                        er.append([g['elective_group_id'], g['group_name'], c, C[c]['course_code'], C[c]['course_name'], "O"])
                blk += [Spacer(1, 3), table(er, [44 * mm, 26 * mm, 30 * mm, 22 * mm, 50 * mm, 8 * mm])]
            d.story += [KeepTogether(blk[:4])] + blk[4:] + [Spacer(1, 6)]
    d.story += [PageBreak(), P("Examination grade range & value (official)", H2), src_line("official", "DOC-OFFICIAL-SYLLABUS-001 p.10 (repeated on every semester page)")]
    for g in T['grading_scheme']: d.mark(g['grade_band_id'])
    d.story.append(table([["Grade band ID", "Marks/Perc. range", "Grade (Regular)", "Grade point (Regular)", "Grade (Remedial)", "Grade point (Remedial)"]] +
        [[g['grade_band_id'], g['marks_range'], g['grade_regular'], g['grade_point_regular'], g['grade_remedial'], g['grade_point_remedial']] for g in T['grading_scheme']],
        [28 * mm, 30 * mm, 28 * mm, 32 * mm, 28 * mm, 34 * mm]))
    d.story += [P("Notes on interpretation", H2), src_line("derived_official"),
                P("• The examination scheme prints marks as '0/40', '0/60' etc. CampusMate stores the raw string and interprets the denominator as maximum marks (derived_official)."),
                P("• Elective, audit and open slots carry one credit/marks scheme per slot. Each option course inherits that slot's scheme (derived_official)."),
                P("• Prerequisites, course descriptions, teaching departments and faculty are NOT given in the official syllabus pages. Any such values in CampusMate are synthetic and labelled.")]

def course_catalog(d, T, L):
    S = {s['semester_id']: s for s in T['semesters']}; F = {f['faculty_id']: f for f in T['faculty']}
    Lb = {l['lab_id']: l for l in T['laboratories']}; C = {c['course_id']: c for c in T['courses']}
    header(d, [c['course_id'] for c in T['courses']], "Course-level records for every course code appearing in the B.Tech IT and M.Tech IT curricula of the official GUNI syllabus, plus five legacy IT course codes that appear only in the official certified course list. Each entry separates official fields [O], derived fields [DO] and synthetic enrichment [S].")
    groups = [("A. B.Tech IT department courses", lambda c: c['course_code'].startswith('2CEIT')),
              ("B. M.Tech IT department courses", lambda c: c['course_code'].startswith('3CEIT')),
              ("C. Common / basic courses in the B.Tech IT and M.Tech IT schemes", lambda c: c['curriculum_status'] != 'legacy_catalog_only' and not c['course_code'].startswith(('2CEIT', '3CEIT'))),
              ("D. Legacy IT course codes found only in the certified course list", lambda c: c['curriculum_status'] == 'legacy_catalog_only')]
    for gi, (title, fn) in enumerate(groups):
        if gi: d.story.append(PageBreak())
        d.story.append(P(title, H2))
        for c in [x for x in T['courses'] if fn(x)]:
            s = S.get(c['semester_id']); k = c['credit_scheme']
            sem_txt = ", ".join(f"{S[x]['semester_id']} ({S[x]['program_id'].split('-')[1]} IT {S[x]['semester_name']})" for x in c['semester_ids']) or "Not available (not in 2021-2022 syllabus)"
            cat = "; ".join(f"{x['academic_year']} under code {x['catalog_program_code']} {x['catalog_program_name']} (p.{x['source_page']})" for x in c['catalog_listings']) or "Not listed"
            shared = ", ".join(x['program_short_name'] for x in c.get('shared_with_other_syllabus_programs', [])) or "—"
            pairs = [("course_id", c['course_id']), ("course_code [O]", c['course_code']), ("course_name [O]", c['course_name']),
                     ("program [O]", ", ".join(c['program_ids'])), ("semester", sem_txt + (" [O]" if c['course_type'] == 'regular' else " [DO]")),
                     ("course_type", (c['course_type'] or "not available") + (f" — group {c['elective_group_id']}" if c['elective_group_id'] else "")),
                     ("credits", (f"{c['credits']} (TH {k['credit_th']} + PR/TW {k['credit_pr']}); {k['contact_hours']} contact hours; total marks {k['total_marks']} (TH int/ext {k['th_internal_max']}/{k['th_external_max']}, PR int/ext {k['pr_internal_max']}/{k['pr_external_max']})" + (" [O]" if c['course_type'] == 'regular' else " [DO: inherited from slot]")) if k else "Not available"),
                     ("official source", f"{c['source_document']} p.{c['source_page']} — {c['source_section']}"),
                     ("also in syllabus of [DO]", shared),
                     ("employability catalog [O]", cat),
                     ("prerequisites (official)", "Not specified in official sources"),
                     ("synthetic prerequisites [S]", ", ".join(f"{x} {C[x]['course_name']}" for x in c['synthetic_prerequisites']) or "—"),
                     ("faculty [S]", ", ".join(f"{x} {F[x]['name']}" for x in c['faculty_ids']) or ("Not assigned in demo dataset" if not c['department_id'] else "—")),
                     ("laboratory [S]", ", ".join(f"{x} {Lb[x]['lab_name']} (Room {Lb[x]['room_number']})" for x in c['lab_ids']) or "—"),
                     ("synthetic description [S]", c['synthetic_description'] or "—")]
            if c['curriculum_status'] == 'legacy_catalog_only': pairs.append(("curriculum note [DO]", c['curriculum_note']))
            d.story.append(KeepTogether([Marker(d.pages, c['course_id']), P(f"{c['course_id']} — {c['course_code']} {e(c['course_name'])}", H3),
                                         kv(pairs, 44 * mm, 136 * mm), Spacer(1, 5)]))
    d.story += [PageBreak(), P("E. Synthetic advisory prerequisite map (REQUIRES)", H2), src_line("synthetic", "not an official GUNI prerequisite list")]
    for p in T['course_prerequisites']: d.mark(p['prerequisite_id'])
    d.story.append(table([["Prerequisite ID", "Course", "Requires", "Strength"]] +
        [[p['prerequisite_id'], f"{C[p['course_id']]['course_code']} {C[p['course_id']]['course_name']}", f"{C[p['requires_course_id']]['course_code']} {C[p['requires_course_id']]['course_name']}", p['strength']] for p in T['course_prerequisites']],
        [28 * mm, 66 * mm, 66 * mm, 20 * mm]))
    d.story += [P("F. Data-quality findings in the official sources", H2), src_line("derived_official")]
    d.story.append(table([["Conflict ID", "Code", "Name in syllabus", "Name in catalog", "Year / program code", "Catalog page"]] +
        [[x['conflict_id'], x['course_code'], x['syllabus_course_name'], x['catalog_course_name'], f"{x['academic_year']} / {x['catalog_program_code']}", x['source_page']] for x in T['data_quality_conflicts']],
        [24 * mm, 18 * mm, 36 * mm, 50 * mm, 32 * mm, 20 * mm]))

def labs_doc(d, T, L):
    C = {c['course_id']: c for c in T['courses']}; F = {f['faculty_id']: f for f in T['faculty']}
    header(d, [l['lab_id'] for l in T['laboratories']], "Ten fictional teaching laboratories of DEPT-IT-001. Buildings, rooms, equipment, hours and course associations are synthetic. Course codes/names shown are official.")
    d.story += [P("1. Laboratory summary", H2), src_line("synthetic"),
                table([["Lab ID", "Laboratory", "Location", "Capacity", "Responsible faculty"]] +
                      [[l['lab_id'], l['lab_name'], f"{l['building']}, Floor {l['floor']}, Room {l['room_number']}", l['capacity'], f"{l['responsible_faculty_id']} {F[l['responsible_faculty_id']]['name']}"] for l in T['laboratories']],
                      [22 * mm, 44 * mm, 56 * mm, 16 * mm, 42 * mm]), P("2. Laboratory details", H2)]
    for l in T['laboratories']:
        d.story.append(KeepTogether([Marker(d.pages, l['lab_id']), P(f"{l['lab_id']} — {e(l['lab_name'])}", H3), src_line("synthetic"),
            kv([("lab_id", l['lab_id']), ("department_id", l['department_id']), ("building", f"{l['building']} ({l['building_id']})"),
                ("floor / room", f"Floor {l['floor']}, Room {l['room_number']} ({l['room_id']})"), ("capacity", f"{l['capacity']} students"),
                ("responsible faculty", f"{l['responsible_faculty_id']} {F[l['responsible_faculty_id']]['name']}"),
                ("opening hours", l['opening_hours']), ("equipment", "; ".join(l['equipment'])),
                ("related courses", "; ".join(f"{x} ({C[x]['course_name']})" for x in l['related_courses'])),
                ("governing policies", ", ".join(l['governing_policy_ids']) + " (Laboratory Usage Policy, Laboratory Safety Policy)"),
                ("booking contact", l['booking_contact'])]), Spacer(1, 6)]))

def facilities_doc(d, T, L):
    header(d, [f['facility_id'] for f in T['facilities']] + [r['room_id'] for r in T['rooms']] + [b['building_id'] for b in T['buildings']],
           "Ten fictional shared facilities of DEPT-IT-001 plus the fictional building and room register that all synthetic locations refer to.")
    d.story += [P("1. Facilities", H2)]
    for f in T['facilities']:
        d.story.append(KeepTogether([Marker(d.pages, f['facility_id']), P(f"{f['facility_id']} — {e(f['facility_name'])}", H3), src_line("synthetic"),
            kv([("facility_id", f['facility_id']), ("type", f['facility_type']), ("department_id", f['department_id']), ("location", f"{f['location']} ({f['room_id']})"),
                ("capacity", f['capacity']), ("availability", f['availability']), ("description", f['description'])]), Spacer(1, 5)]))
    d.story += [PageBreak(), P("2. Buildings", H2), src_line("synthetic")]
    for b in T['buildings']: d.mark(b['building_id'])
    d.story.append(table([["Building ID", "Name", "Code", "Floors", "Description"]] + [[b['building_id'], b['name'], b['code'], b['floors'], b['description']] for b in T['buildings']],
                         [26 * mm, 40 * mm, 12 * mm, 12 * mm, 90 * mm]))
    d.story += [P("3. Room register", H2), src_line("synthetic")]
    for r in T['rooms']: d.mark(r['room_id'])
    d.story.append(table([["Room ID", "Room no.", "Building", "Floor", "Type", "Label"]] + [[r['room_id'], r['room_number'], r['building_id'], r['floor'], r['room_type'], r['label']] for r in T['rooms']],
                         [28 * mm, 18 * mm, 28 * mm, 12 * mm, 30 * mm, 64 * mm]))

def policies_doc(d, T, L):
    header(d, [p['policy_id'] for p in T['policies']], "Eleven synthetic department policies. <b>None of these is a Ganpat University regulation.</b> Each clause is numbered as &lt;policy_number&gt; §n so that answers can cite the exact clause.")
    d.story += [P("1. Policy index", H2), src_line("synthetic"),
                table([["Policy ID", "Policy number", "Title", "Category", "Applies to programmes"]] + [[p['policy_id'], p['policy_number'], p['title'], p['category'], ", ".join(p['applies_to_program_ids'])] for p in T['policies']],
                      [22 * mm, 30 * mm, 56 * mm, 26 * mm, 46 * mm]), PageBreak()]
    for p in T['policies']:
        blk = [Marker(d.pages, p['policy_id']), P(f"{p['policy_id']} — {p['policy_number']} {e(p['title'])}", H2), src_line("synthetic"),
               P(f"<i>{e(p['synthetic_notice'])}</i>", SMALL),
               kv([("policy_id", p['policy_id']), ("policy_number", p['policy_number']), ("category", p['category']), ("version / status", f"{p['version']} / {p['status']}"),
                   ("effective", f"{p['effective_from']} to {p['effective_to']}"), ("applies to department", ", ".join(p['applies_to_department_ids'])),
                   ("applies to programmes", ", ".join(p['applies_to_program_ids'])), ("related courses", ", ".join(p['related_course_ids']) or "—"),
                   ("related labs", ", ".join(p['related_lab_ids']) or "—"), ("related facilities", ", ".join(p['related_facility_ids']) or "—"),
                   ("policy owner", p['owner_faculty_id']), ("summary", p['summary'])]), Spacer(1, 3)]
        blk += [P(f"<b>{p['policy_number']} §{i}.</b> {e(c)}") for i, c in enumerate(p['clauses'], 1)]
        d.story += [KeepTogether(blk), Spacer(1, 8)]

def calendar_doc(d, T, L):
    header(d, [c['event_id'] for c in T['academic_calendar']], "Synthetic academic calendar for the demo academic year 2026-2027. <b>All dates are synthetic and are not an actual Ganpat University schedule.</b>")
    for term in ("Odd", "Even"):
        ev = sorted([c for c in T['academic_calendar'] if c['term'].startswith(term)], key=lambda x: x['start_date'])
        d.story += [P(f"{term} semester {sd.AY}", H2), src_line("synthetic")]
        for c in ev: d.mark(c['event_id'])
        d.story.append(table([["Event ID", "Event", "Type", "Start", "End", "Semesters"]] +
            [[c['event_id'], c['title'], c['event_type'], c['start_date'], c['end_date'], ", ".join(c['semester_ids'])] for c in ev],
            [28 * mm, 54 * mm, 24 * mm, 18 * mm, 18 * mm, 38 * mm]))
    d.story += [P("Key dates in prose", H2), src_line("synthetic")]
    for c in sorted(T['academic_calendar'], key=lambda x: x['start_date']):
        when = c['start_date'] if c['start_date'] == c['end_date'] else f"{c['start_date']} to {c['end_date']}"
        d.story.append(P(f"<b>{c['event_id']}</b> ({c['event_type']}): {e(c['title'])} — {when}. Applies to {', '.join(c['program_ids'])}."))

def notices_doc(d, T, L):
    header(d, [n['notice_id'] for n in T['notices']], "Twenty synthetic department notices dated June–September 2026. Status is computed as of 2026-09-18: <b>active</b>, <b>expired</b> (expiry date passed) or <b>superseded</b> (replaced by a later notice).")
    d.story += [P("1. Notice index", H2), src_line("synthetic"),
                table([["Notice ID", "Date", "Category", "Title", "Status"]] + [[n['notice_id'], n['date'], n['category'], n['title'], n['status']] for n in sorted(T['notices'], key=lambda x: x['date'])],
                      [22 * mm, 20 * mm, 22 * mm, 96 * mm, 20 * mm]), P("2. Notices", H2)]
    for n in sorted(T['notices'], key=lambda x: x['date']):
        rel = n['related_course_ids'] + n['related_faculty_ids'] + n['related_lab_ids'] + n['related_facility_ids'] + n['related_policy_ids'] + n['related_calendar_ids']
        d.story.append(KeepTogether([Marker(d.pages, n['notice_id']), P(f"{n['notice_id']} — {e(n['title'])}", H3), src_line("synthetic"),
            kv([("notice_id", n['notice_id']), ("date issued", n['date']), ("department_id", n['department_id']), ("category", n['category']),
                ("target audience", ", ".join(n['target_audience'])), ("effective / expiry", f"{n['effective_date']} / {n['expiry_date']}"),
                ("status (as of 2026-09-18)", n['status'] + (f" — superseded by {n['superseded_by']}" if n['superseded_by'] else "") + (f" — supersedes {n['supersedes']}" if n['supersedes'] else "")),
                ("related entities", ", ".join(rel) or "—")]), Spacer(1, 2), P(e(n['content'])), Spacer(1, 6)]))

def faq_doc(d, T, L):
    header(d, [q['faq_id'] for q in T['faq']], "Synthetic student-services FAQ for DEPT-IT-001. Answers that quote curriculum or grading facts cite the official GUNI syllabus; all other answers are synthetic and refer to synthetic policies, facilities and people.")
    cats = []
    for q in T['faq']:
        if q['category'] not in cats: cats.append(q['category'])
    for cat in cats:
        d.story += [P(cat.replace('_', ' ').title(), H2)]
        for q in [x for x in T['faq'] if x['category'] == cat]:
            d.story.append(KeepTogether([Marker(d.pages, q['faq_id']), P(f"{q['faq_id']} — {e(q['question'])}", H3),
                src_line("synthetic", "answer basis: " + q['answer_basis']), P(e(q['answer'])),
                P(f"<font color='#555555'>Related entities: {', '.join(q['related_entity_ids'])}</font>", SMALL), Spacer(1, 4)]))

BUILDERS = {"DOC-DEPT-PROFILE-001": dept_profile, "DOC-FACULTY-001": faculty_dir, "DOC-PROGRAMS-001": programs_doc,
            "DOC-COURSES-001": course_catalog, "DOC-LABS-001": labs_doc, "DOC-FACILITIES-001": facilities_doc,
            "DOC-POLICIES-001": policies_doc, "DOC-CALENDAR-001": calendar_doc, "DOC-NOTICES-001": notices_doc, "DOC-FAQ-001": faq_doc}

def render(meta, T, path):
    d = Doc(path, meta)
    BUILDERS[meta['document_id']](d, T, None)
    return d.build()
