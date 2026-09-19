import { expect, it, vi } from "vitest";

import { mockApi } from "../test/mockApi";
import { api, ApiError } from "./client";

it("sends JSON to /api/v1 with same-origin credentials only", async () => {
  const calls = mockApi({ "POST /api/v1/chat/query": { answer: "ok" } });
  await api.ask("What grade do I get for 85 marks?");
  const { url, init } = calls[0];
  expect(url).toBe("/api/v1/chat/query");
  expect(init.credentials).toBe("same-origin");
  expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  expect(JSON.parse(init.body as string)).toEqual({ question: "What grade do I get for 85 marks?" });
});

it("turns the backend error format into an ApiError", async () => {
  mockApi({ "POST /api/v1/auth/login": Response.json({ error: { code: "unauthorized", message: "Invalid email or password." } }, { status: 401 }) });
  await expect(api.login("a@campusmate-demo.example", "wrong")).rejects.toMatchObject(
    { status: 401, code: "unauthorized", message: "Invalid email or password." });
});

it("reports an unreachable server", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
  const error = await api.me().catch((e: unknown) => e);
  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({ status: 0, message: "The CampusMate server cannot be reached." });
});

it("leaves out empty query parameters", async () => {
  const calls = mockApi({ "GET /api/v1/documents": { items: [], total: 0, limit: 20, offset: 0 } });
  await api.documents({ q: "", status: "active", limit: 20, offset: 0 });
  expect(calls[0].url).toBe("/api/v1/documents?status=active&limit=20&offset=0");
});
