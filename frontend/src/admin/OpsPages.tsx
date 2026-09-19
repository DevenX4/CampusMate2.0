import { BarChart3, Clock, Cpu, KeyRound, MessageSquareText, Plus, RotateCcw, Server, ShieldCheck, ThumbsDown, ThumbsUp, UserPlus } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { api } from "../api/client";
import type { IngestionJob, JobStatus, User } from "../api/types";
import { useAuth } from "../auth";
import { EmptyState, ErrorNote, Modal, Spinner, fieldClass } from "../components/ui";
import { formatDate, humanize, initials, relativeTime } from "../lib/format";
import { useLoad } from "../lib/useLoad";
import { card, PageHeader } from "./AdminLayout";

// --- ingestion ---------------------------------------------------------------------------------------

const JOB_STYLE: Record<JobStatus, string> = {
  pending: "bg-blue-500/10 text-blue-700 dark:text-blue-400", processing: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-400",
  completed: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400", failed: "bg-rose-500/10 text-rose-700 dark:text-rose-400",
};
const STAGES = ["extract", "clean", "chunk", "enrich", "index", "store"];

export function IngestionPage() {
  const [status, setStatus] = useState<JobStatus | "">("");
  const jobs = useLoad(() => api.jobs({ status: status || undefined, limit: 50 }), [status]);
  const [error, setError] = useState<string | null>(null);
  const running = (jobs.data?.items ?? []).some((j) => j.status === "pending" || j.status === "processing");

  useEffect(() => {  // follow work in progress
    if (!running) return;
    const timer = setInterval(jobs.reload, 4000);
    return () => clearInterval(timer);
  }, [running, jobs.reload]);

  async function retry(job: IngestionJob) {
    setError(null);
    try { await api.retryJob(job.id); jobs.reload(); } catch (e) { setError(e instanceof Error ? e.message : "Retry failed."); }
  }

  return (
    <>
      <PageHeader title="Ingestion" subtitle="Every document version goes through extract, clean, chunk, enrich, index and store. Jobs are durable: a restart resumes them." />
      <div className="flex flex-wrap gap-1.5">
        {(["", "pending", "processing", "completed", "failed"] as const).map((s) => (
          <button key={s || "all"} type="button" onClick={() => setStatus(s)}
                  className={`rounded-full px-3.5 py-1.5 text-xs font-medium capitalize transition ${status === s ? "bg-blue-600 text-white shadow-sm" : "text-ink-2 hover:bg-panel"}`}>
            {s || "All jobs"}
          </button>
        ))}
        {running && <span className="ml-auto flex items-center gap-1.5 text-xs text-ink-3"><Spinner /> updating while jobs run</span>}
      </div>
      {error && <ErrorNote>{error}</ErrorNote>}
      <section className={`${card} overflow-x-auto`}>
        <table className="w-full text-left text-xs">
          <thead className="border-b border-line-2 bg-panel-2/60 font-semibold uppercase tracking-wider text-ink-4">
            <tr>
              <th className="px-4 py-3">Document</th><th className="px-3 py-3">Job</th><th className="px-3 py-3">Status</th>
              <th className="px-3 py-3">Stage timings</th><th className="px-3 py-3 text-right">Chunks</th><th className="px-3 py-3">Queued</th><th className="px-3 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-line-2 text-ink-2">
            {(jobs.data?.items ?? []).map((job) => {
              const total = Object.values(job.stage_timings).reduce((a, b) => a + b, 0) || 1;
              return (
                <tr key={job.id} className="align-top transition hover:bg-panel-2">
                  <td className="px-4 py-3 font-mono text-[11px]">{job.document_id} <span className="text-ink-4">v{job.version_no}</span></td>
                  <td className="px-3 py-3 capitalize">{job.job_type}</td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${JOB_STYLE[job.status]}`}>{job.status}</span>
                    {job.current_stage && job.status === "processing" && <p className="mt-1 text-[10px] text-ink-4">{job.current_stage}…</p>}
                    {job.error_message && <p className="mt-1 max-w-xs text-[11px] text-rose-600">{job.error_message}</p>}
                  </td>
                  <td className="px-3 py-3">
                    {Object.keys(job.stage_timings).length ? (
                      <div className="w-56">
                        <div className="flex h-2 overflow-hidden rounded-full bg-panel-3">
                          {STAGES.filter((s) => job.stage_timings[s]).map((s, i) => (
                            <span key={s} title={`${s}: ${job.stage_timings[s]} ms`}
                                  className={["bg-blue-500", "bg-sky-400", "bg-indigo-500", "bg-violet-400", "bg-emerald-500", "bg-teal-400"][i]}
                                  style={{ width: `${(job.stage_timings[s] / total) * 100}%` }} />
                          ))}
                        </div>
                        <p className="mt-1 text-[10px] text-ink-4">{total} ms · {STAGES.filter((s) => job.stage_timings[s] !== undefined).map((s) => `${s} ${job.stage_timings[s]}`).join(" · ")}</p>
                      </div>
                    ) : <span className="text-ink-4">–</span>}
                  </td>
                  <td className="px-3 py-3 text-right font-semibold">{job.chunk_count ?? "–"}</td>
                  <td className="whitespace-nowrap px-3 py-3 text-ink-3">{relativeTime(job.created_at)}<span className="block text-[10px] text-ink-4">{job.attempts} attempt{job.attempts === 1 ? "" : "s"}</span></td>
                  <td className="px-3 py-3 text-right">
                    {job.status === "failed" && (
                      <button type="button" onClick={() => void retry(job)} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold text-blue-600 hover:bg-blue-500/10">
                        <RotateCcw size={12} /> Retry
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {jobs.data?.items.length === 0 && <EmptyState icon={<Server size={18} />} title="No ingestion jobs">Uploads and re-indexing create jobs here.</EmptyState>}
        {jobs.loading && !jobs.data && <div className="p-6"><Spinner label="Loading jobs…" /></div>}
      </section>
    </>
  );
}

// --- analytics ---------------------------------------------------------------------------------------

export function AnalyticsPage() {
  const stats = useLoad(() => api.analytics(), []);
  const s = stats.data;
  const answered = s ? (s.by_answer_type.answered ?? 0) + (s.by_answer_type.fallback ?? 0) : 0;
  const max = Math.max(1, ...(s?.last_7_days.map((d) => d.questions) ?? [1]));

  return (
    <>
      <PageHeader title="Analytics" subtitle="How the assistant is used, and where the knowledge base has gaps. No user identities are shown." />
      {stats.error && <ErrorNote>{stats.error}</ErrorNote>}
      {stats.loading && !s && <Spinner label="Loading…" />}
      {s && (
        <>
          <section className="grid grid-cols-2 gap-3.5 lg:grid-cols-5">
            <Kpi label="Questions asked" value={s.total_questions} icon={<MessageSquareText size={17} />} />
            <Kpi label="Answered" value={s.total_questions ? `${Math.round((answered / s.total_questions) * 100)}%` : "–"} icon={<ShieldCheck size={17} />} />
            <Kpi label="Abstained" value={s.by_answer_type.abstained ?? 0} icon={<BarChart3 size={17} />} />
            <Kpi label="Feedback" value={<span className="flex items-center gap-3 text-xl"><span className="flex items-center gap-1 text-emerald-600"><ThumbsUp size={15} />{s.feedback_up}</span><span className="flex items-center gap-1 text-rose-600"><ThumbsDown size={15} />{s.feedback_down}</span></span>} icon={<ThumbsUp size={17} />} />
            <Kpi label="Median latency" value={s.latency_p50_ms !== null ? `${s.latency_p50_ms} ms` : "–"} icon={<Clock size={17} />} note={s.latency_p95_ms !== null ? `p95 ${s.latency_p95_ms} ms` : undefined} />
          </section>

          <div className="grid gap-6 lg:grid-cols-3">
            <section className={`${card} p-5 lg:col-span-2`}>
              <h3 className="text-sm font-bold text-ink">Questions in the last 7 days</h3>
              <div className="mt-5 flex h-44 items-end gap-3">
                {s.last_7_days.map((d) => (
                  <div key={d.day} className="flex flex-1 flex-col items-center gap-1.5">
                    <div className="flex h-36 w-full flex-col items-center justify-end gap-1">
                      <span className="text-[10px] font-semibold text-ink-3">{d.questions}</span>
                      <div className={`w-full rounded-t-lg ${d.questions ? "bg-gradient-to-t from-blue-600 to-indigo-500" : "bg-line"}`}
                           style={{ height: `${Math.max(2, (d.questions / max) * 85)}%` }} />
                    </div>
                    <span className="text-[10px] text-ink-4">{new Date(d.day).toLocaleDateString("en-GB", { weekday: "short" })}</span>
                  </div>
                ))}
              </div>
            </section>
            <section className={`${card} space-y-5 p-5`}>
              <Breakdown title="Answer types" data={s.by_answer_type} total={s.total_questions} />
              <Breakdown title="Routes" data={s.by_route} total={s.total_questions} />
            </section>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <QuestionList title="Questions CampusMate could not answer" hint="Gaps in the knowledge base: candidates for new documents."
                          items={s.unanswered.map((q) => ({ question: q.question, when: q.created_at }))} />
            <QuestionList title="Answers rated down" hint="With the user’s comment, when given."
                          items={s.downvoted.map((q) => ({ question: q.question, when: q.created_at, comment: q.comment }))} />
          </div>
        </>
      )}
    </>
  );
}

function Kpi({ label, value, icon, note }: { label: string; value: ReactNode; icon: ReactNode; note?: string }) {
  return (
    <div className={`${card} flex items-center justify-between p-4`}>
      <div>
        <span className="block text-xs font-medium uppercase tracking-wider text-ink-4">{label}</span>
        <span className="mt-1 block text-2xl font-bold text-ink">{value}</span>
        {note && <span className="text-[11px] text-ink-4">{note}</span>}
      </div>
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">{icon}</span>
    </div>
  );
}

function Breakdown({ title, data, total }: { title: string; data: Record<string, number>; total: number }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <h3 className="mb-2.5 text-xs font-bold uppercase tracking-wider text-ink-4">{title}</h3>
      <div className="space-y-2">
        {entries.map(([key, n]) => (
          <div key={key} className="text-xs">
            <div className="mb-1 flex justify-between"><span className="capitalize text-ink-2">{humanize(key)}</span><span className="font-semibold text-ink">{n}</span></div>
            <div className="h-1.5 overflow-hidden rounded-full bg-panel-3"><div className="h-full rounded-full bg-blue-500" style={{ width: `${(n / Math.max(1, total)) * 100}%` }} /></div>
          </div>
        ))}
        {entries.length === 0 && <p className="text-xs text-ink-4">No data yet.</p>}
      </div>
    </div>
  );
}

function QuestionList({ title, hint, items }: { title: string; hint: string; items: { question: string; when: string; comment?: string | null }[] }) {
  return (
    <section className={`${card} p-5`}>
      <h3 className="text-sm font-bold text-ink">{title}</h3>
      <p className="text-xs text-ink-4">{hint}</p>
      <ul className="mt-3 divide-y divide-line-2">
        {items.map((item, i) => (
          <li key={i} className="py-2.5">
            <p className="text-xs font-medium text-ink">{item.question}</p>
            {item.comment && <p className="mt-0.5 text-[11px] italic text-ink-3">“{item.comment}”</p>}
            <p className="mt-0.5 text-[10px] text-ink-4">{relativeTime(item.when)}</p>
          </li>
        ))}
        {items.length === 0 && <li className="py-4 text-xs text-ink-4">None so far.</li>}
      </ul>
    </section>
  );
}

// --- users ------------------------------------------------------------------------------------------

export function UsersPage() {
  const { me } = useAuth();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const users = useLoad(() => api.users({ q: search || undefined, limit: 100 }), [search]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setSearch(q.trim()), 250);
    return () => clearTimeout(timer);
  }, [q]);

  async function update(user: User, change: { role?: string; is_active?: boolean }) {
    setError(null);
    try { await api.updateUser(user.id, change); users.reload(); } catch (e) { setError(e instanceof Error ? e.message : "The change failed."); }
  }

  return (
    <>
      <PageHeader title="Users" subtitle="Accounts and roles. Deactivating an account ends its sessions at once; accounts are never deleted, so the audit history stays intact.">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search users..." aria-label="Search users"
               className="w-60 rounded-xl border border-line bg-panel px-3.5 py-2 text-sm shadow-sm outline-none focus:border-blue-500" />
        <button type="button" onClick={() => setCreating(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-blue-500/30 hover:bg-blue-700">
          <Plus size={14} /> New user
        </button>
      </PageHeader>
      {error && <ErrorNote>{error}</ErrorNote>}
      <section className={`${card} overflow-x-auto`}>
        <table className="w-full text-left text-xs">
          <thead className="border-b border-line-2 bg-panel-2/60 font-semibold uppercase tracking-wider text-ink-4">
            <tr><th className="px-4 py-3">User</th><th className="px-3 py-3">Username</th><th className="px-3 py-3">Role</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Last login</th></tr>
          </thead>
          <tbody className="divide-y divide-line-2 text-ink-2">
            {(users.data?.items ?? []).map((u) => {
              const self = u.id === me?.user.id;
              const name = u.full_name ?? u.username ?? u.email;
              return (
                <tr key={u.id} className="transition hover:bg-panel-2">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <span className="grid h-8 w-8 place-items-center rounded-full bg-slate-800 text-[10px] font-bold text-white dark:bg-slate-700">{initials(name)}</span>
                      <div>
                        <p className="font-semibold text-ink">{name} {self && <span className="text-[10px] font-normal text-ink-4">(you)</span>}</p>
                        <p className="text-[11px] text-ink-4">{u.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3 font-mono text-[11px]">{u.username ?? "–"}{u.is_demo && <span className="ml-1.5 rounded bg-amber-500/10 px-1.5 py-0.5 font-sans text-[10px] font-semibold text-amber-700">demo</span>}</td>
                  <td className="px-3 py-3">
                    <select aria-label={`Role of ${name}`} value={u.role} disabled={self} onChange={(e) => void update(u, { role: e.target.value })}
                            className="rounded-lg border border-line bg-panel px-2 py-1 text-xs capitalize disabled:opacity-60">
                      {["admin", "faculty", "student"].map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-3">
                    <button type="button" disabled={self} onClick={() => void update(u, { is_active: !u.is_active })}
                            className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition disabled:opacity-60 ${u.is_active ? "bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-400" : "bg-panel-3 text-ink-3 hover:bg-panel-3/70"}`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-ink-3">{u.last_login_at ? relativeTime(u.last_login_at) : "never"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
      {creating && <NewUserModal onClose={() => setCreating(false)} onCreated={() => { setCreating(false); users.reload(); }} />}
    </>
  );
}

function NewUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ email: "", username: "", full_name: "", role: "student", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createUser({ ...form, username: form.username.trim() || undefined, full_name: form.full_name.trim() || undefined });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The account could not be created.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="New user" subtitle="The password must have at least 10 characters" icon={<UserPlus size={15} />} onClose={onClose}>
      <form onSubmit={submit} className="grid gap-4 p-6 sm:grid-cols-2">
        <label className="text-xs font-semibold text-ink-2 sm:col-span-2">Email<input type="email" required value={form.email} onChange={set("email")} className={`${fieldClass} mt-1`} /></label>
        <label className="text-xs font-semibold text-ink-2">Username (optional)<input value={form.username} onChange={set("username")} pattern="[a-zA-Z0-9][a-zA-Z0-9._\-]{2,39}" className={`${fieldClass} mt-1`} /></label>
        <label className="text-xs font-semibold text-ink-2">Full name<input value={form.full_name} onChange={set("full_name")} className={`${fieldClass} mt-1`} /></label>
        <label className="text-xs font-semibold text-ink-2">Role
          <select value={form.role} onChange={set("role")} className={`${fieldClass} mt-1 capitalize`}>
            {["student", "faculty", "admin"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-ink-2">Password<input type="password" required minLength={10} value={form.password} onChange={set("password")} className={`${fieldClass} mt-1`} /></label>
        {error && <div className="sm:col-span-2"><ErrorNote>{error}</ErrorNote></div>}
        <div className="flex justify-end gap-2.5 sm:col-span-2">
          <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-xs font-medium text-ink-2 hover:bg-panel-3">Cancel</button>
          <button type="submit" disabled={busy} className="rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50">Create account</button>
        </div>
      </form>
    </Modal>
  );
}

// --- settings ---------------------------------------------------------------------------------------

export function SettingsPage() {
  const info = useLoad(() => api.systemInfo(), []);
  const i = info.data;
  return (
    <>
      <PageHeader title="Settings" subtitle="How this installation is configured. Values come from the .env file and are read-only here." />
      {info.error && <ErrorNote>{info.error}</ErrorNote>}
      {i && (
        <div className="grid gap-6 lg:grid-cols-2">
          <SettingsCard icon={<Cpu size={16} />} title="Answer generation" rows={[
            ["Provider", i.generation_provider], ["Model", i.generation_model],
            ["Change with", "GENERATION_PROVIDER, GENERATION_MODEL"],
          ]} />
          <SettingsCard icon={<Server size={16} />} title="Retrieval" rows={[
            ["Embedding model", i.embedding_model], ["Vector store", `${i.vector_store} v${i.vector_store_version}`],
            ["Reranker (opt-in)", i.reranker_model], ["Ingestion", i.ingestion_in_api ? "inside the API process" : "separate worker"],
          ]} />
          <SettingsCard icon={<KeyRound size={16} />} title="Security limits" rows={[
            ["Failed logins before lockout", `${i.limits.login_max_failures} per ${i.limits.login_window_minutes} min`],
            ["Questions per user", `${i.limits.chat_questions_per_minute} per minute`],
            ["Largest upload", `${i.limits.max_upload_mb} MB`], ["Session lifetime", `${i.limits.session_ttl_hours} hours`],
          ]} />
          <SettingsCard icon={<ShieldCheck size={16} />} title="Installation" rows={[
            ["Version", i.version], ["Environment", i.environment],
            ["Checked", formatDate(new Date().toISOString())],
          ]} />
        </div>
      )}
    </>
  );
}

function SettingsCard({ icon, title, rows }: { icon: ReactNode; title: string; rows: [string, string][] }) {
  return (
    <section className={`${card} p-5`}>
      <h3 className="flex items-center gap-2 text-sm font-bold text-ink"><span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">{icon}</span>{title}</h3>
      <dl className="mt-4 divide-y divide-line-2 text-xs">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 py-2.5"><dt className="text-ink-3">{k}</dt><dd className="text-right font-mono text-[11.5px] text-ink">{v}</dd></div>
        ))}
      </dl>
    </section>
  );
}
