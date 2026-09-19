// Shapes of the FastAPI responses the UI uses (see backend/app/schemas). The UI displays what
// the API returns and never adds facts of its own.

export type SourceType = "official" | "derived_official" | "synthetic";

export interface Provenance {
  source_type: SourceType;
  document_id: string;
  version_no: number;
  page: number | null;
  section: string | null;
}

// --- accounts ---------------------------------------------------------------------------------

export interface User {
  id: string;
  email: string;
  username: string | null;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Me {
  user: User;
  permissions: string[];
}

export interface DemoAccounts {
  enabled: boolean;
  accounts: { username: string; password: string; role: string }[];
}

export interface SystemInfo {
  version: string;
  environment: string;
  generation_provider: string;
  generation_model: string;
  embedding_model: string;
  vector_store: string;
  vector_store_version: string;
  reranker_model: string;
  ingestion_in_api: boolean;
  limits: Record<string, number>;
}

// --- chat -------------------------------------------------------------------------------------

export interface Citation {
  document_id: string;
  version_no: number;
  title: string;
  document_type: string;
  page_start: number | null;
  page_end: number | null;
  section: string | null;
}

export interface Source {
  ref: number;
  kind: "structured" | "graph" | "document";
  source_type: SourceType;
  cited: boolean;
  label: string;
  text: string;
  citation: Citation;
  entity_ids: string[];
}

export interface AnswerTable {
  ref: number;
  title: string;
  columns: string[];
  rows: string[][];
}

export type AnswerType = "answered" | "fallback" | "abstained" | "unsupported";

export interface ChatResponse {
  query_id: string;
  question: string;
  answer: string;
  answer_type: AnswerType;
  contains_synthetic: boolean;
  route: string;
  intents: string[];
  reasons: string[];
  tables: AnswerTable[];
  sources: Source[];
  grounding: { passed: boolean; issues: string[]; warnings: string[] };
  provider: string;
  model: string;
  timings_ms: Record<string, number>;
}

export type Rating = "up" | "down";

export interface Feedback {
  query_id: string;
  rating: Rating;
  comment: string | null;
}

export interface HistoryItem {
  query_id: string;
  question: string;
  answer_type: AnswerType;
  created_at: string;
}

export interface ChatAnalytics {
  total_questions: number;
  last_7_days: { day: string; questions: number }[];
  by_answer_type: Record<string, number>;
  by_route: Record<string, number>;
  feedback_up: number;
  feedback_down: number;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  unanswered: { question: string; created_at: string }[];
  downvoted: { question: string; created_at: string; comment: string | null }[];
}

// --- knowledge graph ---------------------------------------------------------------------------

export interface KnowledgeItem {
  id: string;
  type: string;
  title: string;
  source_type: SourceType;
  provenance: Provenance;
  attributes: Record<string, unknown>;
  attribute_source_types: Record<string, SourceType>;
  relationships: Record<string, { id: string; source_type: SourceType; type: string | null; title: string | null }[]>;
}

export interface KnowledgeSource {
  document_id: string;
  title: string;
  document_type: string;
  source_type: SourceType;
  version_no: number;
  academic_year: string | null;
  chunks: number;
}

// --- catalog ----------------------------------------------------------------------------------

export interface Department {
  department_id: string;
  department_name: string;
  short_name: string | null;
  status: string;
}

export interface Credits {
  theory: number | null;
  practical: number | null;
  total: number | null;
  contact_hours: number | null;
}

export interface CourseRef {
  course_id: string;
  course_code: string;
  course_name: string;
  source_type: SourceType;
}

export interface SemesterSummary {
  semester_id: string;
  semester_number: number;
  semester_name: string;
  total_credits: number | null;
  provenance: Provenance;
}

export interface ProgramSummary {
  program_id: string;
  program_name: string;
  short_name: string;
  degree_type: string | null;
  effective_year: string | null;
  provenance: Provenance;
}

export interface ProgramDetail extends ProgramSummary {
  department_id: string | null;
  semesters: SemesterSummary[];
  semester_count: number;
  total_credits: number;
}

export interface SemesterDetail extends SemesterSummary {
  program: { program_id: string; short_name: string };
  total_course: number | null;
  total_marks: number | null;
  effective_year: string | null;
  regular_courses: { offering_id: string; course: CourseRef; course_type: string; credits: Credits;
                     marks: { total: number | null }; provenance: Provenance }[];
  elective_slots: { elective_group_id: string; group_name: string; slot_kind: string; credits: Credits;
                    options: CourseRef[]; provenance: Provenance }[];
}

export interface CourseDetail {
  course_id: string;
  course_code: string;
  course_name: string;
  curriculum_status: string;
  synthetic_description: string | null;
  provenance: Provenance;
  offerings: { offering_id: string; program: { short_name: string }; semester: { semester_id: string; semester_name: string };
               course_type: string; elective_group_id: string | null; credits: Credits; marks: { total: number | null };
               provenance: Provenance }[];
  taught_by: { faculty: { faculty_id: string; name: string; designation: string | null; source_type: SourceType };
               semester_id: string; role: string; provenance: Provenance }[];
  labs: { lab_id: string; lab_name: string; source_type: SourceType }[];
  prerequisites: { course: CourseRef; strength: string; provenance: Provenance }[];
  catalog_listings: { academic_year: string; catalog_program_code: string; listed_course_name: string; provenance: Provenance }[];
}

export interface FacultySummary {
  faculty_id: string;
  name: string;
  designation: string | null;
  department_id: string;
  email: string | null;
  status: string;
  provenance: Provenance;
}

export interface FacultyDetail extends FacultySummary {
  qualification: string | null;
  specialization: string | null;
  office_room: { room_number: string } | null;
  consultation_hours: string | null;
  research_areas: string[];
  is_head_of_department: boolean;
  teaching: { course: CourseRef; semester_id: string; role: string }[];
}

export interface Policy {
  policy_id: string;
  policy_number: string;
  title: string;
  category: string | null;
  summary: string | null;
  clauses: string[] | null;
  effective_from: string | null;
  effective_to: string | null;
  status: string;
  academic_year: string | null;
  provenance: Provenance;
}

export interface Notice {
  notice_id: string;
  title: string;
  notice_date: string;
  category: string | null;
  content: string;
  is_current: boolean;
  provenance: Provenance;
}

export interface CalendarEvent {
  event_id: string;
  title: string;
  event_type: string | null;
  start_date: string;
  end_date: string;
  term: string | null;
  academic_year: string | null;
  semester_ids: string[];
  provenance: Provenance;
}

// --- documents & ingestion ------------------------------------------------------------------------

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export type VersionStatus = "pending" | "ready" | "active" | "superseded" | "failed";

export interface Version {
  version_no: number;
  status: VersionStatus;
  sha256: string;
  notes: string | null;
  original_filename: string;
  size_bytes: number;
  page_count: number | null;
  version_label: string | null;
  academic_year: string | null;
  created_at: string;
  activated_at: string | null;
}

export type DocumentStatus = "active" | "inactive" | "archived" | "deleted";

export interface DocumentSummary {
  document_id: string;
  title: string;
  document_type: string;
  source_type: "official" | "synthetic";
  department_id: string | null;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  active_version: Version | null;
  latest_version_no: number | null;
  chunk_count: number;
}

export interface JobSummary {
  id: string;
  version_no: number;
  job_type: string;
  status: JobStatus;
  current_stage: string | null;
  attempts: number;
  error_message: string | null;
  chunk_count: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface DocumentDetail extends DocumentSummary {
  versions: Version[];
  recent_jobs: JobSummary[];
  entity_count: number;
}

export interface DocumentStats {
  active_documents: number;
  total_documents: number;
  total_chunks: number;
  pending_jobs: number;
  failed_jobs: number;
  last_updated: string | null;
}

export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface IngestionJob extends JobSummary {
  document_id: string;
  stage_timings: Record<string, number>;
  started_at: string | null;
}

// The document types the backend accepts for uploads (DocumentType in schemas/documents.py),
// grouped the way the knowledge base page filters them.
export const DOCUMENT_CATEGORIES: { label: string; types: string[] }[] = [
  { label: "Syllabus", types: ["official_structured_syllabus", "syllabus", "official_certified_course_list", "course_catalog", "programs_and_curriculum"] },
  { label: "Regulations", types: ["policies", "examination", "handbook"] },
  { label: "Notices", types: ["notices", "academic_calendar", "student_services_faq"] },
  { label: "Faculty", types: ["faculty_directory"] },
  { label: "Department", types: ["department_profile", "laboratories", "facilities"] },
  { label: "Others", types: ["other"] },
];

export const DOCUMENT_TYPES = DOCUMENT_CATEGORIES.flatMap((c) => c.types);

export const categoryOf = (documentType: string) =>
  DOCUMENT_CATEGORIES.find((c) => c.types.includes(documentType))?.label ?? "Others";
