import {
  FolderClosed, GraduationCap, LayoutDashboard, LineChart, LogOut, Menu, MessagesSquare, Moon, Network, Settings, Sun, Users, X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router";

import { useAuth } from "../auth";
import { initials } from "../lib/format";
import { useTheme } from "../theme";

const NAV = [
  { to: "/admin", label: "Dashboard", Icon: LayoutDashboard, permission: "documents:read", end: true },
  { to: "/admin/documents", label: "Documents", Icon: FolderClosed, permission: "documents:read" },
  { to: "/admin/ingestion", label: "Ingestion", Icon: Network, permission: "ingestion:manage" },
  { to: "/admin/analytics", label: "Analytics", Icon: LineChart, permission: "audit:read" },
  { to: "/admin/users", label: "Users", Icon: Users, permission: "users:manage" },
  { to: "/admin/settings", label: "Settings", Icon: Settings, permission: "documents:read" },
];

// The admin console from the Stitch design: dark navigation on the left, the page on the right.
export function AdminLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden bg-admin-bg font-admin text-ink">
      <aside className="hidden w-64 shrink-0 lg:flex"><AdminSidebar /></aside>
      {menuOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 lg:hidden" onClick={() => setMenuOpen(false)}>
          <aside className="flex h-full w-64 animate-fade-up" onClick={(e) => e.stopPropagation()}>
            <AdminSidebar onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}
      <main className="flex-1 overflow-y-auto">
        <div className="flex items-center gap-3 border-b border-line bg-panel px-4 py-3 lg:hidden">
          <button type="button" onClick={() => setMenuOpen(true)} aria-label="Open navigation" className="grid h-8 w-8 place-items-center rounded-lg text-ink-3 hover:bg-panel-3">
            <Menu size={18} />
          </button>
          <span className="text-sm font-bold">CampusMate Admin</span>
        </div>
        <div className="mx-auto max-w-[1500px] space-y-6 p-4 sm:p-6 lg:p-7"><Outlet /></div>
      </main>
    </div>
  );
}

function AdminSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { me, can, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const name = me ? me.user.full_name ?? me.user.username ?? me.user.email : "";

  return (
    <div className="flex w-full flex-col justify-between border-r border-slate-800/80 bg-navy text-slate-300 shadow-xl">
      <div>
        <div className="flex items-center gap-3 border-b border-slate-800/60 p-5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/20"><GraduationCap size={20} /></span>
          <div>
            <p className="text-base font-bold tracking-tight text-white">CampusMate</p>
            <p className="text-xs font-medium text-slate-400">Admin Portal</p>
          </div>
          {onNavigate && <button type="button" onClick={onNavigate} aria-label="Close navigation" className="ml-auto text-slate-400"><X size={16} /></button>}
        </div>
        <nav aria-label="Admin" className="space-y-1 p-3">
          {NAV.filter((n) => can(n.permission)).map(({ to, label, Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={onNavigate}
                     className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition ${
                       isActive ? "bg-slate-800/70 text-blue-400 shadow-[inset_3px_0_0_#3b82f6,0_2px_10px_-2px_rgba(37,99,235,0.25)]"
                                : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-100"}`}>
              <Icon size={17} className="w-5" />
              {label}
            </NavLink>
          ))}
          {can("chat:use") && (
            <Link to="/" onClick={onNavigate} className="mt-3 flex items-center gap-3 rounded-lg border border-slate-800 px-3.5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-slate-700 hover:text-slate-100">
              <MessagesSquare size={17} className="w-5" /> Open assistant
            </Link>
          )}
        </nav>
      </div>

      <div className="space-y-2 p-3">
        <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-navy-2 p-4">
          <div className="flex items-center gap-3.5">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-blue-400/40 text-xs font-bold tracking-wider text-white shadow-[0_0_20px_-5px_rgba(59,130,246,0.5)]"
                  style={{ background: "radial-gradient(circle at 30% 30%, #3b82f6 0%, #1e1b4b 70%)" }}>AI</span>
            <p className="text-[12px] font-medium leading-tight text-slate-300">Keep knowledge alive for a smarter campus.</p>
          </div>
        </div>
        {me && (
          <div className="flex items-center gap-2.5 rounded-xl px-2 py-2">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-700 text-[11px] font-bold text-white">{initials(name)}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-semibold text-slate-100">{name}</span>
              <span className="block text-[10.5px] capitalize text-slate-500">{me.user.role}</span>
            </span>
            <IconButton label={theme === "dark" ? "Use light theme" : "Use dark theme"} onClick={toggle}>
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </IconButton>
            <IconButton label="Log out" onClick={async () => { await logout(); navigate("/login"); }}><LogOut size={15} /></IconButton>
          </div>
        )}
      </div>
    </div>
  );
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" aria-label={label} title={label} onClick={onClick}
            className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100">
      {children}
    </button>
  );
}

// The title row of every admin page.
export function PageHeader({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return (
    <header className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-ink">{title}</h2>
        <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center gap-3">{children}</div>}
    </header>
  );
}

export const card = "rounded-2xl border border-line bg-panel shadow-sm";
