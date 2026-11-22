# CampusMate dataset — consistency audit

Generated 2026-09-18T12:00:00+05:30. Result: **{'PASS': 37}**

| # | Check | Status | Detail |
|---|---|---|---|
| 1 | no duplicate entity IDs across all tables | PASS | 566 unique IDs |
| 2 | no duplicate course codes | PASS | 116 codes |
| 3 | no duplicate course (name, program) pairs | PASS | ok |
| 4 | department / lab / facility / faculty names unique | PASS |  |
| 5 | no orphan foreign keys (60 FK rules) | PASS | 0 orphans |
| 6 | FAQ references resolve | PASS | ok |
| 7 | all 1202 relationships resolve | PASS | ok |
| 8 | every faculty member teaches >=1 course | PASS | ok |
| 9 | faculty.courses_taught == teaching_assignments | PASS |  |
| 10 | labs <-> courses bidirectionally consistent | PASS |  |
| 11 | prerequisite graph is acyclic | PASS |  |
| 12 | synthetic prerequisites always point to an earlier semester | PASS | ok |
| 13 | every record has a valid source_type | PASS | ok |
| 14 | all invented entity tables are labelled synthetic and cite synthetic documents | PASS | ok |
| 15 | every official/derived_official record cites a GUNI PDF + page | PASS | ok |
| 16 | mixed course records flag synthetic fields in field_provenance | PASS | ok |
| 17 | official prerequisites/description left null (not invented) | PASS |  |
| 18 | no real-looking contact data in synthetic tables (all emails @campusmate-demo.example) | PASS |  |
| 19 | every policy carries the synthetic-policy statement | PASS | ok |
| 20 | every official course / semester / elective group re-verified on its cited PDF page | PASS | 116 courses, 12 semesters, 18 groups verified |
| 21 | per-semester credits reconcile with printed totals | PASS | 12/12 semesters reconcile |
| 22 | programme totals = sum of semester totals | PASS | {"PROG-BTECH-IT-001": 174.0, "PROG-MTECH-IT-001": 74.0} |
| 23 | semester naming consistent (SEM-<PROG>-NN / 'Semester <ROMAN>') | PASS |  |
| 24 | synthetic academic_year consistently '2026-2027' | PASS |  |
| 25 | single department name used everywhere | PASS |  |
| 26 | ID formats | PASS |  |
| 27 | notice status consistent with dates (as of 2026-09-18) | PASS |  |
| 28 | calendar dates valid (end >= start) | PASS |  |
| 29 | registry file hashes match files | PASS | 12 documents |
| 30 | every synthetic PDF: disclaimer banner on p.1, header on every page, metadata block, entity IDs present as text | PASS | 10/10 PDFs |
| 31 | 10 separate synthetic PDFs, none merged | PASS |  |
| 32 | registry entity_ids resolve | PASS | ok |
| 33 | every entity (except offering rows) is described by >=1 registered document | PASS | ok |
| 34 | OKF items (297) have valid id/source_type and resolvable relationships | PASS | ok |
| 35 | evaluation set: 58 questions across 8 categories (A–H); 23 negatives | PASS | {"A_simple_factual": 8, "B_exact_lexical": 8, "C_semantic": 7, "D_metadata_filtered": 7, "E_multi_hop": 8, "F_cross_document": 7, "G_structured_sql": 7, "H_unan |
| 36 | schema.sql + seed.sql load into PostgreSQL 16 with all FK/CHECK constraints | PASS | loaded |
| 37 | all 14 reference SQL queries execute and return rows | PASS | ok |

## Record counts by source_type

```
{
 "official": 145,
 "synthetic": 286,
 "derived_official": 135
}
```

## Relationship edges by source_type

```
{
 "official": 320,
 "synthetic": 751,
 "derived_official": 131
}
```

## Data-quality findings in the official sources

- DQ-CONFLICT-001: 2HS101 = 'COMMUNICATION SKILLS' in syllabus but 'CALCULUS' in catalog 2017-2018 prog 201
- DQ-CONFLICT-002: 2HS101 = 'COMMUNICATION SKILLS' in syllabus but 'CALCULUS' in catalog 2017-2018 prog 205
- DQ-CONFLICT-003: 2HS101 = 'COMMUNICATION SKILLS' in syllabus but 'CALCULUS' in catalog 2019-2020 prog 215
- DQ-CONFLICT-004: 2HS101 = 'COMMUNICATION SKILLS' in syllabus but 'CALCULUS' in catalog 2020-2021 prog 215
- DQ-CONFLICT-005: 2HS102 = 'SEMINAR' in syllabus but 'LINEAR ALGEBRA' in catalog 2017-2018 prog 201
- DQ-CONFLICT-006: 2HS102 = 'SEMINAR' in syllabus but 'LINEAR ALGEBRA' in catalog 2017-2018 prog 205
- DQ-CONFLICT-007: 2HS102 = 'SEMINAR' in syllabus but 'LINEAR ALGEBRA' in catalog 2019-2020 prog 215
- DQ-CONFLICT-008: 2HS102 = 'SEMINAR' in syllabus but 'LINEAR ALGEBRA' in catalog 2020-2021 prog 215
- DQ-CONFLICT-009: 3OS201 = 'OPEN SUBJECT' in syllabus but 'ENGLISH LANGUAGE & COMMUNICATION SKILLS' in catalog 2017-2018 prog 401
- DQ-CONFLICT-010: 3OS201 = 'OPEN SUBJECT' in syllabus but 'ENGLISH LANGUAGE & COMMUNICATION SKILLS' in catalog 2018-2019 prog 401

## Informational

- Department courses with practical credits but no lab (by design): COURSE-2CEIT504, COURSE-2CEIT5PE7, COURSE-2CEIT605, COURSE-2CEIT703, COURSE-2CEIT704, COURSE-2CEIT801, COURSE-3CEIT104, COURSE-3CEIT301, COURSE-3CEIT302, COURSE-3CEIT401. Project, seminar, soft-skill, training and entrepreneurship courses deliberately use facilities (FCL-IT-002/007/001) rather than a lab.
