import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { ADMIN, mockApi, STUDENT, unauthorized } from "./test/mockApi";
import { renderAt } from "./test/render";

it("sends visitors who are not logged in to the login page", async () => {
  mockApi({ "GET /api/v1/auth/me": unauthorized });
  renderAt("/");
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
});

it("logs a student in by username and opens the assistant", async () => {
  let loggedIn = false;
  const calls = mockApi({
    "GET /api/v1/auth/me": () => (loggedIn ? STUDENT : unauthorized()),
    "POST /api/v1/auth/login": () => { loggedIn = true; return { access_token: "hidden", user: STUDENT.user }; },
  });
  renderAt("/");
  await userEvent.type(await screen.findByLabelText("Username or email"), "student");
  await userEvent.type(screen.getByLabelText("Password"), "student@123");
  await userEvent.click(screen.getByRole("button", { name: /Sign in/ }));
  expect(await screen.findByRole("heading", { name: "Welcome to CampusMate" })).toBeInTheDocument();
  const login = calls.find((c) => c.url.endsWith("/auth/login"))!;
  expect(JSON.parse(login.init.body as string)).toEqual({ username: "student", password: "student@123" });
});

it("sends an administrator to the knowledge console, and demo accounts fill the form", async () => {
  let loggedIn = false;
  mockApi({
    "GET /api/v1/auth/me": () => (loggedIn ? ADMIN : unauthorized()),
    "POST /api/v1/auth/login": () => { loggedIn = true; return {}; },
    "GET /api/v1/documents": { items: [], total: 0, limit: 100, offset: 0 },
    "GET /api/v1/documents/stats": { active_documents: 12, total_documents: 12, total_chunks: 935, pending_jobs: 0, failed_jobs: 0, last_updated: null },
  });
  renderAt("/login");
  await userEvent.click(await screen.findByRole("button", { name: /admin@123/ }));
  expect(screen.getByLabelText("Username or email")).toHaveValue("admin");
  await userEvent.click(screen.getByRole("button", { name: /Sign in/ }));
  expect(await screen.findByRole("heading", { name: "Knowledge Control Center" })).toBeInTheDocument();
});

it("shows the login error from the server", async () => {
  mockApi({
    "GET /api/v1/auth/me": unauthorized,
    "POST /api/v1/auth/login": Response.json({ error: { code: "unauthorized", message: "Invalid username or password." } }, { status: 401 }),
  });
  renderAt("/login");
  await userEvent.type(await screen.findByLabelText("Username or email"), "someone");
  await userEvent.type(screen.getByLabelText("Password"), "wrong");
  await userEvent.click(screen.getByRole("button", { name: /Sign in/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password.");
});

it("does not open the knowledge console for a student", async () => {
  mockApi({ "GET /api/v1/auth/me": STUDENT });
  renderAt("/admin");
  expect(await screen.findByRole("heading", { name: "This page is not available to your role" })).toBeInTheDocument();
});
