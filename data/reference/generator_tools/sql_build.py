"""Generate PostgreSQL schema + seed from the canonical structured data."""
import json

ST = "source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic'))"
SCHEMA = f"""-- CampusMate canonical relational schema (PostgreSQL 14+)
-- Every row carries source_type; the full canonical JSON record is kept in `record` for lossless round-trips.
BEGIN;
CREATE TABLE documents (
  document_id TEXT PRIMARY KEY, filename TEXT NOT NULL, path TEXT NOT NULL, document_type TEXT NOT NULL, title TEXT,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','synthetic')), is_synthetic BOOLEAN NOT NULL,
  academic_year TEXT, version TEXT, file_hash TEXT, page_count INT, created_at TEXT,
  effective_from TEXT, effective_to TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','superseded','deleted')),
  department_id TEXT, record JSONB NOT NULL);
CREATE TABLE university (university_id TEXT PRIMARY KEY, name TEXT NOT NULL, {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE org_units (org_unit_id TEXT PRIMARY KEY, unit_type TEXT, name TEXT NOT NULL, parent_id TEXT, {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE departments (department_id TEXT PRIMARY KEY, department_name TEXT NOT NULL UNIQUE, short_name TEXT,
  parent_org_unit_id TEXT REFERENCES org_units, university_id TEXT REFERENCES university, head_faculty_id TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE research_areas (research_area_id TEXT PRIMARY KEY, name TEXT NOT NULL, department_id TEXT REFERENCES departments, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE buildings (building_id TEXT PRIMARY KEY, name TEXT NOT NULL, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE rooms (room_id TEXT PRIMARY KEY, room_number TEXT NOT NULL, building_id TEXT NOT NULL REFERENCES buildings, floor INT, room_type TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE programs (program_id TEXT PRIMARY KEY, program_name TEXT NOT NULL, short_name TEXT UNIQUE, degree_type TEXT,
  department_id TEXT REFERENCES departments, org_unit_id TEXT REFERENCES org_units, number_of_semesters INT, total_credits NUMERIC,
  catalog_program_code TEXT, effective_year TEXT, {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE semesters (semester_id TEXT PRIMARY KEY, program_id TEXT NOT NULL REFERENCES programs, semester_number INT NOT NULL, semester_name TEXT NOT NULL,
  total_credits NUMERIC, total_marks INT, {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL,
  UNIQUE (program_id, semester_number));
CREATE TABLE courses (course_id TEXT PRIMARY KEY, course_code TEXT NOT NULL UNIQUE, course_name TEXT NOT NULL,
  program_id TEXT REFERENCES programs, semester_id TEXT REFERENCES semesters, course_type TEXT, credits NUMERIC,
  curriculum_status TEXT, department_id TEXT REFERENCES departments, prerequisites TEXT, description TEXT,
  synthetic_description TEXT, {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE elective_groups (elective_group_id TEXT PRIMARY KEY, group_name TEXT, slot_kind TEXT, program_id TEXT REFERENCES programs,
  semester_id TEXT REFERENCES semesters, credits NUMERIC, {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE elective_group_options (elective_group_id TEXT REFERENCES elective_groups, course_id TEXT REFERENCES courses, PRIMARY KEY (elective_group_id, course_id));
CREATE TABLE course_offerings (offering_id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses, program_id TEXT NOT NULL REFERENCES programs,
  semester_id TEXT NOT NULL REFERENCES semesters, course_type TEXT, elective_group_id TEXT REFERENCES elective_groups,
  credit_th NUMERIC, credit_pr NUMERIC, credits NUMERIC, contact_hours NUMERIC, total_marks INT,
  {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE catalog_listings (course_id TEXT REFERENCES courses, academic_year TEXT, catalog_program_code TEXT, catalog_program_name TEXT,
  listed_course_name TEXT, source_document TEXT REFERENCES documents, source_page INT, {ST}, PRIMARY KEY (course_id, academic_year, catalog_program_code));
CREATE TABLE grading_scheme (grade_band_id TEXT PRIMARY KEY, marks_range TEXT, grade_regular TEXT, grade_point_regular INT, grade_remedial TEXT, grade_point_remedial INT,
  {ST}, source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE faculty (faculty_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT, department_id TEXT NOT NULL REFERENCES departments,
  qualification TEXT, specialization TEXT, email TEXT UNIQUE, office_id TEXT REFERENCES rooms, joining_year INT, is_hod BOOLEAN,
  {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
ALTER TABLE departments ADD CONSTRAINT fk_hod FOREIGN KEY (head_faculty_id) REFERENCES faculty DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE faculty_research_areas (faculty_id TEXT REFERENCES faculty, research_area_id TEXT REFERENCES research_areas, PRIMARY KEY (faculty_id, research_area_id));
CREATE TABLE teaching_assignments (assignment_id TEXT PRIMARY KEY, faculty_id TEXT NOT NULL REFERENCES faculty, course_id TEXT NOT NULL REFERENCES courses,
  semester_id TEXT REFERENCES semesters, role TEXT, academic_year TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE laboratories (lab_id TEXT PRIMARY KEY, lab_name TEXT NOT NULL UNIQUE, department_id TEXT NOT NULL REFERENCES departments, room_id TEXT REFERENCES rooms,
  capacity INT, responsible_faculty_id TEXT REFERENCES faculty, opening_hours TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE lab_courses (lab_id TEXT REFERENCES laboratories, course_id TEXT REFERENCES courses, PRIMARY KEY (lab_id, course_id));
CREATE TABLE facilities (facility_id TEXT PRIMARY KEY, facility_name TEXT NOT NULL UNIQUE, facility_type TEXT, department_id TEXT NOT NULL REFERENCES departments,
  room_id TEXT REFERENCES rooms, capacity INT, availability TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE course_prerequisites (prerequisite_id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses, requires_course_id TEXT NOT NULL REFERENCES courses,
  strength TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL, CHECK (course_id <> requires_course_id));
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, policy_number TEXT UNIQUE, title TEXT NOT NULL, category TEXT, owner_faculty_id TEXT REFERENCES faculty,
  effective_from DATE, effective_to DATE, version TEXT, status TEXT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE policy_links (policy_id TEXT REFERENCES policies, link_type TEXT, target_id TEXT, PRIMARY KEY (policy_id, link_type, target_id));
CREATE TABLE academic_calendar (event_id TEXT PRIMARY KEY, title TEXT NOT NULL, event_type TEXT, start_date DATE NOT NULL, end_date DATE NOT NULL,
  term TEXT, department_id TEXT REFERENCES departments, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL, CHECK (end_date >= start_date));
CREATE TABLE notices (notice_id TEXT PRIMARY KEY, title TEXT NOT NULL, notice_date DATE NOT NULL, department_id TEXT NOT NULL REFERENCES departments,
  category TEXT, effective_date DATE, expiry_date DATE, status TEXT, supersedes TEXT REFERENCES notices, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE notice_links (notice_id TEXT REFERENCES notices, target_id TEXT, PRIMARY KEY (notice_id, target_id));
CREATE TABLE faq (faq_id TEXT PRIMARY KEY, category TEXT, question TEXT NOT NULL, answer TEXT NOT NULL, department_id TEXT REFERENCES departments,
  {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE faq_links (faq_id TEXT REFERENCES faq, target_id TEXT, PRIMARY KEY (faq_id, target_id));
CREATE TABLE data_quality_conflicts (conflict_id TEXT PRIMARY KEY, course_code TEXT, syllabus_course_name TEXT, catalog_course_name TEXT,
  academic_year TEXT, catalog_program_code TEXT, source_page INT, {ST}, source_document TEXT REFERENCES documents, record JSONB NOT NULL);
-- generic graph edge table (mirrors synthetic/structured/relationships.json)
CREATE TABLE relationships (relationship_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, predicate TEXT NOT NULL, object_id TEXT NOT NULL,
  {ST}, source_document TEXT REFERENCES documents, source_page INT);
CREATE INDEX ON relationships (subject_id, predicate); CREATE INDEX ON relationships (object_id, predicate);
-- entity <-> document mapping used by admin replace/delete/re-index workflows
CREATE TABLE document_entities (document_id TEXT REFERENCES documents ON DELETE CASCADE, entity_id TEXT NOT NULL, pdf_page INT, PRIMARY KEY (document_id, entity_id));
-- RAG chunk store (filled by the ingestion pipeline; embeddings live in ChromaDB or pgvector)
CREATE TABLE document_chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents ON DELETE CASCADE, page INT,
  section TEXT, entity_ids TEXT[], source_type TEXT, academic_year TEXT, text TEXT NOT NULL, tsv tsvector,
  embedding_ref TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX ON document_chunks USING GIN (tsv);
COMMIT;
"""

