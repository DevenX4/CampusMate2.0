import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, FileCode, FileSpreadsheet, FileText, Image as ImageIcon, Loader2, Plus, RefreshCw, Trash2, UploadCloud } from 'lucide-react';
import { adminFetch, formatBytes, timeAgo } from './api';
import { useCatalog } from './CatalogContext';
import { DataTable, EmptyState, StatStrip, StatusTag, TableSkeleton } from './ui';

function getFileIcon(mime = '') {
    if (mime.includes('pdf') || mime.includes('word')) return FileText;
    if (mime.includes('csv') || mime.includes('sheet')) return FileSpreadsheet;
    if (mime.includes('json') || mime.includes('text') || mime.includes('markdown')) return FileCode;
    if (mime.includes('image')) return ImageIcon;
    return FileText;
}

const STATUS_ICON = {
    indexed: <CheckCircle2 size={10} />,
    processing: <Loader2 size={10} className="animate-spin" />,
    error: <AlertTriangle size={10} />,
    pending: <Clock size={10} />,
};

export default function KnowledgeSection({ onChanged }) {
    const { summary } = useCatalog();
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedFile, setSelectedFile] = useState(null);
    const [description, setDescription] = useState('');
    const [dragActive, setDragActive] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadMsg, setUploadMsg] = useState({ type: '', text: '' });
    const [deleteConfirm, setDeleteConfirm] = useState(null);
    const fileInputRef = useRef(null);

    const loadFiles = useCallback(async () => {
        setLoading(true);
        try {
            const res = await adminFetch('/api/admin/knowledge/files');
            if (res.ok) setFiles((await res.json()).files || []);
        } catch { /* noop */ }
        setLoading(false);
    }, []);

    useEffect(() => { loadFiles(); }, [loadFiles]);

    const handleDrop = (e) => {
        e.preventDefault(); e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) { setSelectedFile(e.dataTransfer.files[0]); setUploadMsg({ type: '', text: '' }); }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!selectedFile) return;
        setUploading(true); setUploadMsg({ type: '', text: '' });
        try {
            const u = JSON.parse(localStorage.getItem('currentUser') || '{}');
            const fd = new FormData();
            fd.append('file', selectedFile);
            if (description.trim()) fd.append('description', description.trim());
            const res = await fetch('/api/admin/knowledge/upload', {
                method: 'POST',
                credentials: 'include',
                headers: u.token ? { Authorization: `Bearer ${u.token}` } : {},
                body: fd
            });
            const d = await res.json();
            if (res.ok) {
                setUploadMsg({ type: 'success', text: `"${selectedFile.name}" uploaded and queued for AI indexing.` });
                setSelectedFile(null); setDescription('');
                if (fileInputRef.current) fileInputRef.current.value = '';
                loadFiles();
                if (onChanged) onChanged();
            } else {
                setUploadMsg({ type: 'error', text: d.message || 'Upload failed.' });
            }
        } catch { setUploadMsg({ type: 'error', text: 'Network error during upload.' }); }
        setUploading(false);
    };

    const handleDelete = useCallback(async (id) => {
        try {
            const res = await adminFetch(`/api/admin/knowledge/${id}`, { method: 'DELETE' });
            if (res.ok) { setDeleteConfirm(null); loadFiles(); if (onChanged) onChanged(); }
            else { const d = await res.json(); alert(d.message); }
        } catch { /* noop */ }
    }, [loadFiles, onChanged]);

    const columns = useMemo(() => [
        {
            key: 'originalName', label: 'File', strong: true,
            render: (f) => {
                const FileIcon = getFileIcon(f.mimeType);
                return (
                    <span className="flex min-w-0 items-center gap-2">
                        <FileIcon size={14} className="shrink-0 adm-muted" />
                        <span className="adm-clip">{f.originalName}</span>
                    </span>
                );
            },
        },
        { key: 'description', label: 'Label', hide: 'md', clip: true },
        { key: 'size', label: 'Size', numeric: true, hide: 'sm', render: (f) => formatBytes(f.size) },
        { key: 'uploadedAt', label: 'Uploaded', hide: 'sm', mono: true, render: (f) => timeAgo(f.uploadedAt) },
        {
            key: 'status', label: 'Status',
            render: (f) => <StatusTag status={f.status || 'pending'}>{STATUS_ICON[f.status]} {f.status}</StatusTag>,
        },
        {
            key: 'actions', label: '', sortable: false,
            render: (f) => (deleteConfirm === f._id ? (
                <span className="flex items-center gap-1">
                    <button type="button" onClick={() => handleDelete(f._id)} className="adm-btn adm-btn-danger-solid" style={{ height: 26 }}>Delete</button>
                    <button type="button" onClick={() => setDeleteConfirm(null)} className="adm-btn" style={{ height: 26 }}>Cancel</button>
                </span>
            ) : (
                <button type="button" onClick={() => setDeleteConfirm(f._id)} className="adm-icon-btn" style={{ width: 26, height: 26 }} aria-label={`Delete ${f.originalName}`}>
                    <Trash2 size={12} />
                </button>
            )),
        },
    ], [deleteConfirm, handleDelete]);

    const knowledge = summary.data?.knowledgeIndex;

    return (
        <>
            <p className="adm-page-desc">
                Upload campus documents such as syllabi, exam schedules and notices. Files are stored and queued for indexing, and the status column shows where each one stands.
            </p>

            <StatStrip items={[
                { label: 'Knowledge index', value: knowledge?.total, sub: 'Entries the assistant can search' },
                { label: 'Uploaded files', value: loading ? null : files.length, sub: 'In this workspace' },
                { label: 'Indexed uploads', value: loading ? null : files.filter((f) => f.status === 'indexed').length, sub: 'Ready for retrieval' },
            ]} />

            <section className="adm-panel">
                <div className="adm-panel-head"><h2>Upload document</h2></div>
                <div className="adm-panel-body flex flex-col gap-2.5">
                    {uploadMsg.text && (
                        <p className="adm-msg" data-tone={uploadMsg.type === 'success' ? 'success' : 'error'} role="status">
                            {uploadMsg.type === 'success' ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                            {uploadMsg.text}
                        </p>
                    )}
                    <form onSubmit={handleUpload} className="flex flex-col gap-2.5">
                        <div
                            className="adm-drop"
                            data-active={dragActive}
                            data-file={Boolean(selectedFile)}
                            role="button"
                            tabIndex={0}
                            aria-label="Choose a file to upload"
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputRef.current?.click(); } }}
                            onDragEnter={e => { e.preventDefault(); setDragActive(true); }}
                            onDragLeave={e => { e.preventDefault(); setDragActive(false); }}
                            onDragOver={e => e.preventDefault()}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                className="hidden"
                                accept=".pdf,.docx,.doc,.txt,.md,.csv,.json,image/jpeg,image/png,image/webp"
                                onClick={(e) => e.stopPropagation()}
                                onChange={e => { if (e.target.files?.[0]) { setSelectedFile(e.target.files[0]); setUploadMsg({ type: '', text: '' }); } }}
                            />
                            {selectedFile ? (
                                <>
                                    <FileText size={20} className="text-status-success" />
                                    <span className="font-medium text-text-primary">{selectedFile.name}</span>
                                    <span className="text-xs adm-muted">{formatBytes(selectedFile.size)}, click to change</span>
                                </>
                            ) : (
                                <>
                                    <UploadCloud size={20} className="text-accent" />
                                    <span className="font-medium text-text-primary">Click to select, or drag and drop</span>
                                    <span className="text-xs adm-muted">PDF, DOCX, TXT, MD, CSV, JSON, PNG, JPG up to 20MB</span>
                                </>
                            )}
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <label htmlFor="adm-file-label" className="sr-only">Optional label</label>
                            <input
                                id="adm-file-label"
                                type="text"
                                value={description}
                                onChange={e => setDescription(e.target.value)}
                                placeholder="Optional label, for example Exam Schedule 2026"
                                className="adm-input"
                                style={{ flex: '1 1 240px', width: 'auto' }}
                            />
                            <button type="submit" disabled={uploading || !selectedFile} className="adm-btn adm-btn-primary">
                                {uploading ? <><Loader2 size={13} className="animate-spin" /> Uploading</> : <><Plus size={13} /> Upload</>}
                            </button>
                        </div>
                    </form>
                </div>
            </section>

            <section className="adm-panel">
                <div className="adm-panel-head">
                    <h2>Knowledge documents</h2>
                    <span className="adm-nav-count">{files.length}</span>
                    <span className="adm-spacer" />
                    <button type="button" onClick={loadFiles} className="adm-icon-btn" style={{ width: 26, height: 26 }} aria-label="Refresh documents" title="Refresh"><RefreshCw size={12} /></button>
                </div>
                {loading ? <TableSkeleton rows={3} columns={5} />
                    : files.length === 0 ? <EmptyState title="No documents uploaded yet" icon={UploadCloud}>Uploaded files will appear here with their indexing status.</EmptyState>
                        : <DataTable columns={columns} rows={files} rowKey={(f) => f._id} />}
            </section>
        </>
    );
}
