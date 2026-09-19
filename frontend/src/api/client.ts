// The only place the UI talks to the server. Everything goes to /api/v1 on the same origin,
// with the httpOnly session cookie; the UI never sees or stores the session token.

import type {
  ChatResponse, Department, DocumentDetail, DocumentStats, DocumentSummary, Feedback, IngestionJob, JobStatus, Me, Page,
  Rating,
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

export type DocumentAction = "activate" | "deactivate" | "archive" | "reindex";

export const api = {
  login: (email: string, password: string) => call<unknown>("/auth/login", post({ email, password })),
  logout: () => call<void>("/auth/logout", post()),
  me: () => call<Me>("/auth/me"),

  ask: (question: string) => call<ChatResponse>("/chat/query", post({ question })),
  feedback: (queryId: string, rating: Rating, comment?: string) =>
    call<Feedback>("/chat/feedback", post({ query_id: queryId, rating, comment: comment?.trim() || null })),

  documents: (params: { q?: string; document_type?: string; status?: string; limit?: number; offset?: number }) =>
    call<Page<DocumentSummary>>(`/documents${query(params)}`),
  documentStats: () => call<DocumentStats>("/documents/stats"),
  uploadDocument: (form: FormData) => call<DocumentSummary>("/documents", post(form)),
  documentAction: (documentId: string, action: DocumentAction) =>
    call<DocumentSummary>(`/documents/${encodeURIComponent(documentId)}/${action}`, post()),
  deleteDocument: (documentId: string) =>
    call<DocumentSummary>(`/documents/${encodeURIComponent(documentId)}`, { method: "DELETE" }),
  document: (documentId: string) => call<DocumentDetail>(`/documents/${encodeURIComponent(documentId)}`),
  uploadVersion: (documentId: string, form: FormData) =>
    call<DocumentDetail>(`/documents/${encodeURIComponent(documentId)}/versions`, post(form)),
  activateVersion: (documentId: string, versionNo: number) =>
    call<DocumentDetail>(`/documents/${encodeURIComponent(documentId)}/versions/${versionNo}/activate`, post()),
  // A plain link: the browser sends the session cookie itself (administrators only).
  versionFileUrl: (documentId: string, versionNo: number) =>
    `${BASE}/documents/${encodeURIComponent(documentId)}/versions/${versionNo}/file`,
  departments: () => call<Department[]>("/departments"),

  jobs: (params: { status?: JobStatus; limit?: number; offset?: number }) =>
    call<Page<IngestionJob>>(`/ingestion/jobs${query(params)}`),
  retryJob: (jobId: string) => call<IngestionJob>(`/ingestion/jobs/${encodeURIComponent(jobId)}/retry`, post()),
};
