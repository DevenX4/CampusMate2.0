import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { renderAt } from "../test/render";
import { ADMIN, mockApi } from "../test/mockApi";
import { relativeTime } from "./AdminPage";

const DOCUMENTS = {
  total: 2, limit: 20, offset: 0,
  items: [
    { document_id: "DOC-OFFICIAL-SYLLABUS-001", title: "B.Tech IT syllabus", document_type: "official_structured_syllabus",
      source_type: "official", department_id: "DEPT-IT-001", status: "active", created_at: "2026-09-19T00:00:00Z",
      updated_at: "2026-09-19T00:00:00Z", latest_version_no: 1,
      active_version: { version_no: 1, status: "active", original_filename: "syllabus.pdf", size_bytes: 1, page_count: 742,
                        version_label: null, academic_year: null, created_at: "2026-09-19T00:00:00Z", activated_at: null } },
    { document_id: "DOC-NOTICES-001", title: "Notices", document_type: "notices", source_type: "synthetic",
      department_id: null, status: "inactive", created_at: "2026-09-19T00:00:00Z", updated_at: "2026-09-19T00:00:00Z",
      latest_version_no: 1, active_version: null },
  ],
};
const STATS = { active_documents: 11, total_documents: 12, total_chunks: 935, pending_jobs: 0, failed_jobs: 1,
                last_updated: null };

it("shows the real statistics, the documents and only the actions their status allows", async () => {
  const calls = mockApi({
    "GET /api/v1/auth/me": ADMIN, "GET /api/v1/documents/stats": STATS, "GET /api/v1/documents": DOCUMENTS,
    "POST /api/v1/documents/DOC-NOTICES-001/activate": DOCUMENTS.items[1],
  });
  renderAt("/admin");
  const stats = await screen.findByRole("region", { name: "Statistics" });
  expect(await within(stats).findByText("935")).toBeInTheDocument();
  expect(within(stats).getByText("12 in total")).toBeInTheDocument();

  const syllabus = (await screen.findByText("B.Tech IT syllabus")).closest("tr")!;
  expect(within(syllabus).getByRole("button", { name: "Deactivate" })).toBeInTheDocument();
  expect(within(syllabus).queryByRole("button", { name: "Activate" })).toBeNull();
  const notices = screen.getByText("Notices").closest("tr")!;
  expect(within(notices).getByText("Synthetic demo")).toBeInTheDocument();
  await userEvent.click(within(notices).getByRole("button", { name: "Activate" }));
  expect(calls.some((c) => c.url === "/api/v1/documents/DOC-NOTICES-001/activate" && c.init.method === "POST")).toBe(true);
});

it("refuses to upload until the trust level is chosen explicitly", async () => {
  mockApi({
    "GET /api/v1/auth/me": ADMIN, "GET /api/v1/documents/stats": STATS, "GET /api/v1/documents": DOCUMENTS,
    "GET /api/v1/departments": [],
  });
  renderAt("/admin");
  await userEvent.click(await screen.findByRole("button", { name: "Upload document" }));
  const dialog = screen.getByRole("dialog");
  await userEvent.upload(within(dialog).getByLabelText("PDF file"), new File(["%PDF-1.4"], "notice.pdf", { type: "application/pdf" }));
  await userEvent.type(within(dialog).getByLabelText("Title"), "Exam notice");
  await userEvent.selectOptions(within(dialog).getByLabelText("Document type"), "notices");
  const upload = within(dialog).getByRole("button", { name: "Upload" });
  expect(upload).toBeDisabled();
  await userEvent.click(within(dialog).getByLabelText("Synthetic demo data"));
  expect(upload).toBeEnabled();
});

const DETAIL = {
  ...DOCUMENTS.items[0], entity_count: 40,
  versions: [
    { version_no: 1, status: "superseded", sha256: "a".repeat(64), notes: null, original_filename: "syllabus-2021.pdf",
      size_bytes: 38_000_000, page_count: 742, version_label: "2021-22", academic_year: "2021-2022",
      created_at: "2026-09-18T00:00:00Z", activated_at: "2026-09-18T00:00:00Z" },
    { version_no: 2, status: "active", sha256: "b".repeat(64), notes: null, original_filename: "syllabus-2022.pdf",
      size_bytes: 39_000_000, page_count: 750, version_label: "2022-23", academic_year: "2022-2023",
      created_at: "2026-09-19T00:00:00Z", activated_at: "2026-09-19T00:00:00Z" },
  ],
  recent_jobs: [{ id: "j-1", version_no: 2, job_type: "ingest", status: "completed", current_stage: null, attempts: 1,
                  error_message: null, chunk_count: 120, created_at: "2026-09-19T00:00:00Z", finished_at: null }],
};

it("shows a document's versions, rolls back to an older one, and uploads a new version", async () => {
  const calls = mockApi({
    "GET /api/v1/auth/me": ADMIN, "GET /api/v1/documents/stats": STATS, "GET /api/v1/documents": DOCUMENTS,
    "GET /api/v1/documents/DOC-OFFICIAL-SYLLABUS-001": DETAIL,
    "POST /api/v1/documents/DOC-OFFICIAL-SYLLABUS-001/versions/1/activate": DETAIL,
    "POST /api/v1/documents/DOC-OFFICIAL-SYLLABUS-001/versions": DETAIL,
  });
  renderAt("/admin");
  await userEvent.click(await screen.findByRole("button", { name: "B.Tech IT syllabus" }));
  const panel = await screen.findByRole("dialog");
  const v1 = await within(panel).findByLabelText("Version 1");
  expect(v1).toHaveTextContent("superseded");
  expect(v1).toHaveTextContent("36.2 MB");
  expect(within(within(panel).getByLabelText("Version 2")).queryByRole("button", { name: "Activate" })).toBeNull();
  await userEvent.click(within(v1).getByRole("button", { name: "Activate" }));
  expect(calls.some((c) => c.url.endsWith("/versions/1/activate") && c.init.method === "POST")).toBe(true);

  await userEvent.upload(within(panel).getByLabelText("PDF file"), new File(["%PDF-1.4"], "syllabus-2023.pdf", { type: "application/pdf" }));
  await userEvent.type(within(panel).getByLabelText("Version label (optional)"), "2023-24");
  await userEvent.click(within(panel).getByRole("button", { name: "Upload version" }));
  expect(await within(panel).findByRole("status")).toHaveTextContent("replace the active version once ingested");
  const upload = calls.find((c) => c.url.endsWith("/DOC-OFFICIAL-SYLLABUS-001/versions") && c.init.method === "POST")!;
  const form = upload.init.body as FormData;
  expect(form.get("version_label")).toBe("2023-24");
  expect((form.get("file") as File).name).toBe("syllabus-2023.pdf");
  expect(within(panel).getByLabelText("Version label (optional)")).toHaveValue("");
});

it("formats relative times", () => {
  const now = Date.parse("2026-09-19T12:00:00Z");
  expect(relativeTime(null, now)).toBe("never");
  expect(relativeTime("2026-09-19T11:58:00Z", now)).toBe("2 min ago");
  expect(relativeTime("2026-09-19T09:00:00Z", now)).toBe("3 h ago");
});
