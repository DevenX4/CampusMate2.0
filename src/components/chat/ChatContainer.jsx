import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, MotionConfig, useReducedMotion } from 'framer-motion';
import { ArrowDown, Download, Eraser, MoreHorizontal, PanelLeft } from 'lucide-react';
import ChatSidebar from './ChatSidebar';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ChatEmptyState from './ChatEmptyState';
import SourceModal from './SourceModal';
import CampusLogo from '../brand/CampusLogo';
import { isAbort, requestAnswer, toHistory } from './chatApi';
import '../../styles/chat.css';

const NEW_TITLE = 'New conversation';
const OLD_DEMO_IDS = ['chat-1', 'chat-2', 'chat-3'];
const NEAR_BOTTOM_PX = 96;
const DOCKED_WIDTH = 1024;

const clock = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const makeChat = () => ({ id: `chat-${Date.now()}`, title: NEW_TITLE, createdAt: Date.now() });
const isDesktopPointer = () => window.matchMedia?.('(hover: hover) and (pointer: fine)').matches;

function loadChats() {
  try {
    const parsed = JSON.parse(localStorage.getItem('cm_chats') || '[]');
    if (parsed.length > 0 && !parsed.some((c) => OLD_DEMO_IDS.includes(c.id))) {
      return parsed.filter((c, index, all) => index === all.findIndex((t) => t.id === c.id));
    }
  } catch (err) {
    console.error(err);
  }
  return [makeChat()];
}

function loadMessages() {
  try {
    const parsed = JSON.parse(localStorage.getItem('cm_messages') || '{}') || {};
    // Messages saved by older versions have sources without a ref number.
    return Object.fromEntries(Object.entries(parsed).map(([chatId, list]) => [
      chatId,
      (Array.isArray(list) ? list : []).map((message) => (message.sources?.length
        ? { ...message, sources: message.sources.map((s, index) => ({ ...s, ref: s.ref ?? index + 1 })) }
        : message)),
    ]));
  } catch (err) {
    console.error(err);
    return {};
  }
}

function persist(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (err) {
    console.warn('Could not save chat history', err);
  }
}

