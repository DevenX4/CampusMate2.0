// Who is logged in, as the server says (GET /auth/me). The permissions shown here only decide
// what the UI offers; every request is authorised again by the server.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, ApiError } from "./api/client";
import type { Me } from "./api/types";

type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "offline"; message: string }
  | { status: "signed-in"; me: Me };

interface Auth {
  state: AuthState;
  me: Me | null;
  can: (permission: string) => boolean;
  login: (username: string, password: string) => Promise<Me | null>;
  logout: () => Promise<void>;
  refresh: () => Promise<Me | null>;
}

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const refresh = useCallback(async () => {
    try {
      const me = await api.me();
      setState({ status: "signed-in", me });
      return me;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setState({ status: "anonymous" });
      else setState({ status: "offline", message: error instanceof Error ? error.message : "Unknown error" });
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<Auth>(() => {
    const me = state.status === "signed-in" ? state.me : null;
    return {
      state,
      me,
      can: (permission) => !!me?.permissions.includes(permission),
      login: async (username, password) => {
        await api.login(username, password);
        return refresh();
      },
      logout: async () => {
        await api.logout();
        setState({ status: "anonymous" });
      },
      refresh,
    };
  }, [state, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>");
  return auth;
}

// Where a user starts: administrators in the knowledge console, everyone else in the assistant.
export const homeFor = (me: Me | null) =>
  me?.permissions.includes("documents:manage") ? "/admin" : "/";
