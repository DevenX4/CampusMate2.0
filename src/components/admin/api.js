export function authHeaders() {
    try {
        const u = JSON.parse(localStorage.getItem('currentUser') || '{}');
        return u.token
            ? { 'Content-Type': 'application/json', Authorization: `Bearer ${u.token}` }
            : { 'Content-Type': 'application/json' };
    } catch { return { 'Content-Type': 'application/json' }; }
}

export function adminFetch(url, options = {}) {
    return fetch(url, {
        ...options,
        credentials: 'include',
        headers: { ...authHeaders(), ...(options.headers || {}) },
    });
}

export function timeAgo(date) {
    const s = (Date.now() - new Date(date)) / 1000;
    if (s < 60) return `${Math.floor(s)}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
}

export function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
