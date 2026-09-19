// The only place the UI talks to the server. Everything goes to /api/v1 on the same origin,
// with the httpOnly session cookie; the UI never sees or stores the session token.

import type {
  CalendarEvent, ChatAnalytics, ChatResponse, CourseDetail, DemoAccounts, Department, DocumentDetail, DocumentStats,
  DocumentSummary, FacultyDetail, FacultySummary, Feedback, HistoryItem, IngestionJob, JobStatus, KnowledgeItem,
  KnowledgeSource, Me, Notice, Page, Policy, ProgramDetail, ProgramSummary, Rating, SemesterDetail, SystemInfo, User,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(BASE + path, { ...init, headers, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "network", "The CampusMate server cannot be reached.");
  }
  if (response.status === 204) return undefined as T;
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    // The backend's error format: {"error": {"code", "message", "details"}}
    const error = (body as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(response.status, error?.code ?? "http_error",
                       error?.message ?? `The request failed (HTTP ${response.status}).`);
  }
  return body as T;
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

const post = (body?: unknown): RequestInit => ({
  method: "POST",
  body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
});

const id = encodeURIComponent;

export type DocumentAction = "activate" | "deactivate" | "archive" | "reindex";

export interface AskContext {
  program_id?: string;
  semester_id?: string;
}

export const api = {
  // accounts
  login: (username: string, password: string) => call<unknown>("/auth/login", post({ username, password })),
  logout: () => call<void>("/auth/logout", post()),
  me: () => call<Me>("/auth/me"),
  demoAccounts: () => call<DemoAccounts>("/auth/demo"),
  systemInfo: () => call<SystemInfo>("/system/info"),
  ready: () => call<{ status: string }>("/system/ready"),
  users: (params: { q?: string; role?: string; limit?: number; offset?: number }) => call<Page<User>>(`/users${query(params)}`),
  createUser: (body: { email: string; username?: string; full_name?: string; password: string; role: string }) =>
    call<User>("/users", post(body)),
  updateUser: (userId: string, body: { role?: string; is_active?: boolean; full_name?: string }) =>
    call<User>(`/users/${id(userId)}`, { method: "PATCH", body: JSON.stringify(body) }),

  // chat
  ask: (question: string, context: AskContext = {}) => call<ChatResponse>("/chat/query", post({ question, ...context })),
  feedback: (queryId: string, rating: Rating, comment?: string) =>
    call<Feedback>("/chat/feedback", post({ query_id: queryId, rating, comment: comment?.trim() || null })),
  history: (q?: string) => call<HistoryItem[]>(`/chat/history${query({ q, limit: 30 })}`),
  analytics: () => call<ChatAnalytics>("/chat/analytics"),

  // knowledge & catalog
  entity: (entityId: string) => call<KnowledgeItem>(`/knowledge/entities/${id(entityId)}`),
  sources: () => call<KnowledgeSource[]>("/knowledge/sources"),
  departments: () => call<Department[]>("/departments"),
  programs: () => call<ProgramSummary[]>("/programs"),
  program: (programId: string) => call<ProgramDetail>(`/programs/${id(programId)}`),
  semester: (semesterId: string) => call<SemesterDetail>(`/semesters/${id(semesterId)}`),
  faculty: (params: { q?: string; limit?: number }) => call<Page<FacultySummary>>(`/faculty${query(params)}`),
  facultyMember: (facultyId: string) => call<FacultyDetail>(`/faculty/${id(facultyId)}`),
  courses: (params: { q?: string; limit?: number }) => call<Page<{ course_id: string; course_code: string; course_name: string }>>(`/courses${query(params)}`),
  course: (courseId: string) => call<CourseDetail>(`/courses/${id(courseId)}`),
  policies: () => call<Policy[]>("/policies"),
  notices: (limit = 20) => call<Notice[]>(`/notices${query({ limit })}`),
  calendar: (semesterId?: string) => call<CalendarEvent[]>(`/calendar${query({ semester_id: semesterId })}`),

  // documents & ingestion
  documents: (params: { q?: string; document_type?: string; status?: string; limit?: number; offset?: number }) =>
    call<Page<DocumentSummary>>(`/documents${query(params)}`),
  documentStats: () => call<DocumentStats>("/documents/stats"),
  document: (documentId: string) => call<DocumentDetail>(`/documents/${id(documentId)}`),
  uploadDocument: (form: FormData) => call<DocumentSummary>("/documents", post(form)),
  uploadVersion: (documentId: string, form: FormData) => call<DocumentDetail>(`/documents/${id(documentId)}/versions`, post(form)),
  activateVersion: (documentId: string, versionNo: number) =>
    call<DocumentDetail>(`/documents/${id(documentId)}/versions/${versionNo}/activate`, post()),
  documentAction: (documentId: string, action: DocumentAction) => call<DocumentSummary>(`/documents/${id(documentId)}/${action}`, post()),
  deleteDocument: (documentId: string) => call<DocumentSummary>(`/documents/${id(documentId)}`, { method: "DELETE" }),
  // A plain link: the browser sends the session cookie itself (administrators only).
  versionFileUrl: (documentId: string, versionNo: number) => `${BASE}/documents/${id(documentId)}/versions/${versionNo}/file`,
  jobs: (params: { status?: JobStatus; limit?: number; offset?: number }) => call<Page<IngestionJob>>(`/ingestion/jobs${query(params)}`),
  retryJob: (jobId: string) => call<IngestionJob>(`/ingestion/jobs/${id(jobId)}/retry`, post()),
};
