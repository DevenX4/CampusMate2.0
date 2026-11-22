import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { adminFetch } from './api';
import { TABLE_META } from './catalogMeta';

const CatalogCtx = createContext(null);

export function CatalogProvider({ children }) {
    const [summary, setSummary] = useState({ status: 'loading', data: null, error: '' });
    const [tables, setTables] = useState({});
    const [selection, setSelection] = useState(null);
    const inflight = useRef(new Map());

    const loadSummary = useCallback(async () => {
        setSummary((prev) => ({ ...prev, status: 'loading', error: '' }));
        try {
            const res = await adminFetch('/api/admin/catalog');
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.message || 'The data catalog could not be loaded.');
            setSummary({ status: 'ready', data, error: '' });
        } catch (error) {
            setSummary({ status: 'error', data: null, error: error.message || 'The data catalog could not be loaded.' });
        }
    }, []);

    useEffect(() => { loadSummary(); }, [loadSummary]);

    const loadTable = useCallback((name, force = false) => {
        if (!force && inflight.current.has(name)) return inflight.current.get(name);
        setTables((prev) => ({ ...prev, [name]: { status: 'loading', records: [], error: '' } }));
        const request = (async () => {
            try {
                const res = await adminFetch(`/api/admin/catalog/${encodeURIComponent(name)}`);
                const data = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(data.message || 'This dataset could not be loaded.');
                setTables((prev) => ({ ...prev, [name]: { status: 'ready', records: data.records || [], note: data.note, error: '' } }));
            } catch (error) {
                inflight.current.delete(name);
                setTables((prev) => ({ ...prev, [name]: { status: 'error', records: [], error: error.message || 'This dataset could not be loaded.' } }));
            }
        })();
        inflight.current.set(name, request);
        return request;
    }, []);

    const entityIndex = useMemo(() => {
        const index = new Map();
        for (const [name, state] of Object.entries(tables)) {
            if (state.status !== 'ready') continue;
            const idKey = TABLE_META[name]?.id;
            if (!idKey) continue;
            for (const record of state.records) {
                const id = record?.[idKey];
                if (id && (!index.has(id) || name === 'department_directory')) index.set(id, { table: name, record });
            }
        }
        return index;
    }, [tables]);

    const openRecord = useCallback((table, record) => setSelection({ table, record }), []);
    const closeRecord = useCallback(() => setSelection(null), []);

    const value = useMemo(() => ({
        summary, loadSummary, tables, loadTable, entityIndex, selection, openRecord, closeRecord,
    }), [summary, loadSummary, tables, loadTable, entityIndex, selection, openRecord, closeRecord]);

    return <CatalogCtx.Provider value={value}>{children}</CatalogCtx.Provider>;
}

export function useCatalog() {
    return useContext(CatalogCtx);
}

/** Loads the named datasets and reports one combined loading and error state. */
export function useTables(names) {
    const { tables, loadTable } = useCatalog();
    const key = names.join('|');

    useEffect(() => {
        key.split('|').filter(Boolean).forEach((name) => loadTable(name));
    }, [key, loadTable]);

    const data = useMemo(() => {
        const out = {};
        key.split('|').filter(Boolean).forEach((name) => { out[name] = tables[name]?.records || []; });
        return out;
    }, [key, tables]);

    const states = key.split('|').filter(Boolean).map((name) => tables[name]);
    const error = states.find((state) => state?.status === 'error')?.error || '';
    const loading = !error && states.some((state) => !state || state.status === 'loading');

    const retry = useCallback(() => {
        key.split('|').filter(Boolean).forEach((name) => {
            if (tables[name]?.status === 'error') loadTable(name, true);
        });
    }, [key, tables, loadTable]);

    return { data, loading, error, retry };
}
