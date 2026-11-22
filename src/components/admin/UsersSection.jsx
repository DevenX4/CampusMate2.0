import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Check, Copy, Eye, EyeOff, KeyRound, Loader2, Plus, RefreshCw, Trash2, UserCheck } from 'lucide-react';
import { adminFetch, timeAgo } from './api';
import { DataTable, Drawer, EmptyState, FilterChips, SearchField, TableSkeleton } from './ui';

const ROLE_TONE = { admin: 'accent', student: 'success', teacher: 'warning' };

function RoleTag({ role }) {
    return <span className="adm-tag" data-tone={ROLE_TONE[role] || 'neutral'}>{role}</span>;
}

function VerifiedTag({ verified }) {
    return verified
        ? <span className="adm-tag" data-tone="success"><UserCheck size={11} /> Verified</span>
        : <span className="adm-tag" data-tone="warning"><AlertTriangle size={11} /> Pending</span>;
}

function UserDrawer({ user, onClose, onRefresh }) {
    const [newPassword, setNewPassword] = useState('');
    const [showPw, setShowPw] = useState(false);
    const [pwLoading, setPwLoading] = useState(false);
    const [pwMsg, setPwMsg] = useState({ type: '', text: '' });
    const [verifyLoading, setVerifyLoading] = useState(false);
    const [verifyMsg, setVerifyMsg] = useState('');
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState(false);
    const [isVerified, setIsVerified] = useState(user.isVerified);

    const handleResetPassword = async (e) => {
        e.preventDefault();
        setPwLoading(true); setPwMsg({ type: '', text: '' });
        try {
            const res = await adminFetch(`/api/admin/users/${user._id}/password`, {
                method: 'PATCH',
                body: JSON.stringify({ newPassword })
            });
            const d = await res.json();
            if (res.ok) { setPwMsg({ type: 'success', text: d.message }); setNewPassword(''); }
            else setPwMsg({ type: 'error', text: d.message });
        } catch { setPwMsg({ type: 'error', text: 'Network error.' }); }
        setPwLoading(false);
    };

    const handleToggleVerify = async () => {
        setVerifyLoading(true); setVerifyMsg('');
        try {
            const res = await adminFetch(`/api/admin/users/${user._id}/verify`, { method: 'PATCH' });
            const d = await res.json();
            if (res.ok) { setIsVerified(d.isVerified); setVerifyMsg(d.message); onRefresh(); }
            else setVerifyMsg(d.message);
        } catch { setVerifyMsg('Network error.'); }
        setVerifyLoading(false);
    };

    const handleDelete = async () => {
        setDeleteLoading(true);
        try {
            const res = await adminFetch(`/api/admin/users/${user._id}`, { method: 'DELETE' });
            const d = await res.json();
            if (res.ok) { onRefresh(); onClose(); }
            else { setDeleteConfirm(false); setDeleteLoading(false); alert(d.message); }
        } catch { setDeleteLoading(false); }
    };

    const details = [
        ['Role', <RoleTag key="r" role={user.role} />],
        ['Department', user.department || 'Not set'],
        ['Enrollment', user.enrollmentNumber || 'Not set'],
        ['Semester', user.semester || 'Not set'],
        ['Phone', user.phone || 'Not set'],
        ['Joined', user.createdAt ? timeAgo(user.createdAt) : 'Not set'],
        ['Last login', user.lastLogin ? timeAgo(user.lastLogin) : 'Never'],
        ['Status', <VerifiedTag key="s" verified={isVerified} />],
    ];

    return (
        <Drawer title={user.name} subtitle={user.email} onClose={onClose} labelledBy="adm-user-drawer-title">
            <section className="adm-drawer-section">
                <h3>Account details</h3>
                <dl className="adm-kv">
                    {details.map(([label, value]) => (
                        <div key={label} className="contents"><dt>{label}</dt><dd>{value}</dd></div>
                    ))}
                </dl>
            </section>

            <section className="adm-drawer-section">
                <h3>Reset password</h3>
                <form onSubmit={handleResetPassword} className="flex flex-col gap-2">
                    <label htmlFor="adm-new-password" className="text-xs text-text-secondary">New password (at least 8 characters)</label>
                    <div className="relative">
                        <input
                            id="adm-new-password"
                            type={showPw ? 'text' : 'password'}
                            value={newPassword}
                            onChange={e => setNewPassword(e.target.value)}
                            minLength={8}
                            required
                            className="adm-input"
                            style={{ paddingRight: 36 }}
                        />
                        <button type="button" onClick={() => setShowPw(p => !p)} className="adm-search-clear" aria-label={showPw ? 'Hide password' : 'Show password'}>
                            {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                    </div>
                    <button type="submit" disabled={pwLoading || newPassword.length < 8} className="adm-btn adm-btn-primary self-start">
                        {pwLoading ? <Loader2 size={13} className="animate-spin" /> : <KeyRound size={13} />} Reset password
                    </button>
                </form>
                {pwMsg.text && <p className="adm-msg mt-2" data-tone={pwMsg.type === 'success' ? 'success' : 'error'}>{pwMsg.text}</p>}
            </section>

            <section className="adm-drawer-section">
                <h3>Verification</h3>
                <div className="flex items-center justify-between gap-3">
                    <span className="adm-secondary">Currently {isVerified ? 'verified' : 'unverified'}</span>
                    <button type="button" onClick={handleToggleVerify} disabled={verifyLoading} className="adm-btn">
                        {verifyLoading ? <Loader2 size={13} className="animate-spin" />
                            : isVerified ? <><AlertTriangle size={13} /> Unverify</> : <><UserCheck size={13} /> Verify</>}
                    </button>
                </div>
                {verifyMsg && <p className="adm-msg adm-muted mt-2">{verifyMsg}</p>}
            </section>

            {user.role !== 'admin' && (
                <section className="adm-drawer-section">
                    <h3 style={{ color: 'var(--status-danger)' }}>Delete account</h3>
                    <p className="m-0 mb-2 adm-secondary">Permanently deletes this account. This cannot be undone.</p>
                    {!deleteConfirm
                        ? <button type="button" onClick={() => setDeleteConfirm(true)} className="adm-btn adm-btn-danger"><Trash2 size={13} /> Delete account</button>
                        : (
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="font-medium text-status-danger">Delete this account?</span>
                                <button type="button" onClick={handleDelete} disabled={deleteLoading} className="adm-btn adm-btn-danger-solid">
                                    {deleteLoading ? <Loader2 size={13} className="animate-spin" /> : 'Yes, delete'}
                                </button>
                                <button type="button" onClick={() => setDeleteConfirm(false)} className="adm-btn">Cancel</button>
                            </div>
                        )}
                </section>
            )}
        </Drawer>
    );
}

export default function UsersSection({ onChanged }) {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const [filter, setFilter] = useState('all');
    const [search, setSearch] = useState('');
    const [selectedUser, setSelectedUser] = useState(null);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteLoading, setInviteLoading] = useState(false);
    const [inviteResult, setInviteResult] = useState(null);
    const [inviteError, setInviteError] = useState('');
    const [copied, setCopied] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setLoadError('');
        try {
            const res = await adminFetch('/api/admin/users');
            if (res.ok) setUsers((await res.json()).users || []);
            else setLoadError('The user list could not be loaded.');
        } catch { setLoadError('The user list could not be loaded.'); }
        setLoading(false);
    }, []);

    useEffect(() => { load(); }, [load]);

    const closeDrawer = useCallback(() => setSelectedUser(null), []);
    const refreshFromDrawer = useCallback(() => {
        load();
        setSelectedUser(null);
        if (onChanged) onChanged();
    }, [load, onChanged]);

    const handleInvite = async (e) => {
        e.preventDefault();
        setInviteLoading(true); setInviteError(''); setInviteResult(null);
        try {
            const res = await adminFetch('/api/admin/invite', {
                method: 'POST', body: JSON.stringify({ email: inviteEmail })
            });
            const d = await res.json();
            if (res.ok) { setInviteResult(d); setInviteEmail(''); }
            else setInviteError(d.message || 'Failed.');
        } catch { setInviteError('Network error.'); }
        setInviteLoading(false);
    };

    const counts = {
        all: users.length,
        student: users.filter(u => u.role === 'student').length,
        teacher: users.filter(u => u.role === 'teacher').length,
        admin: users.filter(u => u.role === 'admin').length,
    };

    const filtered = useMemo(() => {
        const byRole = users.filter(u => filter === 'all' || u.role === filter);
        const q = search.trim().toLowerCase();
        return q ? byRole.filter(u => u.name?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q)) : byRole;
    }, [users, filter, search]);

    const columns = useMemo(() => [
        {
            key: 'name', label: 'User', strong: true,
            render: (u) => (
                <span className="flex min-w-0 items-center gap-2">
                    <span className="adm-avatar">{u.name?.charAt(0) || '?'}</span>
                    <span className="min-w-0">
                        <span className="block truncate font-medium text-text-primary">{u.name}</span>
                        <span className="block truncate adm-mono adm-muted" style={{ fontSize: 11 }}>{u.email}</span>
                    </span>
                </span>
            ),
        },
        { key: 'role', label: 'Role', render: (u) => <RoleTag role={u.role} /> },
        { key: 'department', label: 'Department', hide: 'md' },
        { key: 'isVerified', label: 'Status', hide: 'sm', render: (u) => <VerifiedTag verified={u.isVerified} /> },
        { key: 'lastLogin', label: 'Last login', hide: 'sm', mono: true, render: (u) => (u.lastLogin ? timeAgo(u.lastLogin) : 'Never') },
    ], []);

    return (
        <>
            <p className="adm-page-desc">View all users, verify accounts, reset passwords and invite admins.</p>

            <section className="adm-panel">
                <div className="adm-panel-head"><h2>Invite administrator</h2><span className="adm-muted text-xs">Sends a secure 2FA setup link to a @gnu.ac.in address</span></div>
                <div className="adm-panel-body">
                    <form onSubmit={handleInvite} className="flex flex-wrap items-center gap-2">
                        <label htmlFor="adm-invite-email" className="sr-only">Administrator email</label>
                        <input
                            id="adm-invite-email"
                            type="email"
                            value={inviteEmail}
                            onChange={e => setInviteEmail(e.target.value)}
                            placeholder="newadmin@gnu.ac.in"
                            required
                            className="adm-input"
                            style={{ flex: '1 1 220px', maxWidth: 380, width: 'auto' }}
                        />
                        <button type="submit" disabled={inviteLoading || !inviteEmail} className="adm-btn adm-btn-primary">
                            {inviteLoading ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} Send invite
                        </button>
                    </form>
                    {inviteError && <p className="adm-msg mt-2" data-tone="error">{inviteError}</p>}
                    {inviteResult && (
                        <div className="mt-2.5 flex items-start gap-2 rounded-md border border-status-success/30 bg-status-success/10 p-2.5">
                            <Check size={14} className="mt-0.5 shrink-0 text-status-success" />
                            <div className="min-w-0 flex-1">
                                <p className="m-0 text-xs font-medium text-status-success">Invite generated for {inviteResult.email}</p>
                                <div className="mt-1 flex items-center gap-2">
                                    <p className="m-0 min-w-0 flex-1 truncate adm-mono adm-muted">{inviteResult.inviteLink}</p>
                                    <button
                                        type="button"
                                        className="adm-icon-btn"
                                        style={{ width: 26, height: 26 }}
                                        aria-label="Copy invite link"
                                        onClick={() => { navigator.clipboard.writeText(inviteResult.inviteLink); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
                                    >
                                        {copied ? <Check size={12} className="text-status-success" /> : <Copy size={12} />}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </section>

            <section className="adm-panel">
                <div className="adm-panel-head">
                    <h2>All users</h2>
                    <span className="adm-nav-count">{filtered.length}</span>
                    <span className="adm-spacer" />
                    <FilterChips
                        label="Filter by role"
                        active={filter}
                        onChange={(value) => { setFilter(value); setSearch(''); }}
                        options={[
                            { id: 'all', label: 'All', count: counts.all },
                            { id: 'student', label: 'Students', count: counts.student },
                            { id: 'teacher', label: 'Teachers', count: counts.teacher },
                            { id: 'admin', label: 'Admins', count: counts.admin },
                        ]}
                    />
                    <button type="button" className="adm-icon-btn" style={{ width: 26, height: 26 }} onClick={load} aria-label="Refresh users" title="Refresh"><RefreshCw size={12} /></button>
                </div>
                <div className="adm-panel-body" style={{ paddingBottom: 8 }}>
                    <SearchField value={search} onChange={setSearch} placeholder="Search by name or email" />
                </div>
                {loading ? <TableSkeleton rows={5} columns={5} />
                    : loadError ? <EmptyState title={loadError}>Use refresh to try again.</EmptyState>
                        : <DataTable columns={columns} rows={filtered} rowKey={(u) => u._id} onRowClick={setSelectedUser} emptyTitle="No users match your filter" />}
            </section>

            {selectedUser && <UserDrawer key={selectedUser._id} user={selectedUser} onClose={closeDrawer} onRefresh={refreshFromDrawer} />}
        </>
    );
}
