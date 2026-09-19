import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { mockApi, SEMESTER_ANSWER, STUDENT } from "../test/mockApi";
import { renderAt } from "../test/render";

const ENTITY = {
  id: "SEM-BTECH-IT-06", type: "semester", title: "B.TECH-IT Semester VI", source_type: "official",
  provenance: { source_type: "official", document_id: "DOC-OFFICIAL-SYLLABUS-001", version_no: 1, page: 15, section: null },
  attributes: { total_credits: 23 }, attribute_source_types: {},
  relationships: { contains: [{ id: "COURSE-2CEIT602", source_type: "official", type: "course", title: "2CEIT602 ARTIFICIAL INTELLIGENCE" }] },
};

it("asks, shows the answer with its table and sources, and saves feedback", async () => {
  const calls = mockApi({
    "GET /api/v1/auth/me": STUDENT,
    "POST /api/v1/chat/query": SEMESTER_ANSWER,
    "POST /api/v1/chat/feedback": { query_id: "q-1", rating: "up", comment: null },
  });
  renderAt("/");
  await userEvent.type(await screen.findByLabelText("Your question"), "What courses are offered in Semester VI of B.Tech IT?{Enter}");

  const table = await screen.findByRole("table");
  expect(within(table).getByText("ARTIFICIAL INTELLIGENCE")).toBeInTheDocument();
  expect(within(table).getByText("2CEIT602")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /1 verified source/ })).toBeInTheDocument();

  const panel = screen.getByRole("complementary", { name: "Sources" });
  expect(within(within(panel).getByLabelText("Source 1")).getByText("Cited")).toBeInTheDocument();
  expect(within(within(panel).getByLabelText("Source 2")).getByText("Synthetic demo")).toBeInTheDocument();

  await userEvent.click(within(panel).getByRole("button", { name: "Good answer" }));
  expect(await within(panel).findByText("Thanks, your feedback is saved.")).toBeInTheDocument();
  const feedback = calls.find((c) => c.url.endsWith("/chat/feedback"))!;
  expect(JSON.parse(feedback.init.body as string)).toEqual({ query_id: "q-1", rating: "up", comment: null });
});

it("shows the knowledge tree and how the answer was produced", async () => {
  mockApi({
    "GET /api/v1/auth/me": STUDENT, "POST /api/v1/chat/query": SEMESTER_ANSWER,
    "GET /api/v1/knowledge/entities/SEM-BTECH-IT-06": ENTITY,
  });
  renderAt("/");
  await userEvent.type(await screen.findByLabelText("Your question"), "Semester VI courses{Enter}");
  await userEvent.click(await screen.findByRole("button", { name: "Knowledge Tree" }));
  const panel = screen.getByRole("complementary", { name: "Sources" });
  expect(await within(panel).findByText("2CEIT602 ARTIFICIAL INTELLIGENCE")).toBeInTheDocument();

  await userEvent.click(within(panel).getByRole("tab", { name: "Trace" }));
  expect(within(panel).getByText("courses of SEM-BTECH-IT-06: offerings table")).toBeInTheDocument();
  expect(within(panel).getByText(/Grounding check passed/)).toBeInTheDocument();
});

it("sends the semester chosen in the header with the question", async () => {
  const calls = mockApi({ "GET /api/v1/auth/me": STUDENT, "POST /api/v1/chat/query": SEMESTER_ANSWER });
  renderAt("/");
  const term = await screen.findByLabelText("Term");
  await screen.findByRole("option", { name: "Sem VI" });
  await userEvent.selectOptions(term, "SEM-BTECH-IT-06");
  await userEvent.type(screen.getByLabelText("Your question"), "Which courses are in this semester?{Enter}");
  await screen.findByRole("table");
  const query = calls.find((c) => c.url.endsWith("/chat/query"))!;
  expect(JSON.parse(query.init.body as string)).toMatchObject({ program_id: "PROG-BTECH-IT-001", semester_id: "SEM-BTECH-IT-06" });
});

it("shows a semester of the official curriculum", async () => {
  mockApi({
    "GET /api/v1/auth/me": STUDENT,
    "GET /api/v1/semesters/SEM-BTECH-IT-06": {
      semester_id: "SEM-BTECH-IT-06", semester_number: 6, semester_name: "Semester VI", total_credits: 23,
      provenance: { source_type: "official", document_id: "DOC-OFFICIAL-SYLLABUS-001", version_no: 1, page: 15, section: null },
      program: { program_id: "PROG-BTECH-IT-001", short_name: "B.TECH-IT" }, total_course: 6, total_marks: 900, effective_year: "2021-2022",
      regular_courses: [{ offering_id: "OFF-1", course_type: "regular", course: { course_id: "COURSE-2CEIT602", course_code: "2CEIT602", course_name: "ARTIFICIAL INTELLIGENCE", source_type: "official" },
                          credits: { theory: 3, practical: 1, total: 4, contact_hours: 5 }, marks: { total: 150 },
                          provenance: { source_type: "official", document_id: "DOC-OFFICIAL-SYLLABUS-001", version_no: 1, page: 15, section: null } }],
      elective_slots: [],
    },
  });
  renderAt("/curriculum");
  expect(await screen.findByText("ARTIFICIAL INTELLIGENCE")).toBeInTheDocument();
  expect(screen.getByText("150")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Programmes, semesters and courses" })).toBeInTheDocument();
});
