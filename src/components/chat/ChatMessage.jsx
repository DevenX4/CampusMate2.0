import React, { memo, useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import {
  AlertCircle, ArrowUpRight, BookOpen, Check, ChevronDown, CirclePlay, Copy,
  FileText, Globe, GraduationCap, RotateCcw, Volume2, VolumeX,
} from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import ThinkingStatus from './ThinkingStatus';
import { isFailedMessage, STAGE_MOOD } from './chatApi';

const EASE = [0.16, 1, 0.3, 1];

const isUnanswered = (message) => (
  message.answer_type === 'abstained' || ['out_of_scope', 'unknown_abstain'].includes(message.route)
);

function linkIcon(label) {
  if (/youtube|video|lecture/i.test(label)) return CirclePlay;
  if (/nptel|course/i.test(label)) return GraduationCap;
  if (/notes|geeks/i.test(label)) return BookOpen;
  if (/paper|pyq/i.test(label)) return FileText;
  return Globe;
}

function linkHost(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return host === 'google.com' ? 'Google search' : host;
  } catch {
    return '';
  }
}

function SourcesRow({ sources, onOpenSource }) {
  const [open, setOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 h-7 pl-2 pr-1.5 -ml-2 rounded-xl text-[13px] text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
      >
        <span>Sources</span>
        <span className="font-mono text-[11px] text-text-muted">{sources.length}</span>
        <ChevronDown size={14} className={`text-text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.ul
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: EASE }}
            className="overflow-hidden"
          >
            {sources.map((source) => (
              <li key={source.ref}>
                <button
                  type="button"
                  onClick={() => onOpenSource(source)}
                  className="group w-full flex items-start gap-2.5 mt-1 px-2 py-1.5 -ml-2 rounded-xl text-left hover:bg-surface-hover transition-colors cursor-pointer"
                >
                  <span className="cm-cite cm-cite--idle mt-0.5 shrink-0">{source.ref}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] leading-snug text-text-primary truncate">{source.title}</span>
                    {source.content && (
                      <span className="block mt-0.5 text-xs leading-snug text-text-muted truncate">{source.content}</span>
                    )}
                  </span>
                  {source.source_type === 'synthetic' && (
                    <span className="shrink-0 mt-0.5 text-[11px] text-text-muted">Sample</span>
                  )}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

function StudyLinks({ links }) {
  return (
    <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-2">
      {links.map((link) => {
        const Icon = linkIcon(link.label);
        return (
          <a
            key={link.url}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex flex-col gap-1.5 min-w-0 p-2.5 rounded-2xl bg-surface border border-border-default hover:border-border-strong hover:bg-surface-hover transition-colors"
          >
            <span className="flex items-center justify-between">
              <Icon size={15} strokeWidth={1.8} className="text-text-muted group-hover:text-accent transition-colors" />
              <ArrowUpRight size={14} className="text-text-muted group-hover:text-text-primary transition-colors" />
            </span>
            <span className="min-w-0">
              <span className="block text-[13px] font-medium leading-tight text-text-primary truncate">{link.label}</span>
              <span className="block mt-0.5 text-[11px] leading-tight text-text-muted truncate">{linkHost(link.url)}</span>
            </span>
          </a>
        );
      })}
    </div>
  );
}

function QuickReplies({ options, onSelect }) {
  const reduceMotion = useReducedMotion();
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {options.map((option, index) => (
        <motion.button
          key={option}
          type="button"
          initial={reduceMotion ? false : { opacity: 0, y: 8, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.3, delay: index * 0.045, ease: EASE }}
          onClick={() => onSelect(option)}
          className="px-3.5 py-1.5 rounded-full border border-border-strong bg-surface text-[13px] leading-5 text-text-primary hover:border-accent hover:bg-accent-muted hover:text-accent transition-colors cursor-pointer"
        >
          {option}
        </motion.button>
      ))}
    </div>
  );
}

function ActionButton({ label, onClick, active, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`w-7 h-7 flex items-center justify-center rounded-lg transition-colors cursor-pointer hover:bg-surface-hover ${
        active ? 'text-accent' : 'text-text-muted hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  );
}

function AssistantActions({ message, isLatest, onRetry }) {
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => () => {
    if (speaking) window.speechSynthesis?.cancel();
  }, [speaking]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  const toggleSpeech = () => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    if (speaking) {
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(message.text.replace(/\[\d+\]/g, '').replace(/[*_#`|]/g, '').trim());
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  };

  return (
    <div className="cm-actions mt-1.5 -ml-1.5 flex items-center gap-0.5" data-visible={isLatest}>
      <ActionButton label={copied ? 'Copied' : 'Copy answer'} onClick={copy} active={copied}>
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </ActionButton>
      <ActionButton label={speaking ? 'Stop reading' : 'Read aloud'} onClick={toggleSpeech} active={speaking}>
        {speaking ? <VolumeX size={14} /> : <Volume2 size={14} />}
      </ActionButton>
      <ActionButton label="Ask again" onClick={() => onRetry(message)}>
        <RotateCcw size={14} />
      </ActionButton>
      {message.status === 'stopped' && <span className="ml-1.5 text-xs text-text-muted">Stopped</span>}
      {message.timestamp && <span className="ml-1.5 text-[11px] text-text-muted">{message.timestamp}</span>}
    </div>
  );
}

function InlineError({ text, onRetry }) {
  return (
    <div role="alert" className="mt-2 flex items-start gap-2.5 px-3 py-2.5 rounded-2xl border border-status-danger/35 bg-status-danger/5">
      <AlertCircle size={16} className="mt-0.5 shrink-0 text-status-danger" />
      <p className="flex-1 min-w-0 text-[13.5px] leading-snug text-text-primary">{text}</p>
      <button
        type="button"
        onClick={onRetry}
        className="shrink-0 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-xl border border-border-strong text-[13px] text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
      >
        <RotateCcw size={13} />
        Retry
      </button>
    </div>
  );
}

function AssistantMessage({ message, isLive, isLatest, celebrate, statusLabel, onRetry, onOpenSource, onSelectOption }) {
  const reduceMotion = useReducedMotion();
  const failed = isFailedMessage(message);
  const interrupted = message.status === 'interrupted';
  const unanswered = isUnanswered(message);
  const stoppedEmpty = message.status === 'stopped' && !message.text;
  const stages = message.stages || [];
  const currentStage = stages[stages.length - 1];

  let mood = 'idle';
  if (isLive) mood = STAGE_MOOD[currentStage?.key] || 'thinking';
  else if (failed || unanswered || interrupted) mood = 'confused';
  else if (celebrate) mood = 'happy';

  const hasOptions = !isLive && isLatest && message.options?.length > 0;
  const hasLinks = !isLive && message.links?.length > 0;
  const hasSources = !isLive && message.sources?.length > 0;
  const showActions = !isLive && !failed && Boolean(message.text);

  return (
    <motion.article
      className="cm-turn"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: EASE }}
    >
      <ThinkingStatus
        mood={mood}
        animated={isLive || isLatest}
        isLive={isLive}
        statusLabel={statusLabel}
        stages={stages}
        grounding={message.grounding}
        provider={message.provider}
        totalMs={message.timings_ms?.total}
      />

      {failed ? (
        <InlineError text={message.errorText || message.text} onRetry={() => onRetry(message)} />
      ) : (
        <>
          {(message.text || (isLive && currentStage?.key === 'write')) && (
            <div className="mt-2">
              <MarkdownRenderer
                content={message.text}
                streaming={isLive}
                sources={isLive ? undefined : message.sources}
                onOpenSource={onOpenSource}
              />
            </div>
          )}
          {stoppedEmpty && <p className="mt-2 text-sm text-text-muted">Stopped before an answer was written.</p>}
          {interrupted && <InlineError text={message.errorText} onRetry={() => onRetry(message)} />}
          {hasOptions && <QuickReplies options={message.options} onSelect={onSelectOption} />}
          {hasLinks && <StudyLinks links={message.links} />}
          {hasSources && <SourcesRow sources={message.sources} onOpenSource={onOpenSource} />}
          {showActions && <AssistantActions message={message} isLatest={isLatest} onRetry={onRetry} />}
          {stoppedEmpty && (
            <button
              type="button"
              onClick={() => onRetry(message)}
              className="mt-2 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-xl border border-border-strong text-[13px] text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
            >
              <RotateCcw size={13} />
              Retry
            </button>
          )}
        </>
      )}
    </motion.article>
  );
}

function UserMessage({ message }) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      className="flex justify-end"
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.26, ease: EASE }}
    >
      <p className="max-w-[85%] sm:max-w-[75%] px-4 py-2.5 rounded-2xl rounded-br-lg bg-surface-hover border border-border-default text-[15px] leading-relaxed text-text-primary whitespace-pre-wrap [overflow-wrap:anywhere]">
        {message.text}
      </p>
    </motion.div>
  );
}

function ChatMessage(props) {
  if (props.message.sender === 'user') return <UserMessage message={props.message} />;
  if (props.message.sender !== 'assistant') return null;
  return <AssistantMessage {...props} />;
}

export default memo(ChatMessage);
