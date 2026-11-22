import CampusBot from '../brand/CampusBot';
import './auth.css';

export default function CampyLoader({ label = 'Checking your session' }) {
    return (
        <div className="campy-loader font-sans" role="status" aria-live="polite">
            <CampusBot size={56} mood="searching" title="Campy is checking" />
            <p className="m-0">{label}</p>
        </div>
    );
}
