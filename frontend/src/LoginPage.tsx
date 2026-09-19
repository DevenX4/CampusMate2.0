import { ArrowRight, Eye, EyeOff, FileCheck2, GitBranch, Loader2, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { api } from "./api/client";
import { homeFor, useAuth } from "./auth";
import { LogoMark } from "./components/ui";
import { useLoad } from "./lib/useLoad";

const FEATURES = [
  { Icon: FileCheck2, title: "Every answer cites its source", text: "Document, version and page, one click away." },
  { Icon: ShieldCheck, title: "Official vs demo, always labelled", text: "Synthetic demo data is never shown as official." },
  { Icon: GitBranch, title: "Structured, graph and document search", text: "Exact figures from the syllabus, not guesses." },
];

export function LoginPage() {
  const { state, me, login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from;
  const demo = useLoad(() => api.demoAccounts(), []);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "signed-in") return <Navigate to={from ?? homeFor(me)} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const signedIn = await login(username.trim(), password);
      navigate(from ?? homeFor(signedIn), { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  const field = "mt-1.5 w-full rounded-xl border border-line bg-panel px-3.5 py-2.5 text-sm text-ink outline-none transition placeholder:text-ink-4 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20";
  return (
    <div className="campus-backdrop grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-blue-600/25 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-40 right-0 h-[28rem] w-[28rem] rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <LogoMark />
          <div>
            <p className="text-sm font-bold tracking-tight">CampusMate</p>
            <p className="text-[11px] text-slate-400">GUNI IT campus assistant</p>
          </div>
        </div>
        <div className="relative max-w-lg">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-blue-400">University Knowledge Base</p>
          <h1 className="mt-3 text-4xl font-bold leading-tight tracking-tight">
            Answers about your programme,<br />grounded in the <span className="font-serif font-normal italic text-blue-300">actual</span> records.
          </h1>
          <ul className="mt-10 space-y-5">
            {FEATURES.map(({ Icon, title, text }) => (
              <li key={title} className="flex gap-3.5">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/5 text-blue-300"><Icon size={17} /></span>
                <span><span className="block text-sm font-semibold">{title}</span><span className="block text-xs text-slate-400">{text}</span></span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-[11px] text-slate-500">Ganpat University · Department of Information Technology · local deployment</p>
      </section>

      <main className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden"><LogoMark /><span className="text-sm font-bold text-ink">CampusMate</span></div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">Sign in</h2>
          <p className="mt-1 text-sm text-ink-3">Use your CampusMate username or email.</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <div>
              <label className="text-xs font-semibold text-ink-2" htmlFor="username">Username or email</label>
              <input id="username" autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)}
                     placeholder="e.g. student" className={field} />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink-2" htmlFor="password">Password</label>
              <div className="relative">
                <input id="password" type={show ? "text" : "password"} autoComplete="current-password" required value={password}
                       onChange={(e) => setPassword(e.target.value)} className={`${field} pr-10`} />
                <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}
                        className="absolute right-2.5 top-1/2 mt-[3px] -translate-y-1/2 rounded-md p-1 text-ink-4 hover:text-ink-2">
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            {error && <p role="alert" className="rounded-xl bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-700 dark:text-rose-400">{error}</p>}
            {state.status === "offline" && <p role="alert" className="rounded-xl bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-700">{state.message}</p>}
            <button type="submit" disabled={busy}
                    className="group flex w-full items-center justify-center gap-2 rounded-xl bg-solid py-2.5 text-sm font-semibold text-solid-ink shadow-sm transition hover:bg-blue-600 hover:text-white disabled:opacity-60">
              {busy ? <Loader2 size={16} className="animate-spin" /> : null}
              Sign in <ArrowRight size={16} className="transition group-hover:translate-x-0.5" />
            </button>
          </form>

          {demo.data?.enabled && (
            <div className="mt-8 rounded-2xl border border-dashed border-line bg-panel-2 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-4">Demo accounts · local only</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {demo.data.accounts.map((a) => (
                  <button key={a.username} type="button" onClick={() => { setUsername(a.username); setPassword(a.password); }}
                          className="rounded-xl border border-line bg-panel px-3 py-2 text-left transition hover:border-blue-500/50">
                    <span className="block text-xs font-semibold capitalize text-ink">{a.role}</span>
                    <span className="block font-mono text-[10.5px] text-ink-3">{a.username} · {a.password}</span>
                  </button>
                ))}
              </div>
              <p className="mt-2.5 text-[10.5px] leading-relaxed text-ink-4">Click to fill in. These accounts cannot sign in when CampusMate runs in production.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