def q(v):
    if v is None: return "NULL"
    if isinstance(v, bool): return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, (dict, list)): v = json.dumps(v, ensure_ascii=False)
    return "'" + str(v).replace("'", "''") + "'"

def ins(table, row):
    return f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(q(v) for v in row.values())});"

def seed(T, R, REG, EIDX):
    L = ["BEGIN;", "SET CONSTRAINTS ALL DEFERRED;"]
    for d in REG:
        L.append(ins("documents", dict(document_id=d['document_id'], filename=d['filename'], path=d['path'], document_type=d['document_type'], title=d['title'],
            source_type=d['source_type'], is_synthetic=d['is_synthetic'], academic_year=d['academic_year'], version=d['version'], file_hash=d['file_hash'],
            page_count=d['page_count'], created_at=d['created_at'], effective_from=d['effective_from'], effective_to=d['effective_to'], status=d['status'],
            department_id=d['department_id'], record=d)))
    base = lambda r: dict(source_type=r['source_type'], source_document=r.get('source_document'))
    for r in T['university']: L.append(ins("university", dict(university_id=r['university_id'], name=r['name'], **base(r), source_page=r['source_page'], record=r)))
    for r in T['org_units']: L.append(ins("org_units", dict(org_unit_id=r['org_unit_id'], unit_type=r['unit_type'], name=r['name'], parent_id=r['parent_id'], **base(r), source_page=r['source_page'], record=r)))
    for r in T['departments']: L.append(ins("departments", dict(department_id=r['department_id'], department_name=r['department_name'], short_name=r['short_name'], parent_org_unit_id=r['parent_org_unit_id'], university_id=r['university_id'], head_faculty_id=r['head_faculty_id'], **base(r), record=r)))
    for r in T['research_areas']: L.append(ins("research_areas", dict(research_area_id=r['research_area_id'], name=r['name'], department_id=r['department_id'], **base(r), record=r)))
    for r in T['buildings']: L.append(ins("buildings", dict(building_id=r['building_id'], name=r['name'], **base(r), record=r)))
    for r in T['rooms']: L.append(ins("rooms", dict(room_id=r['room_id'], room_number=r['room_number'], building_id=r['building_id'], floor=r['floor'], room_type=r['room_type'], **base(r), record=r)))
    for r in T['programs']: L.append(ins("programs", dict(program_id=r['program_id'], program_name=r['program_name'], short_name=r['short_name'], degree_type=r['degree_type'], department_id=r['department_id'], org_unit_id=r['org_unit_id'], number_of_semesters=r['number_of_semesters'], total_credits=r['total_credits'], catalog_program_code=r['catalog_program_code'], effective_year=r['effective_year'], **base(r), source_page=r['source_page'], record=r)))
    for r in T['semesters']: L.append(ins("semesters", dict(semester_id=r['semester_id'], program_id=r['program_id'], semester_number=r['semester_number'], semester_name=r['semester_name'], total_credits=r['total_credits'], total_marks=r['total_marks'], **base(r), source_page=r['source_page'], record=r)))
    for r in T['courses']: L.append(ins("courses", dict(course_id=r['course_id'], course_code=r['course_code'], course_name=r['course_name'], program_id=r['program_id'], semester_id=r['semester_id'], course_type=r['course_type'], credits=r['credits'], curriculum_status=r['curriculum_status'], department_id=r['department_id'], prerequisites=r['prerequisites'], description=r['description'], synthetic_description=r['synthetic_description'], **base(r), source_page=r['source_page'], record=r)))
    for r in T['elective_groups']:
        L.append(ins("elective_groups", dict(elective_group_id=r['elective_group_id'], group_name=r['group_name'], slot_kind=r['slot_kind'], program_id=r['program_id'], semester_id=r['semester_id'], credits=r['slot_scheme']['credit_total'], **base(r), source_page=r['source_page'], record=r)))
        for c in r['option_course_ids']: L.append(ins("elective_group_options", dict(elective_group_id=r['elective_group_id'], course_id=c)))
    for r in T['course_offerings']:
        k = r['credit_scheme']
        L.append(ins("course_offerings", dict(offering_id=r['offering_id'], course_id=r['course_id'], program_id=r['program_id'], semester_id=r['semester_id'], course_type=r['course_type'], elective_group_id=r['elective_group_id'], credit_th=k['credit_th'], credit_pr=k['credit_pr'], credits=k['credit_total'], contact_hours=k['contact_hours'], total_marks=k['total_marks'], **base(r), source_page=r['source_page'], record=r)))
    for c in T['courses']:
        for x in c['catalog_listings']:
            L.append(ins("catalog_listings", dict(course_id=c['course_id'], academic_year=x['academic_year'], catalog_program_code=x['catalog_program_code'], catalog_program_name=x['catalog_program_name'], listed_course_name=x['listed_course_name'], source_document=x['source_document'], source_page=x['source_page'], source_type="official")))
    for r in T['grading_scheme']: L.append(ins("grading_scheme", dict(grade_band_id=r['grade_band_id'], marks_range=r['marks_range'], grade_regular=r['grade_regular'], grade_point_regular=r['grade_point_regular'], grade_remedial=r['grade_remedial'], grade_point_remedial=r['grade_point_remedial'], **base(r), source_page=r['source_page'], record=r)))
    for r in T['faculty']:
        L.append(ins("faculty", dict(faculty_id=r['faculty_id'], name=r['name'], designation=r['designation'], department_id=r['department_id'], qualification=r['qualification'], specialization=r['specialization'], email=r['email'], office_id=r['office_id'], joining_year=r['joining_year'], is_hod=r['is_hod'], **base(r), record=r)))
        for ra in r['research_area_ids']: L.append(ins("faculty_research_areas", dict(faculty_id=r['faculty_id'], research_area_id=ra)))
    for r in T['teaching_assignments']: L.append(ins("teaching_assignments", dict(assignment_id=r['assignment_id'], faculty_id=r['faculty_id'], course_id=r['course_id'], semester_id=r['semester_id'], role=r['role'], academic_year=r['academic_year'], **base(r), record=r)))
    for r in T['laboratories']:
        L.append(ins("laboratories", dict(lab_id=r['lab_id'], lab_name=r['lab_name'], department_id=r['department_id'], room_id=r['room_id'], capacity=r['capacity'], responsible_faculty_id=r['responsible_faculty_id'], opening_hours=r['opening_hours'], **base(r), record=r)))
        for c in r['related_courses']: L.append(ins("lab_courses", dict(lab_id=r['lab_id'], course_id=c)))
    for r in T['facilities']: L.append(ins("facilities", dict(facility_id=r['facility_id'], facility_name=r['facility_name'], facility_type=r['facility_type'], department_id=r['department_id'], room_id=r['room_id'], capacity=r['capacity'], availability=r['availability'], **base(r), record=r)))
    for r in T['course_prerequisites']: L.append(ins("course_prerequisites", dict(prerequisite_id=r['prerequisite_id'], course_id=r['course_id'], requires_course_id=r['requires_course_id'], strength=r['strength'], **base(r), record=r)))
    for r in T['policies']:
        L.append(ins("policies", dict(policy_id=r['policy_id'], policy_number=r['policy_number'], title=r['title'], category=r['category'], owner_faculty_id=r['owner_faculty_id'], effective_from=r['effective_from'], effective_to=r['effective_to'], version=r['version'], status=r['status'], **base(r), record=r)))
        for lt, k in [("department", "applies_to_department_ids"), ("program", "applies_to_program_ids"), ("course", "related_course_ids"), ("lab", "related_lab_ids"), ("facility", "related_facility_ids")]:
            for x in r[k]: L.append(ins("policy_links", dict(policy_id=r['policy_id'], link_type=lt, target_id=x)))
    for r in T['academic_calendar']: L.append(ins("academic_calendar", dict(event_id=r['event_id'], title=r['title'], event_type=r['event_type'], start_date=r['start_date'], end_date=r['end_date'], term=r['term'], department_id=r['department_id'], **base(r), record=r)))
    for r in sorted(T['notices'], key=lambda x: (x['supersedes'] is not None, x['notice_id'])):
        L.append(ins("notices", dict(notice_id=r['notice_id'], title=r['title'], notice_date=r['date'], department_id=r['department_id'], category=r['category'], effective_date=r['effective_date'], expiry_date=r['expiry_date'], status=r['status'], supersedes=r['supersedes'], **base(r), record=r)))
        for k in ('related_course_ids', 'related_faculty_ids', 'related_lab_ids', 'related_facility_ids', 'related_policy_ids', 'related_calendar_ids'):
            for x in r[k]: L.append(ins("notice_links", dict(notice_id=r['notice_id'], target_id=x)))
    for r in T['faq']:
        L.append(ins("faq", dict(faq_id=r['faq_id'], category=r['category'], question=r['question'], answer=r['answer'], department_id=r['department_id'], **base(r), record=r)))
        for x in r['related_entity_ids']: L.append(ins("faq_links", dict(faq_id=r['faq_id'], target_id=x)))
    for r in T['data_quality_conflicts']: L.append(ins("data_quality_conflicts", dict(conflict_id=r['conflict_id'], course_code=r['course_code'], syllabus_course_name=r['syllabus_course_name'], catalog_course_name=r['catalog_course_name'], academic_year=r['academic_year'], catalog_program_code=r['catalog_program_code'], source_page=r['source_page'], **base(r), record=r)))
    for r in R: L.append(ins("relationships", r))
    for d in REG:
        pages = d.get('entity_pages', {})
        for eid in dict.fromkeys(d['entity_ids']):
            L.append(ins("document_entities", dict(document_id=d['document_id'], entity_id=eid, pdf_page=pages.get(eid))))
    L.append("COMMIT;")
    return "\n".join(L) + "\n"
