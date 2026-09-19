// Shapes of the FastAPI responses the UI uses (see backend/app/schemas). The UI displays what
// the API returns and never adds facts of its own.

export type SourceType = "official" | "derived_official" | "synthetic";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Me {
  user: User;
  permissions: string[];
}

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

export interface IngestionJob {
  id: string;
  document_id: string;
  version_no: number;
  job_type: string;
  status: JobStatus;
  current_stage: string | null;
  attempts: number;
  chunk_count: number | null;
  error_message: string | null;
  stage_timings: Record<string, number>;
  created_at: string;
  finished_at: string | null;
}

export interface Department {
  department_id: string;
  department_name: string;
  short_name: string | null;
  status: string;
}

// The document types the backend accepts for uploads (DocumentType in schemas/documents.py).
export const DOCUMENT_TYPES = [
  "syllabus", "examination", "handbook", "policies", "notices", "academic_calendar", "faculty_directory",
  "course_catalog", "programs_and_curriculum", "laboratories", "facilities", "student_services_faq",
  "department_profile", "official_structured_syllabus", "official_certified_course_list", "other",
] as const;
