import { useEffect, useState } from 'react';
import CampyLoader from './auth/CampyLoader';

export default function RequireAdmin({ children, navigate }) {
    const [isAuthenticated, setIsAuthenticated] = useState(null);

    useEffect(() => {
        let isMounted = true;

        const verifyAdminSession = async () => {
            try {
                // Check localStorage token first as a fast path
                const storedUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
                const token = storedUser?.token;

                const headers = { 'Content-Type': 'application/json' };
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }

                const res = await fetch('/api/admin/verify', {
                    method: 'GET',
                    headers,
                    credentials: 'include' // send httpOnly cookies
                });

                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        setIsAuthenticated(true);
                        // Preserve stored user data but ensure role/auth fields are consistent
                        const existing = JSON.parse(localStorage.getItem('currentUser') || '{}');
                        localStorage.setItem('currentUser', JSON.stringify({
                            ...existing,
                            email: data.user.email,
                            role: 'admin',
                            department: existing.department || 'Administration',
                            name: existing.name || data.user.email.split('@')[0],
                            token: existing.token, // preserve the JWT token
                        }));
                    }
                } else {
                    if (isMounted) {
                        setIsAuthenticated(false);
                        localStorage.removeItem('currentUser');
                        navigate('/portal/login');
                    }
                }
            } catch (err) {
                if (isMounted) {
                    setIsAuthenticated(false);
                    navigate('/portal/login');
                }
            }
        };

        verifyAdminSession();

        return () => {
            isMounted = false;
        };
    }, [navigate]);

    if (isAuthenticated === null) {
        // Prevent layout flash/briefly rendering protected content before redirecting
        return <CampyLoader label="Verifying admin access" />;
    }

    return isAuthenticated ? children : null;
}
