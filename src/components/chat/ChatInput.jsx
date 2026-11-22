import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { ArrowUp, Check, ChevronDown, Square } from 'lucide-react';

const ENGINE_LABEL = 'Groq gpt-oss-120b + Hybrid RAG';
const MAX_HEIGHT = 200;

export default function ChatInput({ inputRef, inputVal, setInputVal, onSendMessage, onStopThinking, isThinking }) {
  const reduceMotion = useReducedMotion();
  const [showEngine, setShowEngine] = useState(false);
  const engineRef = useRef(null);
  const canSend = Boolean(inputVal.trim()) && !isThinking;

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
  }, [inputVal, inputRef]);

  useEffect(() => {
    if (!showEngine) return undefined;
    const onDown = (e) => {
      if (engineRef.current && !engineRef.current.contains(e.target)) setShowEngine(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setShowEngine(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [showEngine]);

  const submit = () => {
    if (canSend) onSendMessage(inputVal);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const iconMotion = reduceMotion
    ? {}
    : {
        initial: { opacity: 0, scale: 0.5, rotate: -45 },
        animate: { opacity: 1, scale: 1, rotate: 0 },
        exit: { opacity: 0, scale: 0.5, rotate: 45 },
        transition: { duration: 0.16 },
      };

  return (
    <div className="shrink-0 bg-page pb-[max(0.6rem,env(safe-area-inset-bottom))]">
      <div className="cm-column">
        <div className="cm-composer">
          <label htmlFor="cm-composer-input" className="sr-only">Message CampusMate</label>
          <textarea
            id="cm-composer-input"
            ref={inputRef}
            rows={1}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about exams, faculty or subjects"
            className="cm-scroll block w-full resize-none bg-transparent px-4 pt-3.5 pb-1 text-base sm:text-[15px] leading-6 text-text-primary placeholder:text-text-muted"
          />

          <div className="flex items-center justify-between gap-2 pl-2 pr-2 pb-2 pt-1">
            <div className="relative min-w-0" ref={engineRef}>
              <button
                type="button"
                onClick={() => setShowEngine((open) => !open)}
                aria-expanded={showEngine}
                aria-haspopup="dialog"
                className="flex items-center gap-1 max-w-full h-8 px-2 rounded-xl text-xs text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
              >
                <span className="truncate">{ENGINE_LABEL}</span>
                <ChevronDown size={13} className={`shrink-0 transition-transform duration-200 ${showEngine ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {showEngine && (
                  <motion.div
                    role="dialog"
                    aria-label="Answer engine"
                    initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
                    transition={{ duration: 0.16 }}
                    className="absolute bottom-full left-0 mb-2 w-[min(19rem,calc(100vw-3rem))] p-3 rounded-2xl bg-elevated border border-border-default shadow-2xl z-30"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[13px] font-medium text-text-primary">{ENGINE_LABEL}</span>
                      <Check size={14} className="shrink-0 text-accent" />
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-text-muted">
                      Hybrid keyword and semantic search finds campus records, then Groq writes the answer from them.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <button
              type="button"
              onClick={isThinking ? onStopThinking : submit}
              disabled={!isThinking && !canSend}
              aria-label={isThinking ? 'Stop generating' : 'Send message'}
              title={isThinking ? 'Stop generating' : 'Send message'}
              className={`relative shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-colors duration-150 ${
                isThinking
                  ? 'bg-text-primary text-page cursor-pointer'
                  : canSend
                    ? 'bg-accent text-on-accent hover:bg-accent-hover cursor-pointer'
                    : 'bg-surface-hover text-text-muted cursor-not-allowed'
              }`}
            >
              <AnimatePresence mode="wait" initial={false}>
                {isThinking ? (
                  <motion.span key="stop" className="flex" {...iconMotion}>
                    <Square size={13} fill="currentColor" strokeWidth={0} />
                  </motion.span>
                ) : (
                  <motion.span key="send" className="flex" {...iconMotion}>
                    <ArrowUp size={18} strokeWidth={2.2} />
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
          </div>
        </div>

        <p className="mt-1.5 text-center text-[11px] leading-snug text-text-muted">
          CampusMate can make mistakes, and some records are sample data. Confirm important details with your department.
        </p>
      </div>
    </div>
  );
}
