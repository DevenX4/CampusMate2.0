import { useEffect, useState } from 'react';
import CampyLoader from './auth/CampyLoader';

export default function GuestOnly({ children, navigate }) {
    const [checking, setChecking] = useState(true);

    useEffect(() => {
        let isMounted = true;

        const checkAuthenticatedGuest = async () => {
            try {
                const storedUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
                if (storedUser && storedUser.role && storedUser.token) {
                    const headers = { 
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${storedUser.token}`
                    };
                    const endpoint = storedUser.role === 'admin' ? '/api/admin/verify' : '/api/auth/verify';
                    
                    const res = await fetch(endpoint, {
                        method: 'GET',
                        headers,
                        credentials: 'include'
                    });

                    if (res.ok) {
                        const data = await res.json();
                        if (isMounted && data.authenticated) {
                            const targetPath = storedUser.role === 'admin' ? '/dashboard/admin' : '/dashboard/student';
                            window.history.replaceState({}, '', targetPath);
                            navigate(targetPath);
                            return;
                        }
                    } else {
                        // Stale/invalid token in localStorage - clean up
                        localStorage.removeItem('currentUser');
                    }
                }
            } catch {
                // Network error or offline - fall through to display login page
            }

            if (isMounted) {
                setChecking(false);
            }
        };

        checkAuthenticatedGuest();

        return () => {
            isMounted = false;
        };
    }, [navigate]);

    if (checking) {
        return <CampyLoader label="Checking your session" />;
    }

    return children;
}
