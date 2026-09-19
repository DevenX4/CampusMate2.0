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
  can: (permission: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const refresh = useCallback(async () => {
    try {
      setState({ status: "signed-in", me: await api.me() });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setState({ status: "anonymous" });
      else setState({ status: "offline", message: error instanceof Error ? error.message : "Unknown error" });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<Auth>(() => ({
    state,
    can: (permission) => state.status === "signed-in" && state.me.permissions.includes(permission),
    login: async (email, password) => {
      await api.login(email, password);
      await refresh();
    },
    logout: async () => {
      await api.logout();
      setState({ status: "anonymous" });
    },
    refresh,
  }), [state, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>");
  return auth;
}
