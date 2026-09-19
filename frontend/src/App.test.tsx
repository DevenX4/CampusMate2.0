import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { mockApi, STUDENT, unauthorized } from "./test/mockApi";
import { renderAt } from "./test/render";

it("sends visitors who are not logged in to the login page", async () => {
  mockApi({ "GET /api/v1/auth/me": unauthorized });
  renderAt("/");
  expect(await screen.findByRole("heading", { name: "Sign in to CampusMate" })).toBeInTheDocument();
});

it("logs in and opens the assistant", async () => {
  let loggedIn = false;
  const calls = mockApi({
    "GET /api/v1/auth/me": () => (loggedIn ? STUDENT : unauthorized()),
    "POST /api/v1/auth/login": () => { loggedIn = true; return { access_token: "hidden", user: STUDENT.user }; },
  });
  renderAt("/");
  await userEvent.type(await screen.findByLabelText("Email"), "student@campusmate-demo.example");
  await userEvent.type(screen.getByLabelText("Password"), "correct horse");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("heading", { name: "Welcome to CampusMate" })).toBeInTheDocument();
  const login = calls.find((c) => c.url.endsWith("/auth/login"))!;
  expect(JSON.parse(login.init.body as string)).toEqual({ email: "student@campusmate-demo.example", password: "correct horse" });
});

it("shows the login error from the server", async () => {
  mockApi({
    "GET /api/v1/auth/me": unauthorized,
    "POST /api/v1/auth/login": Response.json({ error: { code: "unauthorized", message: "Invalid email or password." } }, { status: 401 }),
  });
  renderAt("/login");
  await userEvent.type(await screen.findByLabelText("Email"), "someone@campusmate-demo.example");
  await userEvent.type(screen.getByLabelText("Password"), "wrong");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
});

it("does not open the knowledge base for a student", async () => {
  mockApi({ "GET /api/v1/auth/me": STUDENT });
  renderAt("/admin");
  expect(await screen.findByRole("heading", { name: "This page is not available to your role" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Upload document" })).toBeNull();
});
