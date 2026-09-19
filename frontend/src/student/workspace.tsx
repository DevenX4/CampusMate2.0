// State of the student workspace, shared by its pages: the conversation (kept while moving between
// Curriculum, Faculty, ... and back) and the selected department / programme / semester.

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { api, ApiError } from "../api/client";
import type { ChatResponse } from "../api/types";
import { useAuth } from "../auth";

export interface Turn {
  id: number;
  question: string;
  response?: ChatResponse;
  error?: string;
}

export interface Scope {
  departmentId: string;
  programId: string;
  semesterId: string;
}

export type PanelTab = "sources" | "tree" | "trace";

interface Workspace {
  turns: Turn[];
  busy: boolean;
  ask: (question: string) => Promise<void>;
  reset: () => void;
  selected: { turn: number; ref: number | null } | null;
  select: (turn: number, ref: number | null, tab?: PanelTab) => void;
  tab: PanelTab;
  setTab: (tab: PanelTab) => void;
  panelOpen: boolean;
  setPanelOpen: (open: boolean) => void;
  scope: Scope;
  setScope: (scope: Scope) => void;
  historyVersion: number;
}

const WorkspaceContext = createContext<Workspace | null>(null);
const SCOPE_KEY = "campusmate-scope";

function savedScope(): Scope {
  try {
    const saved = JSON.parse(localStorage.getItem(SCOPE_KEY) ?? "null");
    if (saved && typeof saved === "object") return { departmentId: "", programId: "", semesterId: "", ...saved };
  } catch { /* nothing saved */ }
  return { departmentId: "", programId: "", semesterId: "" };
}

const firstCited = (r: ChatResponse) => r.sources.find((s) => s.cited)?.ref ?? r.sources[0]?.ref ?? null;

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { refresh } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Workspace["selected"]>(null);
  const [tab, setTab] = useState<PanelTab>("sources");
  // Open beside the chat on wide screens; on smaller ones it slides over only when asked for.
  const [panelOpen, setPanelOpen] = useState(() => window.matchMedia?.("(min-width: 1280px)").matches ?? true);
  const [scope, setScopeState] = useState<Scope>(savedScope);
  const [historyVersion, setHistoryVersion] = useState(0);
  const nextId = useRef(1);

  const setScope = useCallback((next: Scope) => {
    setScopeState(next);
    try { localStorage.setItem(SCOPE_KEY, JSON.stringify(next)); } catch { /* not remembered */ }
  }, []);

  const ask = useCallback(async (question: string) => {
    const id = nextId.current++;
    setTurns((all) => [...all, { id, question }]);
    setBusy(true);
    try {
      const response = await api.ask(question, {
        program_id: scope.programId || undefined, semester_id: scope.semesterId || undefined,
      });
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, response } : t)));
      setSelected({ turn: id, ref: firstCited(response) });
      setTab("sources");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) void refresh();  // session expired: back to login
      const message = error instanceof Error ? error.message : "Something went wrong.";
      setTurns((all) => all.map((t) => (t.id === id ? { ...t, error: message } : t)));
    } finally {
      setBusy(false);
      setHistoryVersion((v) => v + 1);
    }
  }, [scope.programId, scope.semesterId, refresh]);

  const reset = useCallback(() => { setTurns([]); setSelected(null); }, []);

  const select = useCallback((turn: number, ref: number | null, next?: PanelTab) => {
    setSelected({ turn, ref });
    if (next) setTab(next);
    setPanelOpen(true);
  }, []);

  // Alt+N: a new query, as the sidebar button says.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey && event.key.toLowerCase() === "n") { event.preventDefault(); reset(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [reset]);

  const value = useMemo<Workspace>(() => ({
    turns, busy, ask, reset, selected, select, tab, setTab, panelOpen, setPanelOpen, scope, setScope, historyVersion,
  }), [turns, busy, ask, reset, selected, select, tab, panelOpen, scope, setScope, historyVersion]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): Workspace {
  const workspace = useContext(WorkspaceContext);
  if (!workspace) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return workspace;
}
