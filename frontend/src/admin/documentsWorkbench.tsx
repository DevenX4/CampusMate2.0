// Document actions and the documents card, shared by the Dashboard and the Documents page.

import { useMemo, useState, type ReactNode } from "react";

import { api } from "../api/client";
import { categoryOf, type Department, type DocumentSummary } from "../api/types";
import { CategoryPills, DocumentTable, type RowAction } from "./DocumentTable";
import { ConfirmDialog, DocumentPanel, ReplaceModal, UploadModal } from "./DocumentDialogs";
import { card } from "./AdminLayout";

type Dialog =
  | { kind: "upload" }
  | { kind: "open" | "replace"; doc: DocumentSummary }
  | { kind: "confirm"; doc: DocumentSummary; action: "deactivate" | "archive" | "reindex" | "delete" };

const CONFIRM = {
  deactivate: { title: "Deactivate document", confirm: "Deactivate", text: "CampusMate stops answering from it at once. Nothing is deleted, and you can activate it again." },
  archive: { title: "Archive document", confirm: "Archive", text: "It stops answering and is kept for the record." },
  reindex: { title: "Re-index document", confirm: "Re-index", text: "Its active version is chunked and embedded again; it keeps answering meanwhile." },
  delete: { title: "Delete document", confirm: "Delete", text: "It will no longer be used for answers. The history of its versions is kept." },
};

export function useDocumentActions(onChanged: () => void) {
  const [selected, setSelected] = useState<DocumentSummary | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const close = () => setDialog(null);
  const done = (message: string) => { setDialog(null); setNotice(message); onChanged(); };

  async function run(doc: DocumentSummary | null, action: RowAction | "upload") {
    setNotice(null);
    if (action === "upload") return setDialog({ kind: "upload" });
    if (!doc) return;
    setSelected(doc);
    if (action === "open" || action === "replace") return setDialog({ kind: action, doc });
    if (action === "activate") {
      try { await api.documentAction(doc.document_id, "activate"); done(`“${doc.title}” is active again.`); }
      catch (e) { setNotice(e instanceof Error ? e.message : "Activation failed."); }
      return;
    }
    setDialog({ kind: "confirm", doc, action });
  }

  let dialogs: ReactNode = null;
  if (dialog?.kind === "upload") dialogs = <UploadModal onClose={close} onUploaded={() => done("Uploaded. The ingestion pipeline is processing it.")} />;
  else if (dialog?.kind === "replace") dialogs = <ReplaceModal document={dialog.doc} onClose={close} onDone={() => done("New version uploaded. It replaces the active one once ingested.")} />;
  else if (dialog?.kind === "open") dialogs = <DocumentPanel documentId={dialog.doc.document_id} onClose={close} onChanged={onChanged} />;
  else if (dialog?.kind === "confirm") {
    const c = CONFIRM[dialog.action];
    const { doc, action } = dialog;
    dialogs = (
      <ConfirmDialog title={c.title} confirm={c.confirm} danger={action === "delete"} onClose={close}
                     onConfirm={async () => {
                       if (action === "delete") await api.deleteDocument(doc.document_id);
                       else await api.documentAction(doc.document_id, action);
                       if (action === "delete") setSelected(null);
                       done(`${c.confirm}: “${doc.title}”.`);
                     }}>
        <p><span className="font-semibold text-ink">{doc.title}</span></p>
        <p className="mt-1">{c.text}</p>
      </ConfirmDialog>
    );
  }
  return { selected, setSelected, run, dialogs, notice, setNotice };
}

export function DocumentsCard({ documents, departments, search, status, trust, pageSize, selectedId, onSelect, onAction, manage }: {
  documents: DocumentSummary[]; departments: Department[]; search: string; status: string; trust: string; pageSize: number;
  selectedId: string | null; onSelect: (d: DocumentSummary) => void; onAction: (d: DocumentSummary, a: RowAction) => void; manage: boolean;
}) {
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(0);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return documents.filter((d) => (!category || categoryOf(d.document_type) === category)
      && (!status || d.status === status) && (!trust || d.source_type === trust)
      && (!q || d.title.toLowerCase().includes(q) || d.document_id.toLowerCase().includes(q)))
      // Official records first, then by title.
      .sort((a, b) => Number(a.source_type !== "official") - Number(b.source_type !== "official") || a.title.localeCompare(b.title));
  }, [documents, category, search, status, trust]);
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const current = Math.min(page, pages - 1);
  const shown = filtered.slice(current * pageSize, current * pageSize + pageSize);

  return (
    <section aria-label="Documents" className={`${card} flex flex-col overflow-hidden`}>
      <CategoryPills value={category} onChange={(c) => { setCategory(c); setPage(0); }} />
      <DocumentTable documents={shown} departments={departments} selectedId={selectedId} onSelect={onSelect} onAction={onAction} manage={manage} />
      <div className="flex items-center justify-between border-t border-line-2 bg-panel-2/40 px-5 py-3 text-xs text-ink-4">
        <span>Showing {shown.length} of {filtered.length} document{filtered.length === 1 ? "" : "s"}</span>
        <div className="flex gap-1">
          <button type="button" disabled={current === 0} onClick={() => setPage(current - 1)}
                  className="rounded-lg border border-line bg-panel px-2.5 py-1 text-ink-2 transition hover:bg-panel-2 disabled:opacity-40">Previous</button>
          <button type="button" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}
                  className="rounded-lg border border-line bg-panel px-2.5 py-1 text-ink-2 transition hover:bg-panel-2 disabled:opacity-40">Next</button>
        </div>
      </div>
    </section>
  );
}
