import { Loader2, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { api } from "../api/client";
import { DOCUMENT_TYPES, type Department } from "../api/types";

// New document: the file plus the metadata the backend requires. Whether the file is official
// or synthetic has no default: the admin must say so, because it decides how every answer from
// it is labelled.
export function UploadDialog({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [sourceType, setSourceType] = useState<"" | "official" | "synthetic">("");
  const [departmentId, setDepartmentId] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.departments().then(setDepartments).catch(() => setDepartments([]));
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const ready = file !== null && title.trim().length >= 3 && documentType !== "" && sourceType !== "" && !busy;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!ready || !file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("title", title.trim());
    form.append("document_type", documentType);
    form.append("source_type", sourceType);
    if (departmentId) form.append("department_id", departmentId);
    if (academicYear.trim()) form.append("academic_year", academicYear.trim());
    setBusy(true);
    setError(null);
    try {
      await api.uploadDocument(form);
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The upload failed.");
    } finally {
      setBusy(false);
    }
  }

  const field = "mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent";
  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-canvas/70 px-4 backdrop-blur-sm">
      <form role="dialog" aria-modal="true" aria-labelledby="upload-title" onSubmit={submit}
            className="w-full max-w-lg rounded-2xl border border-line bg-surface p-6 shadow-float">
        <div className="flex items-center justify-between">
          <h2 id="upload-title" className="text-lg font-medium">Upload a document</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-ink-3 hover:bg-sunken"><X size={18} /></button>
        </div>
        <p className="mt-1 text-sm text-ink-2">A PDF becomes searchable after ingestion. Uploading the same file twice is refused.</p>

        <label className="mt-5 block text-sm font-medium" htmlFor="file">PDF file</label>
        <input id="file" type="file" accept="application/pdf,.pdf" required
               onChange={(e) => setFile(e.target.files?.[0] ?? null)} className={`${field} file:mr-3 file:border-0 file:bg-sunken file:px-2 file:py-1`} />

        <label className="mt-4 block text-sm font-medium" htmlFor="title">Title</label>
        <input id="title" value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} className={field} />

        <label className="mt-4 block text-sm font-medium" htmlFor="document-type">Document type</label>
        <select id="document-type" value={documentType} onChange={(e) => setDocumentType(e.target.value)} className={field}>
          <option value="" disabled>Choose a type</option>
          {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t.replaceAll("_", " ")}</option>)}
        </select>

        <fieldset className="mt-4">
          <legend className="text-sm font-medium">Trust level</legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {([["official", "Official GUNI document"], ["synthetic", "Synthetic demo data"]] as const).map(([value, label]) => (
              <label key={value} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm
                                             ${sourceType === value ? "border-accent bg-accent-soft" : "border-line"}`}>
                <input type="radio" name="source_type" value={value} checked={sourceType === value}
                       onChange={() => setSourceType(value)} className="accent-accent" />
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="block text-sm font-medium">Department (optional)
            <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} className={field}>
              <option value="">None</option>
              {departments.map((d) => <option key={d.department_id} value={d.department_id}>{d.short_name ?? d.department_name}</option>)}
            </select>
          </label>
          <label className="block text-sm font-medium">Academic year (optional)
            <input value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="2026-2027"
                   pattern="\d{4}-\d{4}" className={field} />
          </label>
        </div>

        {error && <p role="alert" className="mt-4 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-ink-2 hover:bg-sunken">Cancel</button>
          <button type="submit" disabled={!ready}
                  className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40">
            {busy && <Loader2 size={15} className="animate-spin" aria-hidden />} Upload
          </button>
        </div>
      </form>
    </div>
  );
}
