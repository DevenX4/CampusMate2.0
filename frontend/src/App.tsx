import { Loader2 } from "lucide-react";
import { Component, type ReactNode } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router";

import { AdminLayout } from "./admin/AdminLayout";
import { DashboardPage, DocumentsPage } from "./admin/DashboardPage";
import { AnalyticsPage, IngestionPage, SettingsPage, UsersPage } from "./admin/OpsPages";
import { AuthProvider, homeFor, useAuth } from "./auth";
import { LoginPage } from "./LoginPage";
import { AssistantPage } from "./student/AssistantPage";
import { CurriculumPage } from "./student/CurriculumPage";
import { CalendarPage, FacultyPage, PoliciesPage } from "./student/DirectoryPages";
import { StudentLayout } from "./student/StudentLayout";
import { ThemeProvider } from "./theme";

// Shows a page only to users whose role has the permission. This is a convenience: the server
// checks the same permission on every request, whatever the browser shows.
function Protected({ permission, children }: { permission: string; children: ReactNode }) {
  const { state, me, can } = useAuth();
  const location = useLocation();
  if (state.status === "loading") {
    return <div className="grid min-h-screen place-items-center text-ink-3"><Loader2 className="animate-spin" aria-label="Loading" /></div>;
  }
  if (state.status !== "signed-in") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!can(permission)) {
    return (
      <main className="grid min-h-screen place-items-center px-4 text-center">
        <div>
          <h1 className="text-xl font-bold text-ink">This page is not available to your role</h1>
          <p className="mt-2 text-sm text-ink-3">Your role ({state.me.user.role}) does not include “{permission}”.</p>
          <Link to={homeFor(me)} className="mt-4 inline-block text-sm font-semibold text-blue-600 hover:underline">Go to a page you can use</Link>
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
          <h1 className="text-xl font-bold text-ink">Something went wrong on this page</h1>
          <button type="button" onClick={() => window.location.reload()} className="mt-4 rounded-xl bg-solid px-4 py-2 text-sm text-solid-ink">Reload</button>
        </div>
      </main>
    );
  }
}

export function AppRoutes() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<Protected permission="chat:use"><StudentLayout /></Protected>}>
              <Route index element={<AssistantPage />} />
              <Route path="curriculum" element={<CurriculumPage />} />
              <Route path="faculty" element={<FacultyPage />} />
              <Route path="calendar" element={<CalendarPage />} />
              <Route path="policies" element={<PoliciesPage />} />
            </Route>
            <Route path="/admin" element={<Protected permission="documents:read"><AdminLayout /></Protected>}>
              <Route index element={<DashboardPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="ingestion" element={<Protected permission="ingestion:manage"><IngestionPage /></Protected>} />
              <Route path="analytics" element={<Protected permission="audit:read"><AnalyticsPage /></Protected>} />
              <Route path="users" element={<Protected permission="users:manage"><UsersPage /></Protected>} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
