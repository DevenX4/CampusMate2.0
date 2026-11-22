import { useDeferredValue, useMemo, useState } from 'react';
import { useCatalog, useTables } from './CatalogContext';
import { countBy, humanValue, matchesQuery } from './catalogMeta';
import { DataBoundary, DataTable, EmptyState, FilterChips, SearchField, SourceTag, Tabs } from './ui';

const TABLES = ['buildings', 'rooms', 'laboratories', 'facilities', 'faculty'];

function Buildings({ data, openRecord }) {
    const [buildingId, setBuildingId] = useState(null);
    const [roomType, setRoomType] = useState('all');
    const [query, setQuery] = useState('');
    const deferred = useDeferredValue(query);

    const roomCounts = useMemo(() => countBy(data.rooms, (row) => row.building_id), [data.rooms]);
    const building = data.buildings.find((row) => row.building_id === buildingId) || data.buildings[0];
    const buildingRooms = useMemo(() => data.rooms.filter((row) => row.building_id === building?.building_id), [data.rooms, building]);
    const typeCounts = useMemo(() => countBy(buildingRooms, (row) => row.room_type), [buildingRooms]);

    const floors = useMemo(() => {
        const visible = buildingRooms.filter((row) => (roomType === 'all' || row.room_type === roomType) && matchesQuery(row, deferred.trim()));
        const map = new Map();
        for (const row of visible) {
            if (!map.has(row.floor)) map.set(row.floor, []);
            map.get(row.floor).push(row);
        }
        return [...map.entries()].sort((a, b) => a[0] - b[0]).map(([floor, rooms]) => ({
            floor,
            rooms: rooms.sort((a, b) => String(a.room_number).localeCompare(String(b.room_number), undefined, { numeric: true })),
        }));
    }, [buildingRooms, roomType, deferred]);

    if (!building) return <div className="adm-panel"><EmptyState title="No buildings in the data" /></div>;

    return (
        <div className="adm-grid-2 adm-grid-side">
            <section className="adm-panel self-start">
                <div className="adm-panel-head"><h2>Buildings</h2><span className="adm-nav-count">{data.buildings.length}</span></div>
                {data.buildings.map((row) => (
                    <button
                        key={row.building_id}
                        type="button"
                        className="adm-list-btn"
                        aria-pressed={row.building_id === building.building_id}
                        onClick={() => { setBuildingId(row.building_id); setRoomType('all'); }}
                    >
                        <span className="min-w-0 flex-1">
                            <span className="adm-list-title">{row.name}</span>
                            <span className="block text-xs adm-muted">{row.floors} floors, {roomCounts[row.building_id] || 0} rooms listed</span>
                        </span>
                        <SourceTag type={row.source_type} />
                    </button>
                ))}
            </section>

            <section className="adm-panel min-w-0">
                <div className="adm-panel-head">
                    <h2>{building.name}</h2>
                    <button type="button" className="adm-btn" style={{ height: 24, fontSize: 12 }} onClick={() => openRecord('buildings', building)}>Details</button>
                </div>
                <div className="adm-panel-body flex flex-col gap-2" style={{ paddingBottom: 8 }}>
                    {building.description && <p className="m-0 adm-secondary">{building.description}</p>}
                    <div className="adm-toolbar">
                        <SearchField value={query} onChange={setQuery} placeholder="Search rooms" />
                    </div>
                    <FilterChips
                        label="Filter by room type"
                        active={roomType}
                        onChange={setRoomType}
                        options={[
                            { id: 'all', label: 'All', count: buildingRooms.length },
                            ...Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => ({ id: type, label: humanValue(type), count })),
                        ]}
                    />
                </div>
                {floors.length === 0 ? <EmptyState title="No rooms match" /> : (
                    <div className="adm-table-wrap">
                        <table className="adm-table">
                            <thead>
                                <tr><th>Room</th><th>Name</th><th className="adm-hide-sm">Type</th><th className="adm-hide-sm">Source</th></tr>
                            </thead>
                            <tbody>
                                {floors.map(({ floor, rooms }) => (
                                    <FloorRows key={floor} floor={floor} rooms={rooms} onOpen={(room) => openRecord('rooms', room)} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </div>
    );
}

function FloorRows({ floor, rooms, onOpen }) {
    return (
        <>
            <tr className="adm-group-row">
                <td colSpan={4}>Floor {floor} <span className="adm-muted font-normal">{rooms.length} {rooms.length === 1 ? 'room' : 'rooms'}</span></td>
            </tr>
            {rooms.map((room) => (
                <tr key={room.room_id} data-click="true" tabIndex={0} onClick={() => onOpen(room)} onKeyDown={(e) => { if (e.key === 'Enter') onOpen(room); }}>
                    <td className="adm-mono adm-strong whitespace-nowrap">{room.room_number}</td>
                    <td className="adm-strong">{room.label}</td>
                    <td className="adm-hide-sm"><span className="adm-tag">{humanValue(room.room_type)}</span></td>
                    <td className="adm-hide-sm"><SourceTag type={room.source_type} /></td>
                </tr>
            ))}
        </>
    );
}

function Laboratories({ data, openRecord }) {
    const [query, setQuery] = useState('');
    const deferred = useDeferredValue(query);
    const people = useMemo(() => new Map(data.faculty.map((row) => [row.faculty_id, row.name])), [data.faculty]);
    const rows = useMemo(() => data.laboratories.filter((row) => matchesQuery(row, deferred.trim())), [data.laboratories, deferred]);
    const columns = useMemo(() => [
        { key: 'lab_name', label: 'Laboratory', strong: true, clip: true },
        { key: 'room_number', label: 'Room', mono: true },
        { key: 'capacity', label: 'Seats', numeric: true },
        { key: 'responsible', label: 'In charge', hide: 'sm', clip: true, value: (row) => people.get(row.responsible_faculty_id) || row.responsible_faculty_id },
        { key: 'opening_hours', label: 'Hours', hide: 'md', clip: true },
        { key: 'source_type', label: 'Source', hide: 'sm', render: (row) => <SourceTag type={row.source_type} /> },
    ], [people]);
    return (
        <>
            <div className="adm-toolbar"><SearchField value={query} onChange={setQuery} placeholder="Search labs or equipment" /></div>
            <section className="adm-panel">
                <DataTable columns={columns} rows={rows} rowKey={(row) => row.lab_id} onRowClick={(row) => openRecord('laboratories', row)} />
            </section>
        </>
    );
}

function Facilities({ data, openRecord }) {
    const [query, setQuery] = useState('');
    const deferred = useDeferredValue(query);
    const rows = useMemo(() => data.facilities.filter((row) => matchesQuery(row, deferred.trim())), [data.facilities, deferred]);
    const columns = useMemo(() => [
        { key: 'facility_name', label: 'Facility', strong: true, clip: true },
        { key: 'facility_type', label: 'Type', hide: 'sm', render: (row) => <span className="adm-tag">{humanValue(row.facility_type)}</span> },
        { key: 'location', label: 'Location', hide: 'md', clip: true, clipClass: 'adm-clip-sm' },
        { key: 'capacity', label: 'Capacity', numeric: true },
        { key: 'availability', label: 'Availability', hide: 'md', clip: true, clipClass: 'adm-clip-sm' },
        { key: 'source_type', label: 'Source', hide: 'sm', render: (row) => <SourceTag type={row.source_type} /> },
    ], []);
    return (
        <>
            <div className="adm-toolbar"><SearchField value={query} onChange={setQuery} placeholder="Search facilities" /></div>
            <section className="adm-panel">
                <DataTable columns={columns} rows={rows} rowKey={(row) => row.facility_id} onRowClick={(row) => openRecord('facilities', row)} />
            </section>
        </>
    );
}

export default function CampusView() {
    const { openRecord } = useCatalog();
    const { data, loading, error, retry } = useTables(TABLES);
    const [tab, setTab] = useState('buildings');

    return (
        <>
            <p className="adm-page-desc">Buildings and their rooms, teaching laboratories and shared facilities.</p>
            <Tabs
                label="Campus"
                active={tab}
                onChange={setTab}
                tabs={[
                    { id: 'buildings', label: 'Buildings and rooms', count: loading ? undefined : data.rooms.length },
                    { id: 'labs', label: 'Laboratories', count: loading ? undefined : data.laboratories.length },
                    { id: 'facilities', label: 'Facilities', count: loading ? undefined : data.facilities.length },
                ]}
            />
            <DataBoundary loading={loading} error={error} retry={retry}>
                {tab === 'buildings' && <Buildings data={data} openRecord={openRecord} />}
                {tab === 'labs' && <Laboratories data={data} openRecord={openRecord} />}
                {tab === 'facilities' && <Facilities data={data} openRecord={openRecord} />}
            </DataBoundary>
        </>
    );
}
