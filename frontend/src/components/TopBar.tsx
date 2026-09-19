import { GraduationCap, LogOut } from "lucide-react";
import { NavLink, useNavigate } from "react-router";

import { useAuth } from "../auth";

export function TopBar() {
  const { state, can, logout } = useAuth();
  const navigate = useNavigate();
  const me = state.status === "signed-in" ? state.me : null;
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-sunken text-ink" : "text-ink-2 hover:bg-sunken"}`;

  return (
    <header className="sticky top-0 z-10 border-b border-line bg-canvas/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1280px] items-center gap-4 px-4 lg:px-8">
        <span className="flex items-center gap-2 font-medium tracking-tight">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-ink text-white"><GraduationCap size={16} aria-hidden /></span>
          CampusMate
        </span>
        <nav className="flex gap-1" aria-label="Main">
          {can("chat:use") && <NavLink to="/" end className={link}>Assistant</NavLink>}
          {can("documents:read") && <NavLink to="/admin" className={link}>Knowledge base</NavLink>}
        </nav>
        {me && (
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden text-ink-2 sm:inline">{me.user.full_name ?? me.user.email}</span>
            <span className="rounded-full bg-sunken px-2 py-0.5 text-xs capitalize text-ink-2">{me.user.role}</span>
            <button type="button" onClick={async () => { await logout(); navigate("/login"); }} aria-label="Log out"
                    className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-ink-2 hover:bg-sunken">
              <LogOut size={15} aria-hidden /> <span className="hidden sm:inline">Log out</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
