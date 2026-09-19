import { GraduationCap, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { useAuth } from "../auth";

export function LoginPage() {
  const { state, login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "signed-in") return <Navigate to={from} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  const field = "mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] outline-none focus:border-accent";
  return (
    <main className="grid min-h-screen place-items-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-line bg-surface p-8 shadow-float">
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-ink text-white"><GraduationCap size={20} aria-hidden /></span>
        <h1 className="mt-5 text-2xl font-medium tracking-tight">Sign in to CampusMate</h1>
        <p className="mt-1 text-sm text-ink-2">The campus assistant of the GUNI IT department.</p>
        <label className="mt-6 block text-sm font-medium" htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="username" required value={email}
               onChange={(e) => setEmail(e.target.value)} className={field} />
        <label className="mt-4 block text-sm font-medium" htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" required value={password}
               onChange={(e) => setPassword(e.target.value)} className={field} />
        {error && <p role="alert" className="mt-4 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        {state.status === "offline" && (
          <p role="alert" className="mt-4 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">{state.message}</p>
        )}
        <button type="submit" disabled={busy}
                className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-ink py-2.5 text-sm font-medium
                           text-white disabled:opacity-60">
          {busy && <Loader2 size={15} className="animate-spin" aria-hidden />} Sign in
        </button>
      </form>
    </main>
  );
}
