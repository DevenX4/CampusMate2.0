import { vi } from "vitest";

import type { ChatResponse, Me } from "../api/types";

type Reply = unknown | Response | ((init: RequestInit) => unknown);
export interface Call { url: string; init: RequestInit }

// Replaces fetch with canned replies keyed by "METHOD /path" (query string ignored). Unknown
// routes answer 404 in the backend's error format.
export function mockApi(routes: Record<string, Reply>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    const key = `${init.method ?? "GET"} ${url.split("?")[0]}`;
    if (!(key in routes)) {
      return Response.json({ error: { code: "not_found", message: `no mock for ${key}` } }, { status: 404 });
    }
    const route = routes[key];
    const result = typeof route === "function" ? (route as (init: RequestInit) => unknown)(init) : route;
    return result instanceof Response ? result : Response.json(result);
  }));
  return calls;
}

export const unauthorized = () => Response.json({ error: { code: "unauthorized", message: "Not authenticated" } }, { status: 401 });

export function me(role: string, permissions: string[]): Me {
  return {
    user: { id: "u-1", email: `${role}@campusmate-demo.example`, full_name: null, role, is_active: true,
            created_at: "2026-09-19T00:00:00Z", last_login_at: null },
    permissions,
  };
}

export const STUDENT = me("student", ["catalog:read", "chat:use"]);
export const ADMIN = me("admin", ["audit:read", "catalog:read", "chat:use", "documents:manage", "documents:read",
                                  "ingestion:manage", "users:manage"]);

export const LAB_ANSWER: ChatResponse = {
  query_id: "q-1",
  question: "Which lab hosts the AI practicals?",
  answer: "(Synthetic demo data) practicals_in: LAB-IT-001 (AI & Machine Learning Lab) [synthetic] [1]. Synthetic demo data is not official GUNI information.",
  answer_type: "answered",
  contains_synthetic: true,
  route: "graph",
  intents: ["entity_relations", "documents"],
  sources: [
    { ref: 1, kind: "graph", source_type: "official", cited: true, label: "DOC-OFFICIAL-SYLLABUS-001, p.15",
      text: "ARTIFICIAL INTELLIGENCE (course COURSE-2CEIT602, official). Relationships: practicals_in: LAB-IT-001 (AI & Machine Learning Lab) [synthetic]",
      citation: { document_id: "DOC-OFFICIAL-SYLLABUS-001", version_no: 1, title: "ARTIFICIAL INTELLIGENCE",
                  document_type: "knowledge_graph", page_start: 15, page_end: 15, section: null } },
    { ref: 2, kind: "document", source_type: "synthetic", cited: false, label: "DOC-LABS-001, p.2",
      text: "LAB-IT-001 AI & Machine Learning Lab",
      citation: { document_id: "DOC-LABS-001", version_no: 1, title: "Laboratories", document_type: "laboratories",
                  page_start: 2, page_end: 2, section: null } },
  ],
  grounding: { passed: true, issues: [], warnings: [] },
  provider: "extractive",
  model: "extractive-v1",
  timings_ms: { total: 42 },
};
