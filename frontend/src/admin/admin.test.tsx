import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { ADMIN, document, mockApi } from "../test/mockApi";
import { renderAt } from "../test/render";

const DOCUMENTS = {
  total: 2, limit: 100, offset: 0,
  items: [
    document({}),
    document({ document_id: "DOC-NOTICES-001", title: "Department Notices", document_type: "notices", source_type: "synthetic", chunk_count: 40 }),
  ],
};
const STATS = { active_documents: 12, total_documents: 12, total_chunks: 935, pending_jobs: 0, failed_jobs: 0, last_updated: null };
const baseRoutes = { "GET /api/v1/auth/me": ADMIN, "GET /api/v1/documents": DOCUMENTS, "GET /api/v1/documents/stats": STATS };

it("shows real statistics and filters documents by category", async () => {
  mockApi(baseRoutes);
  renderAt("/admin");
  const stats = await screen.findByRole("region", { name: "Statistics" });
  expect(await within(stats).findByText("935")).toBeInTheDocument();
  expect(await screen.findByText("GUNI Structured Syllabus")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Notices" }));
  expect(screen.queryByText("GUNI Structured Syllabus")).toBeNull();
  expect(screen.getByText("Department Notices")).toBeInTheDocument();
  expect(screen.getByText("Showing 1 of 1 document")).toBeInTheDocument();
});

it("quick actions apply to the selected document, after confirmation", async () => {
  const calls = mockApi({ ...baseRoutes, "POST /api/v1/documents/DOC-NOTICES-001/deactivate": DOCUMENTS.items[1] });
  renderAt("/admin");
  const quick = await screen.findByRole("region", { name: "Quick Actions" });
  expect(within(quick).getByRole("button", { name: /Deactivate Document/ })).toBeDisabled();

  await userEvent.click(await screen.findByText("DOC-NOTICES-001"));
  const deactivate = within(quick).getByRole("button", { name: /Deactivate Document/ });
  expect(deactivate).toBeEnabled();
  await userEvent.click(deactivate);
  const dialog = await screen.findByRole("dialog", { name: "Deactivate document" });
  await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Deactivate: “Department Notices”");
  expect(calls.some((c) => c.url === "/api/v1/documents/DOC-NOTICES-001/deactivate" && c.init.method === "POST")).toBe(true);
});

it("refuses to upload until the trust level is chosen explicitly", async () => {
  mockApi(baseRoutes);
  renderAt("/admin");
  const [headerUpload] = await screen.findAllByRole("button", { name: /Upload Document/ });  // header and Quick Actions
  await userEvent.click(headerUpload);
  const dialog = screen.getByRole("dialog", { name: "Upload New PDF to CampusMate" });
  await userEvent.upload(within(dialog).getByLabelText("PDF file"), new File(["%PDF-1.4"], "exam_notice.pdf", { type: "application/pdf" }));
  expect(within(dialog).getByDisplayValue("exam notice")).toBeInTheDocument();  // title suggested from the file name
  await userEvent.selectOptions(within(dialog).getByLabelText("Document type"), "notices");
  const upload = within(dialog).getByRole("button", { name: /Start Ingestion Pipeline/ });
  expect(upload).toBeDisabled();
  await userEvent.click(within(dialog).getByLabelText("Synthetic demo data"));
  expect(upload).toBeEnabled();
});

it("creates a user from the users page", async () => {
  const calls = mockApi({
    ...baseRoutes,
    "GET /api/v1/users": { items: [ADMIN.user], total: 1, limit: 100, offset: 0 },
    "POST /api/v1/users": { ...ADMIN.user, id: "u-new", email: "new@campusmate-demo.example", role: "faculty" },
  });
  renderAt("/admin/users");
  await userEvent.click(await screen.findByRole("button", { name: /New user/ }));
  const dialog = screen.getByRole("dialog", { name: "New user" });
  await userEvent.type(within(dialog).getByLabelText("Email"), "new@campusmate-demo.example");
  await userEvent.type(within(dialog).getByLabelText("Password"), "a-long-password");
  await userEvent.selectOptions(within(dialog).getByLabelText("Role"), "faculty");
  await userEvent.click(within(dialog).getByRole("button", { name: "Create account" }));
  const created = calls.find((c) => c.url === "/api/v1/users" && c.init.method === "POST")!;
  expect(JSON.parse(created.init.body as string)).toMatchObject({ email: "new@campusmate-demo.example", role: "faculty", password: "a-long-password" });
});
