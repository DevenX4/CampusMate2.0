import { useEffect, useState } from 'react';
import CampyLoader from './auth/CampyLoader';

export default function RequireStudent({ children, navigate, logout }) {
    const [isAuthenticated, setIsAuthenticated] = useState(null);

    useEffect(() => {
        let isMounted = true;

        const verifyStudentSession = async () => {
            try {
                const storedUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
                const token = storedUser?.token;

                if (!storedUser || storedUser.role !== 'student') {
                    if (isMounted) {
                        setIsAuthenticated(false);
                        if (logout) logout();
                        else {
                            localStorage.removeItem('currentUser');
                            window.history.replaceState({}, '', '/login');
                            navigate('/login');
                        }
                    }
                    return;
                }

                const headers = { 'Content-Type': 'application/json' };
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }

                const res = await fetch('/api/auth/verify', {
                    method: 'GET',
                    headers,
                    credentials: 'include'
                });

                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        setIsAuthenticated(true);
                        // Sync verified user data back into localStorage
                        const existing = JSON.parse(localStorage.getItem('currentUser') || '{}');
                        localStorage.setItem('currentUser', JSON.stringify({
                            ...existing,
                            name: data.user.name || existing.name,
                            email: data.user.email,
                            role: 'student',
                            department: data.user.department || existing.department,
                            semester: data.user.semester || existing.semester,
                            token: existing.token,
                        }));
                    }
                } else {
                    if (isMounted) {
                        setIsAuthenticated(false);
                        localStorage.removeItem('currentUser');
                        window.history.replaceState({}, '', '/login');
                        if (logout) logout();
                        else navigate('/login');
                    }
                }
            } catch (err) {
                if (isMounted) {
                    setIsAuthenticated(false);
                    localStorage.removeItem('currentUser');
                    window.history.replaceState({}, '', '/login');
                    if (logout) logout();
                    else navigate('/login');
                }
            }
        };

        verifyStudentSession();

        return () => {
            isMounted = false;
        };
    }, [navigate, logout]);

    if (isAuthenticated === null) {
        return <CampyLoader label="Opening your dashboard" />;
    }

    return isAuthenticated ? children : null;
}
