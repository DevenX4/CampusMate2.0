-- CampusMate canonical relational schema (PostgreSQL 14+)
-- Every row carries source_type; the full canonical JSON record is kept in `record` for lossless round-trips.
BEGIN;
CREATE TABLE documents (
  document_id TEXT PRIMARY KEY, filename TEXT NOT NULL, path TEXT NOT NULL, document_type TEXT NOT NULL, title TEXT,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','synthetic')), is_synthetic BOOLEAN NOT NULL,
  academic_year TEXT, version TEXT, file_hash TEXT, page_count INT, created_at TEXT,
  effective_from TEXT, effective_to TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','superseded','deleted')),
  department_id TEXT, record JSONB NOT NULL);
CREATE TABLE university (university_id TEXT PRIMARY KEY, name TEXT NOT NULL, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE org_units (org_unit_id TEXT PRIMARY KEY, unit_type TEXT, name TEXT NOT NULL, parent_id TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE departments (department_id TEXT PRIMARY KEY, department_name TEXT NOT NULL UNIQUE, short_name TEXT,
  parent_org_unit_id TEXT REFERENCES org_units, university_id TEXT REFERENCES university, head_faculty_id TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE research_areas (research_area_id TEXT PRIMARY KEY, name TEXT NOT NULL, department_id TEXT REFERENCES departments, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE buildings (building_id TEXT PRIMARY KEY, name TEXT NOT NULL, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE rooms (room_id TEXT PRIMARY KEY, room_number TEXT NOT NULL, building_id TEXT NOT NULL REFERENCES buildings, floor INT, room_type TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE programs (program_id TEXT PRIMARY KEY, program_name TEXT NOT NULL, short_name TEXT UNIQUE, degree_type TEXT,
  department_id TEXT REFERENCES departments, org_unit_id TEXT REFERENCES org_units, number_of_semesters INT, total_credits NUMERIC,
  catalog_program_code TEXT, effective_year TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE semesters (semester_id TEXT PRIMARY KEY, program_id TEXT NOT NULL REFERENCES programs, semester_number INT NOT NULL, semester_name TEXT NOT NULL,
  total_credits NUMERIC, total_marks INT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL,
  UNIQUE (program_id, semester_number));
CREATE TABLE courses (course_id TEXT PRIMARY KEY, course_code TEXT NOT NULL UNIQUE, course_name TEXT NOT NULL,
  program_id TEXT REFERENCES programs, semester_id TEXT REFERENCES semesters, course_type TEXT, credits NUMERIC,
  curriculum_status TEXT, department_id TEXT REFERENCES departments, prerequisites TEXT, description TEXT,
  synthetic_description TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE elective_groups (elective_group_id TEXT PRIMARY KEY, group_name TEXT, slot_kind TEXT, program_id TEXT REFERENCES programs,
  semester_id TEXT REFERENCES semesters, credits NUMERIC, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE elective_group_options (elective_group_id TEXT REFERENCES elective_groups, course_id TEXT REFERENCES courses, PRIMARY KEY (elective_group_id, course_id));
CREATE TABLE course_offerings (offering_id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses, program_id TEXT NOT NULL REFERENCES programs,
  semester_id TEXT NOT NULL REFERENCES semesters, course_type TEXT, elective_group_id TEXT REFERENCES elective_groups,
  credit_th NUMERIC, credit_pr NUMERIC, credits NUMERIC, contact_hours NUMERIC, total_marks INT,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE catalog_listings (course_id TEXT REFERENCES courses, academic_year TEXT, catalog_program_code TEXT, catalog_program_name TEXT,
  listed_course_name TEXT, source_document TEXT REFERENCES documents, source_page INT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), PRIMARY KEY (course_id, academic_year, catalog_program_code));
CREATE TABLE grading_scheme (grade_band_id TEXT PRIMARY KEY, marks_range TEXT, grade_regular TEXT, grade_point_regular INT, grade_remedial TEXT, grade_point_remedial INT,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT, record JSONB NOT NULL);
CREATE TABLE faculty (faculty_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT, department_id TEXT NOT NULL REFERENCES departments,
  qualification TEXT, specialization TEXT, email TEXT UNIQUE, office_id TEXT REFERENCES rooms, joining_year INT, is_hod BOOLEAN,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
ALTER TABLE departments ADD CONSTRAINT fk_hod FOREIGN KEY (head_faculty_id) REFERENCES faculty DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE faculty_research_areas (faculty_id TEXT REFERENCES faculty, research_area_id TEXT REFERENCES research_areas, PRIMARY KEY (faculty_id, research_area_id));
CREATE TABLE teaching_assignments (assignment_id TEXT PRIMARY KEY, faculty_id TEXT NOT NULL REFERENCES faculty, course_id TEXT NOT NULL REFERENCES courses,
  semester_id TEXT REFERENCES semesters, role TEXT, academic_year TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE laboratories (lab_id TEXT PRIMARY KEY, lab_name TEXT NOT NULL UNIQUE, department_id TEXT NOT NULL REFERENCES departments, room_id TEXT REFERENCES rooms,
  capacity INT, responsible_faculty_id TEXT REFERENCES faculty, opening_hours TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE lab_courses (lab_id TEXT REFERENCES laboratories, course_id TEXT REFERENCES courses, PRIMARY KEY (lab_id, course_id));
CREATE TABLE facilities (facility_id TEXT PRIMARY KEY, facility_name TEXT NOT NULL UNIQUE, facility_type TEXT, department_id TEXT NOT NULL REFERENCES departments,
  room_id TEXT REFERENCES rooms, capacity INT, availability TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE course_prerequisites (prerequisite_id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses, requires_course_id TEXT NOT NULL REFERENCES courses,
  strength TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL, CHECK (course_id <> requires_course_id));
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, policy_number TEXT UNIQUE, title TEXT NOT NULL, category TEXT, owner_faculty_id TEXT REFERENCES faculty,
  effective_from DATE, effective_to DATE, version TEXT, status TEXT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE policy_links (policy_id TEXT REFERENCES policies, link_type TEXT, target_id TEXT, PRIMARY KEY (policy_id, link_type, target_id));
CREATE TABLE academic_calendar (event_id TEXT PRIMARY KEY, title TEXT NOT NULL, event_type TEXT, start_date DATE NOT NULL, end_date DATE NOT NULL,
  term TEXT, department_id TEXT REFERENCES departments, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL, CHECK (end_date >= start_date));
CREATE TABLE notices (notice_id TEXT PRIMARY KEY, title TEXT NOT NULL, notice_date DATE NOT NULL, department_id TEXT NOT NULL REFERENCES departments,
  category TEXT, effective_date DATE, expiry_date DATE, status TEXT, supersedes TEXT REFERENCES notices, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE notice_links (notice_id TEXT REFERENCES notices, target_id TEXT, PRIMARY KEY (notice_id, target_id));
CREATE TABLE faq (faq_id TEXT PRIMARY KEY, category TEXT, question TEXT NOT NULL, answer TEXT NOT NULL, department_id TEXT REFERENCES departments,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
CREATE TABLE faq_links (faq_id TEXT REFERENCES faq, target_id TEXT, PRIMARY KEY (faq_id, target_id));
CREATE TABLE data_quality_conflicts (conflict_id TEXT PRIMARY KEY, course_code TEXT, syllabus_course_name TEXT, catalog_course_name TEXT,
  academic_year TEXT, catalog_program_code TEXT, source_page INT, source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, record JSONB NOT NULL);
-- generic graph edge table (mirrors synthetic/structured/relationships.json)
CREATE TABLE relationships (relationship_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, predicate TEXT NOT NULL, object_id TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('official','derived_official','synthetic')), source_document TEXT REFERENCES documents, source_page INT);
CREATE INDEX ON relationships (subject_id, predicate); CREATE INDEX ON relationships (object_id, predicate);
-- entity <-> document mapping used by admin replace/delete/re-index workflows
CREATE TABLE document_entities (document_id TEXT REFERENCES documents ON DELETE CASCADE, entity_id TEXT NOT NULL, pdf_page INT, PRIMARY KEY (document_id, entity_id));
-- RAG chunk store (filled by the ingestion pipeline; embeddings live in ChromaDB or pgvector)
CREATE TABLE document_chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents ON DELETE CASCADE, page INT,
  section TEXT, entity_ids TEXT[], source_type TEXT, academic_year TEXT, text TEXT NOT NULL, tsv tsvector,
  embedding_ref TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX ON document_chunks USING GIN (tsv);
COMMIT;