export default function ChatContainer({ headerActions, onHome }) {
  const reduceMotion = useReducedMotion();
  const [chats, setChats] = useState(loadChats);
  const [activeChatId, setActiveChatId] = useState(() => {
    const saved = localStorage.getItem('cm_active_chat_id');
    return chats.some((c) => c.id === saved) ? saved : chats[0].id;
  });
  const [messages, setMessages] = useState(loadMessages);
  const [liveRuns, setLiveRuns] = useState({});
  const [celebrateId, setCelebrateId] = useState(null);
  const [inputVal, setInputVal] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => window.innerWidth >= DOCKED_WIDTH);
  const [selectedSource, setSelectedSource] = useState(null);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showJump, setShowJump] = useState(false);

  const scrollRef = useRef(null);
  const contentRef = useRef(null);
  const inputRef = useRef(null);
  const menuRef = useRef(null);
  const pinnedRef = useRef(true);
  const runsRef = useRef({});
  const messagesRef = useRef(messages);
  const chatsRef = useRef(chats);
  const activeIdRef = useRef(activeChatId);
  const reduceRef = useRef(reduceMotion);
  const toastTimer = useRef(null);
  const celebrateTimer = useRef(null);

  useLayoutEffect(() => {
    messagesRef.current = messages;
    chatsRef.current = chats;
    activeIdRef.current = activeChatId;
    reduceRef.current = reduceMotion;
  });

  useEffect(() => persist('cm_chats', JSON.stringify(chats)), [chats]);
  useEffect(() => persist('cm_messages', JSON.stringify(messages)), [messages]);
  useEffect(() => persist('cm_active_chat_id', activeChatId), [activeChatId]);

  useEffect(() => () => {
    Object.values(runsRef.current).forEach((run) => {
      run.discard = true;
      clearTimeout(run.timer);
      run.controller.abort();
    });
    clearTimeout(toastTimer.current);
    clearTimeout(celebrateTimer.current);
  }, []);

  const showToast = useCallback((text) => {
    setToastMessage(text);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMessage(null), 2400);
  }, []);

  const focusComposer = useCallback(() => {
    if (isDesktopPointer()) requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  /* ---------- Scroll following ---------- */

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const pinned = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
    pinnedRef.current = pinned;
    setShowJump(!pinned);
  }, []);

  useEffect(() => {
    const scroller = scrollRef.current;
    const content = contentRef.current;
    if (!scroller || !content) return undefined;
    const observer = new ResizeObserver(() => {
      if (pinnedRef.current) scroller.scrollTop = scroller.scrollHeight;
      else handleScroll();
    });
    observer.observe(content);
    observer.observe(scroller);
    return () => observer.disconnect();
  }, [handleScroll]);

  useLayoutEffect(() => {
    pinnedRef.current = true;
    setShowJump(false);
    scrollToBottom();
  }, [activeChatId, scrollToBottom]);

  /* ---------- Answer lifecycle ---------- */

  const publish = useCallback((run) => {
    if (run.discard) return;
    const snapshot = {
      id: run.id,
      sender: 'assistant',
      text: run.buffer.slice(0, run.shown),
      stages: run.stages,
      fallback: run.fallback,
    };
    setLiveRuns((prev) => ({ ...prev, [run.chatId]: snapshot }));
  }, []);

  const commit = useCallback((run, outcome) => {
    if (run.discard || run.committed) return;
    run.committed = true;
    clearTimeout(run.timer);
    delete runsRef.current[run.chatId];

    const finishedAt = Date.now();
    const stages = run.stages.map((stage, index) => ({
      key: stage.key,
      label: stage.label,
      count: stage.count,
      ms: (run.stages[index + 1]?.at ?? finishedAt) - stage.at,
    }));
    const message = { id: run.id, sender: 'assistant', ...outcome, stages, timestamp: clock() };

    setMessages((prev) => ({ ...prev, [run.chatId]: [...(prev[run.chatId] || []), message] }));
    setLiveRuns((prev) => {
      const next = { ...prev };
      delete next[run.chatId];
      return next;
    });

    const answered = !outcome.status && !outcome.clarification_required
      && outcome.answer_type !== 'abstained'
      && !['out_of_scope', 'unknown_abstain'].includes(outcome.route);
    if (answered) {
      setCelebrateId(run.id);
      clearTimeout(celebrateTimer.current);
      celebrateTimer.current = setTimeout(() => setCelebrateId(null), 1600);
    }
  }, []);

  // Reveals received text at a steady pace, catching up faster when it falls behind.
  const pump = useCallback((run) => {
    if (run.timer || run.committed || run.discard) return;
    const tick = () => {
      run.timer = null;
      if (run.committed || run.discard) return;

      const backlog = run.buffer.length - run.shown;
      if (backlog > 0) {
        const instant = document.hidden || reduceRef.current;
        const step = instant ? backlog : Math.max(3, Math.ceil(backlog / (run.outcome ? 5 : 12)));
        let next = Math.min(run.buffer.length, run.shown + step);
        const code = run.buffer.charCodeAt(next - 1);
        if (next < run.buffer.length && code >= 0xd800 && code <= 0xdbff) next += 1;
        run.shown = next;
        publish(run);
      }

      if (run.shown < run.buffer.length) run.timer = setTimeout(tick, 33);
      else if (run.outcome) commit(run, run.outcome);
    };
    run.timer = setTimeout(tick, 33);
  }, [commit, publish]);

  const settleAnswer = useCallback((run, final) => {
    if (run.discard || run.committed) return;
    const shownText = run.buffer.slice(0, run.shown);
    run.buffer = final.text;
    if (!final.text.startsWith(shownText)) run.shown = final.text.length;
    run.outcome = final;
    if (run.shown >= run.buffer.length) commit(run, final);
    else pump(run);
  }, [commit, pump]);

  const settleFailure = useCallback((run, outcome) => {
    if (run.discard || run.committed) return;
    run.shown = run.buffer.length;
    commit(run, { ...outcome, text: run.buffer });
  }, [commit]);

  const startTurn = useCallback((chatId, question, base) => {
    const now = Date.now();
    const history = toHistory(base);
    const isFirst = !base.some((m) => m.sender === 'user');
    const userMessage = { id: `user-${now}`, sender: 'user', text: question, timestamp: clock() };

    setMessages((prev) => ({ ...prev, [chatId]: [...base, userMessage] }));
    setChats((prev) => prev.map((chat) => {
      if (chat.id !== chatId) return chat;
      const title = isFirst && chat.title === NEW_TITLE
        ? question.slice(0, 42) + (question.length > 42 ? '...' : '')
        : chat.title;
      return { ...chat, title, updatedAt: now };
    }));

    const run = {
      id: `bot-${now}`,
      chatId,
      controller: new AbortController(),
      buffer: '',
      shown: 0,
      stages: [],
      timer: null,
      fallback: false,
      outcome: null,
      committed: false,
      discard: false,
    };
    runsRef.current[chatId] = run;
    pinnedRef.current = true;
    setShowJump(false);
    publish(run);

    requestAnswer({
      question,
      conversationId: chatId,
      history,
      signal: run.controller.signal,
      onStage: (stage) => {
        run.stages = [...run.stages, { ...stage, at: Date.now() }];
        publish(run);
      },
      onToken: (text) => {
        run.buffer += text;
        pump(run);
      },
      onFallback: () => {
        run.fallback = true;
        publish(run);
      },
    })
      .then((final) => settleAnswer(run, final))
      .catch((err) => {
        if (isAbort(err)) settleFailure(run, { status: 'stopped' });
        else if (err.code === 'interrupted') settleFailure(run, { status: 'interrupted', errorText: err.message });
        else settleFailure(run, { status: 'error', errorText: err.message || 'Something went wrong. Please try again.' });
      });
  }, [publish, pump, settleAnswer, settleFailure]);

  const handleSend = useCallback((raw) => {
    const text = raw.trim();
    const chatId = activeIdRef.current;
    if (!text || runsRef.current[chatId]) return;
    setInputVal((value) => (value === raw ? '' : value));
    startTurn(chatId, text, messagesRef.current[chatId] || []);
    focusComposer();
  }, [focusComposer, startTurn]);

  const handleStop = useCallback(() => {
    const run = runsRef.current[activeIdRef.current];
    if (!run) return;
    if (run.outcome) {
      run.shown = run.buffer.length;
      commit(run, run.outcome);
    } else {
      run.controller.abort();
    }
  }, [commit]);

  const handleRetry = useCallback((message) => {
    const chatId = activeIdRef.current;
    if (runsRef.current[chatId]) return;
    const list = messagesRef.current[chatId] || [];
    const index = list.findIndex((m) => m.id === message.id);
    let userIndex = index - 1;
    while (userIndex >= 0 && list[userIndex].sender !== 'user') userIndex -= 1;
    if (userIndex < 0) return;
    startTurn(chatId, list[userIndex].text, list.slice(0, userIndex));
  }, [startTurn]);

  const cancelRun = (chatId) => {
    const run = runsRef.current[chatId];
    if (!run) return;
    run.discard = true;
    clearTimeout(run.timer);
    run.controller.abort();
    delete runsRef.current[chatId];
    setLiveRuns((prev) => {
      const next = { ...prev };
      delete next[chatId];
      return next;
    });
  };

  /* ---------- Conversations ---------- */

  const closeSidebarIfOverlay = () => {
    if (window.innerWidth < DOCKED_WIDTH) setIsSidebarOpen(false);
  };

  const handleNewChat = useCallback(() => {
    const currentId = activeIdRef.current;
    const isEmpty = (id) => !(messagesRef.current[id] || []).length && !runsRef.current[id];
    setInputVal('');
    if (window.innerWidth < DOCKED_WIDTH) setIsSidebarOpen(false);
    if (isEmpty(currentId)) {
      focusComposer();
      return;
    }
    const existing = chatsRef.current.find((c) => isEmpty(c.id));
    if (existing) {
      setActiveChatId(existing.id);
    } else {
      const chat = makeChat();
      setChats((prev) => [chat, ...prev]);
      setActiveChatId(chat.id);
    }
    focusComposer();
  }, [focusComposer]);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        handleNewChat();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [handleNewChat]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    const onKey = (e) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const handleDeleteChat = (chatId) => {
    cancelRun(chatId);
    const remaining = chats.filter((c) => c.id !== chatId);
    const fallback = remaining.length ? null : makeChat();
    setChats(fallback ? [fallback] : remaining);
    setMessages((prev) => {
      const next = { ...prev };
      delete next[chatId];
      return next;
    });
    if (activeChatId === chatId) setActiveChatId(fallback ? fallback.id : remaining[0].id);
    showToast('Conversation deleted');
  };

  const handleRenameChat = (chatId, title) => {
    setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, title } : c)));
    showToast('Conversation renamed');
  };

  const handleExportChat = () => {
    setMenuOpen(false);
    const list = messages[activeChatId] || [];
    if (!list.length) {
      showToast('No messages to export');
      return;
    }
    const title = chats.find((c) => c.id === activeChatId)?.title || 'CampusMate chat';
    const header = `# CampusMate conversation\n\n**Date:** ${new Date().toLocaleDateString()}\n**Topic:** ${title}\n\n---\n\n`;
    const body = list.map((m) => {
      const sender = m.sender === 'user' ? 'Student' : 'CampusMate';
      const sources = m.sources?.length
        ? `\n\nSources:\n${m.sources.map((s) => `- [${s.ref}] ${s.title}`).join('\n')}`
        : '';
      return `### ${sender} (${m.timestamp || ''})\n\n${m.text || m.errorText || ''}${sources}\n\n`;
    }).join('---\n\n');

    const url = URL.createObjectURL(new Blob([header + body], { type: 'text/markdown;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.replace(/[^a-z0-9]+/gi, '_').toLowerCase()}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showToast('Exported as Markdown');
  };

  const handleClearMessages = () => {
    setMenuOpen(false);
    cancelRun(activeChatId);
    setMessages((prev) => ({ ...prev, [activeChatId]: [] }));
    setChats((prev) => prev.map((c) => (c.id === activeChatId ? { ...c, title: NEW_TITLE } : c)));
    showToast('Messages cleared');
  };

  const handleOpenSource = useCallback((source) => {
    setSelectedSource(source);
    setIsSourceModalOpen(true);
  }, []);
  const handleCloseSource = useCallback(() => setIsSourceModalOpen(false), []);

  /* ---------- Render ---------- */

  const activeChat = chats.find((c) => c.id === activeChatId) || chats[0];
  const saved = messages[activeChatId] || [];
  const live = liveRuns[activeChatId] || null;
  const rendered = live ? [...saved, live] : saved;
  const latestAssistantId = [...rendered].reverse().find((m) => m.sender === 'assistant')?.id;
  const isBusy = Boolean(live);
  const hasMessages = rendered.length > 0;

  const liveStage = live?.stages[live.stages.length - 1];
  const statusLabel = liveStage?.label || (live?.fallback ? 'Reconnecting' : 'Connecting');

  return (
    <MotionConfig reducedMotion="user">
      <div className="cm-shell flex h-full w-full bg-page text-text-primary overflow-hidden relative font-sans">
        <ChatSidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          chats={chats}
          activeChatId={activeChatId}
          onSelectChat={(id) => {
            setActiveChatId(id);
            closeSidebarIfOverlay();
            focusComposer();
          }}
          onNewChat={handleNewChat}
          onDeleteChat={handleDeleteChat}
          onRenameChat={handleRenameChat}
          onHome={onHome}
        />

        <div className="flex-1 min-w-0 h-full flex flex-col relative">
          <header className="shrink-0 h-13 flex items-center gap-1 px-2 sm:px-3 border-b border-border-default bg-page">
            {!isSidebarOpen && (
              <button
                type="button"
                onClick={() => setIsSidebarOpen(true)}
                aria-label="Open sidebar"
                title="Open sidebar"
                className="w-9 h-9 shrink-0 flex items-center justify-center rounded-xl text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
              >
                <PanelLeft size={18} strokeWidth={1.8} />
              </button>
            )}
            {!isSidebarOpen && (
              <button type="button" onClick={onHome} title="Return to home" className="hidden lg:block mx-1.5 shrink-0 cursor-pointer rounded-lg">
                <CampusLogo size="sm" showTag={false} />
              </button>
            )}
            <h2 className="flex-1 min-w-0 px-1.5 text-sm font-medium text-text-primary truncate">
              {hasMessages ? activeChat?.title : 'New chat'}
            </h2>

            {hasMessages && (
              <div className="relative shrink-0" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setMenuOpen((open) => !open)}
                  aria-label="Conversation options"
                  aria-haspopup="menu"
                  aria-expanded={menuOpen}
                  title="Conversation options"
                  className="w-9 h-9 flex items-center justify-center rounded-xl text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
                >
                  <MoreHorizontal size={18} strokeWidth={1.8} />
                </button>
                <AnimatePresence>
                  {menuOpen && (
                    <motion.div
                      role="menu"
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.14 }}
                      className="absolute right-0 top-full mt-1 w-48 p-1 rounded-2xl bg-elevated border border-border-default shadow-2xl z-30"
                    >
                      <button type="button" role="menuitem" onClick={handleExportChat} className="w-full flex items-center gap-2 h-8 px-2.5 rounded-lg text-[13px] text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer">
                        <Download size={14} />
                        Export as Markdown
                      </button>
                      <button type="button" role="menuitem" onClick={handleClearMessages} className="w-full flex items-center gap-2 h-8 px-2.5 rounded-lg text-[13px] text-status-danger hover:bg-status-danger/10 transition-colors cursor-pointer">
                        <Eraser size={14} />
                        Clear messages
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {headerActions}
          </header>

          <div className="relative flex-1 min-h-0 flex flex-col">
            <div ref={scrollRef} onScroll={handleScroll} className="cm-scroll flex-1 min-h-0 overflow-y-auto">
              <div ref={contentRef} className="min-h-full flex flex-col">
                {!hasMessages ? (
                  <ChatEmptyState onSelectPrompt={handleSend} />
                ) : (
                  <div className="cm-column flex flex-col gap-6 pt-5 sm:pt-7 pb-8">
                    {rendered.map((message) => (
                      <ChatMessage
                        key={message.id}
                        message={message}
                        isLive={Boolean(live) && message.id === live.id}
                        isLatest={message.id === latestAssistantId}
                        celebrate={message.id === celebrateId}
                        statusLabel={Boolean(live) && message.id === live.id ? statusLabel : undefined}
                        onRetry={handleRetry}
                        onOpenSource={handleOpenSource}
                        onSelectOption={handleSend}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="cm-fade-up pointer-events-none absolute inset-x-0 bottom-0 h-6" />

            <AnimatePresence>
              {showJump && hasMessages && (
                <motion.button
                  type="button"
                  onClick={() => {
                    pinnedRef.current = true;
                    setShowJump(false);
                    scrollToBottom();
                  }}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  transition={{ duration: 0.16 }}
                  className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 inline-flex items-center gap-1.5 h-8 pl-2.5 pr-3 rounded-full bg-elevated border border-border-strong text-xs font-medium text-text-primary shadow-lg hover:bg-surface-hover transition-colors cursor-pointer"
                >
                  <ArrowDown size={14} />
                  Jump to latest
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          <ChatInput
            inputRef={inputRef}
            inputVal={inputVal}
            setInputVal={setInputVal}
            onSendMessage={handleSend}
            onStopThinking={handleStop}
            isThinking={isBusy}
          />

          <AnimatePresence>
            {toastMessage && (
              <motion.div
                role="status"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.18 }}
                className="absolute top-15 left-1/2 -translate-x-1/2 z-40 px-3.5 py-2 rounded-xl bg-elevated border border-border-default shadow-xl text-[13px] text-text-primary whitespace-nowrap"
              >
                {toastMessage}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <SourceModal isOpen={isSourceModalOpen} onClose={handleCloseSource} source={selectedSource} />
      </div>
    </MotionConfig>
  );
}
