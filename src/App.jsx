import React, { useEffect, useState, useCallback } from 'react';
import Login from './components/Login';
import Register from './components/Register';
import LandingPage from './components/LandingPage';
import StudentDashboard from './components/StudentDashboard';
import AdminLogin from './components/AdminLogin';
import AdminInviteSetup from './components/AdminInviteSetup';
import AdminDashboard from './components/AdminDashboard';
import RequireAdmin from './components/RequireAdmin';
import RequireStudent from './components/RequireStudent';
import GuestOnly from './components/GuestOnly';

// ─── Lightweight client-side router ──────────────────────────────────────────
function getPath() {
  return window.location.pathname || '/';
}

function readUser() {
  try {
    const raw = localStorage.getItem('currentUser');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('cm_theme') || 'dark');
  const [path, setPath]   = useState(getPath);
  // Keep user in React state so logout triggers a clean re-render
  const [_user, setUser]   = useState(readUser);

  // ── Navigation helper ─────────────────────────────────────────────────────
  const navigate = useCallback((to) => {
    if (to.startsWith('#')) return;
    window.history.pushState({}, '', to);
    setPath(to);
  }, []);

  // ── Logout helper — clears auth, terminates server session, hard-navigates ──
  const logout = useCallback(() => {
    // Terminate cookies on server (fire-and-forget)
    fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    fetch('/api/auth/admin/logout', { method: 'POST', credentials: 'include' }).catch(() => {});

    localStorage.removeItem('currentUser');
    setUser(null);          // clear React state immediately
    window.history.replaceState({}, '', '/login');
    setPath('/login');
  }, []);

  // Handle browser back/forward
  useEffect(() => {
    const onPop = () => setPath(getPath());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  // ── Theme effect ─────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light');
    localStorage.setItem('cm_theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((p) => (p === 'dark' ? 'light' : 'dark'));

  // ── After login: sync React user state from localStorage ─────────────────
  const handleLoginSuccess = useCallback(() => {
    setUser(readUser());
  }, []);

  // ── Resolve path ─────────────────────────────────────────────────────────
  // Admin invite emails link to /portal/invite/<token>; the setup screen reads the token from the URL.
  const resolvedPath = path.startsWith('/portal/invite/') ? '/portal/invite-setup' : path;

  // ── Route → Component ────────────────────────────────────────────────────
  const renderPage = () => {
    switch (resolvedPath) {
      case '/':
        return <LandingPage navigate={navigate} theme={theme} toggleTheme={toggleTheme} />;

      case '/login':
        return (
          <GuestOnly navigate={navigate}>
            <Login
              navigate={navigate}
              theme={theme}
              toggleTheme={toggleTheme}
              onLoginSuccess={handleLoginSuccess}
            />
          </GuestOnly>
        );

      case '/register':
        return (
          <GuestOnly navigate={navigate}>
            <Register navigate={navigate} theme={theme} toggleTheme={toggleTheme} />
          </GuestOnly>
        );

      case '/dashboard/student':
        return (
          <RequireStudent navigate={navigate} logout={logout}>
            <StudentDashboard
              navigate={navigate}
              logout={logout}
              theme={theme}
              toggleTheme={toggleTheme}
            />
          </RequireStudent>
        );

      case '/dashboard/admin':
        return (
          <RequireAdmin navigate={navigate}>
            <AdminDashboard
              navigate={navigate}
              logout={logout}
              theme={theme}
              toggleTheme={toggleTheme}
            />
          </RequireAdmin>
        );

      case '/portal/login':
        return (
          <GuestOnly navigate={navigate}>
            <AdminLogin navigate={navigate} theme={theme} toggleTheme={toggleTheme} onLoginSuccess={handleLoginSuccess} />
          </GuestOnly>
        );

      case '/portal/invite-setup':
        return <AdminInviteSetup navigate={navigate} theme={theme} toggleTheme={toggleTheme} />;

      default:
        navigate('/login');
        return null;
    }
  };

  return (
    <div className="min-h-screen w-screen bg-page text-text-primary selection:bg-accent/20 tracking-tight antialiased">
      {renderPage()}
    </div>
  );
}
