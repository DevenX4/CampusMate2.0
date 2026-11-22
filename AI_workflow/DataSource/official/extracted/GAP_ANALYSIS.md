# Official source inventory and gap analysis

Sources (page numbers are physical PDF pages):

| Document ID | File | What it actually is |
|---|---|---|
| DOC-OFFICIAL-SYLLABUS-001 | `official/GUNI_BTech_IT_Syllabus.pdf` (orig. `1.2.2._1_GUNI_A_STRUCTURED_SYLLABUS.pdf`) | University-wide "Syllabus Details", Effective Year 2021-2022, pages dated 28/09/2022, 742 pages. **Teaching and examination schemes only; no unit-wise content for B.Tech IT.** B.Tech IT = pp.10–18, M.Tech IT = pp.104–108. |
| DOC-OFFICIAL-CATALOG-001 | `official/GUNI_Course_Catalog.pdf` (orig. `1.1.3_Certified_Document.pdf`) | Certified NAAC-style list **1.1.3: courses focused on employability/entrepreneurship/skill development**, 2017-18 to 2021-22, 137 pages, signed by the Executive Registrar (Admin). **Not a descriptive course catalogue.** |

## 1. What IS available (official / derived_official)

| Information | Where | Stored as |
|---|---|---|
| University name, postal address, general phone/fax/toll-free, general email, website | Catalog p.1 letterhead | `university.json` (official) |
| Faculty of Engineering & Technology; U.V. Patel College of Engineering | Syllabus page headers | `org_units.json` (official) |
| Programme names and short names (B.TECH-IT, M.TECH-IT) | Syllabus pp.10, 104 | `programs.json` (official) |
| Catalog programme codes 202 = BTech(Information Technology), 402 = Mtech(Information Technology) | Catalog | `programs.json` (official) |
| Number of semesters, total programme credits (174 / 74) | Sum of semester pages | `programs.json` (derived_official) |
| Per semester: course counts (total/regular/elective/open/audit), credit/hour/marks totals | Semester headers & totals | `semesters.json` (official) |
| Course code, title, TH/PR credits, total credits, contact hours, internal/external marks | Semester course tables | `courses.json`, `course_offerings.json` (official) |
| Elective/audit/open slots with the list of option courses | "List of Elective/Audit/Open Subjects" | `elective_groups.json` (official); option credits inherited from slot (derived_official) |
| Grade table (marks → grade → grade point, regular & remedial) | Every semester page | `grading_scheme.json` (official) |
| Which other programmes' schemes list the same course code (e.g. B.TECH-CE, B.TECH-CE(AI)) | Other syllabus pages | `courses.json → shared_with_other_syllabus_programs` (derived_official) |
| Year-wise employability-list membership of each course | Catalog pages | `courses.json → catalog_listings` (official) |
| Legacy IT codes 2IT302, 2IT503, 2IT606, 3IT101, 3IT201 | Catalog only (2017-20) | `courses.json` with `curriculum_status = legacy_catalog_only` |
| Year-wise counts of listed courses: 2021-22 1964, 2020-21 1894, 2019-20 1845, 2018-19 1756, 2017-18 1506 | Catalog p.1 | noted here |

## 2. What is MISSING from the official sources

Fields are stored as `null` (never guessed). Where CampusMate needs the structure for testing, a clearly-labelled synthetic stand-in exists:

| Missing information | Official value | Synthetic stand-in |
|---|---|---|
| A department entity for IT, its head, vision, mission | none | `DEPT-IT-001`, `FAC-IT-001` |
| Faculty members, designations, contacts, offices | none | 20 × `FAC-IT-0xx` |
| Who teaches which course | none | `teaching_assignments.json` |
| Course descriptions, units, outcomes, textbooks | `null` | `synthetic_description` (labelled) |
| Course prerequisites | `null` | `course_prerequisites.json` (`PREREQ-SYN-*`, advisory) |
| Laboratories, equipment, rooms, buildings | none | `LAB-IT-*`, `ROOM-*`, `BLDG-DEMO-*` |
| Department facilities | none | `FCL-IT-*` |
| Regulations (attendance, passing rules, project submission, lab rules) | none | `POLICY-001…011` (synthetic) |
| Academic calendar, exam dates, holidays | none | `CAL-2026-27-*` |
| Notices / circulars | none | `NOTICE-001…020` |
| Student services / FAQ | none | `FAQ-001…032` |
| Department-level contacts | none | placeholders on `campusmate-demo.example` |
| Intake, fees, placements, accreditation grade, dean/HOD names, timetable, syllabus versions after 2021-2022 | none | **none — deliberately left unanswerable** (see `evaluation/negative_questions.json`) |

## 3. Data-quality findings in the official sources

1. **Course codes are not globally unique.** 2HS101 is COMMUNICATION SKILLS in the B.Tech IT syllabus but CALCULUS in other programmes/years of the catalog; 2HS102 is SEMINAR vs LINEAR ALGEBRA; 3OS201 is OPEN SUBJECT vs ENGLISH LANGUAGE & COMMUNICATION SKILLS. There are 10 records in `data_quality_conflicts.json`. Catalog lookups must key on (code, programme code, year).
2. **The catalog lists B.Tech IT's 2CEIT courses under programme code 201 BTech(Computer Engineering)**, not 202. Code 202 only carries the legacy 2IT codes.
3. The M.Tech IT Semester II header prints "Total Course 12 / Total Elective Course 8", counting elective options rather than slots. It is stored verbatim.
4. The examination scheme prints marks as `0/40`, `0/60`, etc. The raw string is kept, and only the denominator is interpreted (as maximum marks, derived_official). No passing rule is inferred.
5. Electives carry credits per **slot**, not per option. Option credits are inherited from the slot and marked derived_official.
6. The syllabus PDF is university-wide. The file was renamed to the package convention, and the original filename is kept in the registry.
