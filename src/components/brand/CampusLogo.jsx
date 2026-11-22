import CampusBot from './CampusBot';

/** Still version of Campy. Used wherever many copies can appear, such as chat history. */
function BotMark({ className = '' }) {
  return (
    <svg viewBox="0 0 96 96" fill="none" aria-hidden="true" className={className}>
      <path d="M72 30 L80 17" stroke="var(--bot-line)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="81" cy="15" r="4" fill="var(--accent)" />
      <rect x="9" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />
      <rect x="79" y="52" width="8" height="17" rx="4" fill="var(--bot-line)" />
      <rect x="15" y="31" width="66" height="56" rx="20" fill="var(--bot-shell-light)" stroke="var(--bot-line)" strokeWidth="1.5" />
      <rect x="23" y="42" width="50" height="34" rx="14" fill="var(--bot-visor)" />
      <rect x="33" y="51" width="9" height="13" rx="4.5" fill="var(--accent)" />
      <rect x="54" y="51" width="9" height="13" rx="4.5" fill="var(--accent)" />
      <path d="M31 28 V36 C31 40 65 40 65 36 V28" fill="var(--bot-cap-side)" />
      <path d="M48 7 L80 21 L48 35 L16 21 Z" fill="var(--bot-cap)" stroke="var(--bot-line)" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M48 21 L25 28 V42" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="22" y="41" width="6" height="8" rx="2" fill="var(--accent)" />
      <circle cx="48" cy="21" r="2.6" fill="var(--accent)" />
    </svg>
  );
}

const SIZES = {
  sm: { px: 26, icon: 'w-[26px] h-[26px]', text: 'text-sm' },
  md: { px: 34, icon: 'w-[34px] h-[34px]', text: 'text-base' },
  lg: { px: 44, icon: 'w-11 h-11', text: 'text-xl' },
  xl: { px: 64, icon: 'w-16 h-16', text: 'text-3xl' },
};

/** CampusMate logo with Campy as its emblem. */
export default function CampusLogo({ size = 'md', animated = false, showTag = true, className = '', textClassName = '' }) {
  const current = SIZES[size] || SIZES.md;

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      <div className={`relative ${current.icon} flex items-center justify-center shrink-0`}>
        {animated
          ? <CampusBot size={current.px} mood="idle" title="CampusMate" />
          : <BotMark className="h-full w-full transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-105" />}
      </div>

      <div className="flex min-w-0 flex-col">
        <span className={`font-semibold leading-none tracking-[-0.03em] ${textClassName || 'text-text-primary'} ${current.text}`}>
          Campus<span className={textClassName ? 'opacity-75' : 'text-accent'}>Mate</span>
        </span>
        {showTag && (
          <span className={`mt-1 text-[10px] font-medium leading-none ${textClassName ? 'opacity-70 text-current' : 'text-text-muted'}`}>
            Campus AI assistant
          </span>
        )}
      </div>
    </div>
  );
}

/** Avatar for chat messages and thinking indicators. */
export function AIAvatar({ size = 32, isThinking = false }) {
  return (
    <div
      style={{ width: size, height: size }}
      className={`relative flex shrink-0 items-center justify-center rounded-xl border border-border-structural bg-structural p-0.5 ${isThinking ? 'ring-2 ring-accent/50 ring-offset-2 ring-offset-page' : ''}`}
    >
      {isThinking
        ? <CampusBot size={size - 6} mood="thinking" title="CampusMate is thinking" />
        : <BotMark className="h-full w-full" />}
    </div>
  );
}
