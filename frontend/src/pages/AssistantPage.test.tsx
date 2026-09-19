import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { renderAt } from "../test/render";
import type { ChatResponse } from "../api/types";
import { LAB_ANSWER, mockApi, STUDENT } from "../test/mockApi";

it("asks, shows the cited answer with its sources and the synthetic warning, and saves feedback", async () => {
  const calls = mockApi({
    "GET /api/v1/auth/me": STUDENT,
    "POST /api/v1/chat/query": LAB_ANSWER,
    "POST /api/v1/chat/feedback": { query_id: "q-1", rating: "up", comment: null },
  });
  renderAt("/");
  await userEvent.type(await screen.findByLabelText("Your question"), "Which lab hosts the AI practicals?{Enter}");

  expect(await screen.findByText(/uses synthetic demo data, which is not official/)).toBeInTheDocument();
  const query = calls.find((c) => c.url.endsWith("/chat/query"))!;
  expect(JSON.parse(query.init.body as string)).toEqual({ question: "Which lab hosts the AI practicals?" });

  const panel = screen.getByRole("complementary", { name: "Sources" });
  expect(within(panel).getByText("1 cited of 2", { exact: false })).toBeInTheDocument();
  expect(within(within(panel).getByLabelText("Source 1")).getByText("Cited in the answer")).toBeInTheDocument();
  expect(within(within(panel).getByLabelText("Source 2")).getByText("Synthetic demo")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Good answer" }));
  expect(await screen.findByText("Thanks, your feedback is saved.")).toBeInTheDocument();
  const feedback = calls.find((c) => c.url.endsWith("/chat/feedback"))!;
  expect(JSON.parse(feedback.init.body as string)).toEqual({ query_id: "q-1", rating: "up", comment: null });
});

it("shows an abstention plainly, and unsupported requests without feedback", async () => {
  const abstained: ChatResponse = {
    ...LAB_ANSWER, query_id: "q-2", contains_synthetic: false, sources: [], answer_type: "abstained",
    answer: "I couldn't find authoritative information for that in the current CampusMate knowledge base.",
  };
  const unsupported: ChatResponse = {
    ...abstained, query_id: "q-3", answer_type: "unsupported",
    answer: "CampusMate cannot see personal records such as your marks, attendance or fees yet.",
  };
  let reply = abstained;
  mockApi({ "GET /api/v1/auth/me": STUDENT, "POST /api/v1/chat/query": () => reply });
  renderAt("/");
  await userEvent.type(await screen.findByLabelText("Your question"), "What is the hostel curfew?{Enter}");
  expect(await screen.findByText(/does not guess/)).toBeInTheDocument();
  expect(screen.queryByText(/synthetic demo data, which/)).toBeNull();
  expect(screen.getAllByRole("button", { name: "Good answer" })).toHaveLength(1);

  reply = unsupported;
  await userEvent.type(screen.getByLabelText("Your question"), "What are my marks?{Enter}");
  expect(await screen.findByText(/cannot see personal records/)).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Good answer" })).toHaveLength(1);  // none for the unsupported one
});

it("survives a browser whose scrollIntoView returns a Promise (as Chromium's does)", async () => {
  // Found with headless Edge: an effect returned that Promise, and React's clean-up crashed the page.
  Object.defineProperty(Element.prototype, "scrollIntoView", { value: () => Promise.resolve(), configurable: true });
  try {
    mockApi({ "GET /api/v1/auth/me": STUDENT, "POST /api/v1/chat/query": LAB_ANSWER });
    renderAt("/");
    await userEvent.type(await screen.findByLabelText("Your question"), "Which lab hosts the AI practicals?{Enter}");
    expect(await screen.findByText(/uses synthetic demo data/)).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong on this page")).toBeNull();
  } finally {
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;  // jsdom has none
  }
});
