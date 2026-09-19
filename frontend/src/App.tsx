import { Loader2 } from "lucide-react";
import { Component, type ReactNode } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router";

import { AuthProvider, useAuth } from "./auth";
import { AdminPage } from "./pages/AdminPage";
import { AssistantPage } from "./pages/AssistantPage";
import { LoginPage } from "./pages/LoginPage";

// Shows a page only to users whose role has the permission. This is a convenience: the server
// checks the same permission on every request, whatever the browser shows.
function Protected({ permission, children }: { permission: string; children: ReactNode }) {
  const { state, can } = useAuth();
  const location = useLocation();
  if (state.status === "loading") {
    return <div className="grid min-h-screen place-items-center text-ink-3"><Loader2 className="animate-spin" aria-label="Loading" /></div>;
  }
  if (state.status !== "signed-in") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!can(permission)) {
    return (
      <main className="grid min-h-screen place-items-center px-4 text-center">
        <div>
          <h1 className="text-xl font-medium">This page is not available to your role</h1>
          <p className="mt-2 text-sm text-ink-2">Your role ({state.me.user.role}) does not include “{permission}”.</p>
          <Link to={can("chat:use") ? "/" : can("documents:read") ? "/admin" : "/login"}
                className="mt-4 inline-block text-sm text-accent hover:underline">Go to a page you can use</Link>
        </div>
      </main>
    );
  }
  return children;
}

// A rendering error shows a message instead of a blank page.
class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="grid min-h-screen place-items-center px-4 text-center">
        <div>
          <h1 className="text-xl font-medium">Something went wrong on this page</h1>
          <button type="button" onClick={() => window.location.reload()}
                  className="mt-4 rounded-lg bg-ink px-4 py-2 text-sm text-white">Reload</button>
        </div>
      </main>
    );
  }
}

export function AppRoutes() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Protected permission="chat:use"><AssistantPage /></Protected>} />
          <Route path="/admin" element={<Protected permission="documents:read"><AdminPage /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
