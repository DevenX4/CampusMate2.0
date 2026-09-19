import { vi } from "vitest";

import type { ChatResponse, DocumentSummary, Me } from "../api/types";

type Reply = unknown | Response | ((init: RequestInit, url: string) => unknown);
export interface Call { url: string; init: RequestInit }

const PROVENANCE = { source_type: "official", document_id: "DOC-OFFICIAL-SYLLABUS-001", version_no: 1, page: 15, section: null };

// What the student workspace and the admin console load around every page.
export const CHROME: Record<string, Reply> = {
  "GET /api/v1/system/info": {
    version: "0.1.0", environment: "development", generation_provider: "extractive", generation_model: "extractive-v1 (no model)",
    embedding_model: "BAAI/bge-small-en-v1.5", vector_store: "Chroma (embedded)", vector_store_version: "1.5.9",
    reranker_model: "Xenova/ms-marco-MiniLM-L-12-v2", ingestion_in_api: true,
    limits: { login_max_failures: 5, login_window_minutes: 15, chat_questions_per_minute: 20, max_upload_mb: 50, session_ttl_hours: 12 },
  },
  "GET /api/v1/system/ready": { status: "ready" },
  "GET /api/v1/auth/demo": { enabled: true, accounts: [{ username: "admin", password: "admin@123", role: "admin" }, { username: "student", password: "student@123", role: "student" }] },
  "GET /api/v1/departments": [{ department_id: "DEPT-IT-001", department_name: "Department of Information Technology", short_name: "IT", status: "active" }],
  "GET /api/v1/programs": [{ program_id: "PROG-BTECH-IT-001", program_name: "Bachelor of Technology in Information Technology", short_name: "B.TECH-IT", degree_type: "UG", effective_year: "2021-2022", provenance: PROVENANCE }],
  "GET /api/v1/programs/PROG-BTECH-IT-001": {
    program_id: "PROG-BTECH-IT-001", program_name: "Bachelor of Technology in Information Technology", short_name: "B.TECH-IT", degree_type: "UG",
    effective_year: "2021-2022", provenance: PROVENANCE, department_id: "DEPT-IT-001", semester_count: 1, total_credits: 23,
    semesters: [{ semester_id: "SEM-BTECH-IT-06", semester_number: 6, semester_name: "Semester VI", total_credits: 23, provenance: PROVENANCE }],
  },
  "GET /api/v1/notices": [{ notice_id: "NOTICE-001", title: "Lab slot registration", notice_date: "2026-09-10", category: "labs", content: "Register by Friday.", is_current: true, provenance: { ...PROVENANCE, source_type: "synthetic" } }],
  "GET /api/v1/knowledge/sources": [
    { document_id: "DOC-OFFICIAL-SYLLABUS-001", title: "GUNI Structured Syllabus", document_type: "official_structured_syllabus", source_type: "official", version_no: 1, academic_year: null, chunks: 21 },
    { document_id: "DOC-LABS-001", title: "Laboratories", document_type: "laboratories", source_type: "synthetic", version_no: 1, academic_year: null, chunks: 40 },
  ],
  "GET /api/v1/chat/history": [],
};

// Replaces fetch with canned replies keyed by "METHOD /path" (query string ignored), on top of
// CHROME. Unknown routes answer 404 in the backend's error format.
export function mockApi(routes: Record<string, Reply>): Call[] {
  const all = { ...CHROME, ...routes };
  const calls: Call[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    const key = `${init.method ?? "GET"} ${url.split("?")[0]}`;
    if (!(key in all)) {
      return Response.json({ error: { code: "not_found", message: `no mock for ${key}` } }, { status: 404 });
    }
    const route = all[key];
    const result = typeof route === "function" ? (route as (init: RequestInit, url: string) => unknown)(init, url) : route;
    return result instanceof Response ? result : Response.json(result);
  }));
  return calls;
}

export const unauthorized = () => Response.json({ error: { code: "unauthorized", message: "Not authenticated" } }, { status: 401 });

export function me(role: string, username: string, permissions: string[]): Me {
  return {
    user: { id: `u-${role}`, email: `${role}@campusmate-demo.example`, username, full_name: null, role, is_active: true, is_demo: true,
            created_at: "2026-09-19T00:00:00Z", last_login_at: null },
    permissions,
  };
}

export const STUDENT = me("student", "student", ["catalog:read", "chat:use"]);
export const ADMIN = me("admin", "admin", ["audit:read", "catalog:read", "chat:use", "documents:manage", "documents:read",
                                           "ingestion:manage", "users:manage"]);

export const SEMESTER_ANSWER: ChatResponse = {
  query_id: "q-1",
  question: "What courses are offered in Semester VI of B.Tech IT?",
  answer: "B.TECH-IT Semester VI (23 credits in total): regular courses: 2CEIT602 ARTIFICIAL INTELLIGENCE (4 cr) [1].",
  answer_type: "answered",
  contains_synthetic: false,
  route: "structured",
  intents: ["semester_courses", "documents"],
  reasons: ["courses of SEM-BTECH-IT-06: offerings table", "supporting passages: hybrid retrieval"],
  tables: [{ ref: 1, title: "B.TECH-IT Semester VI · 23 credits in total", columns: ["Course code", "Course title", "Credits", "Classification"],
             rows: [["2CEIT602", "ARTIFICIAL INTELLIGENCE", "4", "regular"]] }],
  sources: [
    { ref: 1, kind: "structured", source_type: "official", cited: true, label: "DOC-OFFICIAL-SYLLABUS-001, p.15",
      text: "B.TECH-IT Semester VI (23 credits in total): regular courses: 2CEIT602 ARTIFICIAL INTELLIGENCE (4 cr)",
      entity_ids: ["SEM-BTECH-IT-06", "COURSE-2CEIT602"],
      citation: { document_id: "DOC-OFFICIAL-SYLLABUS-001", version_no: 1, title: "B.TECH-IT Semester VI", document_type: "structured_record",
                  page_start: 15, page_end: 15, section: null } },
    { ref: 2, kind: "document", source_type: "synthetic", cited: false, label: "DOC-LABS-001, p.2", text: "LAB-IT-001 AI & Machine Learning Lab",
      entity_ids: ["LAB-IT-001"],
      citation: { document_id: "DOC-LABS-001", version_no: 1, title: "Laboratories", document_type: "laboratories", page_start: 2, page_end: 2, section: null } },
  ],
  grounding: { passed: true, issues: [], warnings: [] },
  provider: "extractive",
  model: "extractive-v1",
  timings_ms: { routing: 12, evidence: 30, generation: 1, grounding: 1, total: 44 },
};

export function document(overrides: Partial<DocumentSummary>): DocumentSummary {
  return {
    document_id: "DOC-OFFICIAL-SYLLABUS-001", title: "GUNI Structured Syllabus", document_type: "official_structured_syllabus",
    source_type: "official", department_id: "DEPT-IT-001", status: "active", created_at: "2026-09-19T00:00:00Z",
    updated_at: "2026-09-19T00:00:00Z", latest_version_no: 1, chunk_count: 21,
    active_version: { version_no: 1, status: "active", sha256: "a".repeat(64), notes: null, original_filename: "syllabus.pdf",
                      size_bytes: 38_000_000, page_count: 742, version_label: null, academic_year: "2021-2022",
                      created_at: "2026-09-18T00:00:00Z", activated_at: "2026-09-18T00:00:00Z" },
    ...overrides,
  };
}
