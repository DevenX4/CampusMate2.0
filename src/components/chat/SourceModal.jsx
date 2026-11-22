import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

const isSample = (source) => source?.source_type === 'synthetic';

export default function SourceModal({ isOpen, onClose, source }) {
  const closeRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const previous = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      previous?.focus?.();
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && source && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4 modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.16 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="cm-source-title"
            className="w-full sm:max-w-xl max-h-[85dvh] flex flex-col overflow-hidden bg-elevated border border-border-default rounded-t-2xl sm:rounded-2xl shadow-2xl"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3 px-5 pt-4 pb-3 border-b border-border-default">
              {source.ref != null && (
                <span className="cm-cite cm-cite--idle mt-0.5 shrink-0" style={{ height: '1.4rem', minWidth: '1.4rem', fontSize: '0.75rem' }}>
                  {source.ref}
                </span>
              )}
              <div className="min-w-0 flex-1">
                <h3 id="cm-source-title" className="text-[15px] font-semibold leading-snug text-text-primary">
                  {source.title || 'Campus record'}
                </h3>
                {isSample(source) && (
                  <p className="mt-1 text-xs text-text-muted">Sample data, so confirm it with your department.</p>
                )}
              </div>
              <button
                ref={closeRef}
                type="button"
                onClick={onClose}
                aria-label="Close source"
                className="p-1.5 -mr-1 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="cm-scroll px-5 py-4 overflow-y-auto">
              <p className="text-sm leading-relaxed text-text-secondary whitespace-pre-wrap">
                {source.content || 'No excerpt is available for this record.'}
              </p>
            </div>

            <p className="px-5 py-3 border-t border-border-default text-xs leading-relaxed text-text-muted">
              Excerpt from the record CampusMate used for this answer.
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
