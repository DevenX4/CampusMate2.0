import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MoreHorizontal, PanelLeftClose, Pencil, Pin, PinOff, Plus, Search, Trash2 } from 'lucide-react';
import CampusLogo from '../brand/CampusLogo';

const DAY = 24 * 60 * 60 * 1000;

function groupChats(chats, pinnedIds) {
  const startOfToday = new Date().setHours(0, 0, 0, 0);
  const groups = { Pinned: [], Today: [], Yesterday: [], 'Previous 7 days': [], Older: [] };
  const stamp = (chat) => chat.updatedAt || chat.createdAt || 0;

  [...chats].sort((a, b) => stamp(b) - stamp(a)).forEach((chat) => {
    const time = stamp(chat);
    if (pinnedIds.includes(chat.id)) groups.Pinned.push(chat);
    else if (time >= startOfToday) groups.Today.push(chat);
    else if (time >= startOfToday - DAY) groups.Yesterday.push(chat);
    else if (time >= startOfToday - 7 * DAY) groups['Previous 7 days'].push(chat);
    else groups.Older.push(chat);
  });

  return Object.entries(groups).filter(([, list]) => list.length > 0);
}

function RowMenu({ anchor, isPinned, onPin, onRename, onDelete, onClose }) {
  const ref = useRef(null);
  const [confirming, setConfirming] = useState(false);
  const rect = anchor.getBoundingClientRect();
  const width = 168;
  const height = 124;
  const opensUp = rect.bottom + height + 8 > window.innerHeight;
  const style = {
    top: opensUp ? rect.top - height - 4 : rect.bottom + 4,
    left: Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8)),
    width,
  };

  useEffect(() => {
    const onDown = (e) => {
      if (ref.current?.contains(e.target) || anchor.contains(e.target)) return;
      onClose();
    };
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', onClose);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', onClose);
    };
  }, [anchor, onClose]);

  const item = 'w-full flex items-center gap-2 h-8 px-2.5 rounded-lg text-[13px] transition-colors cursor-pointer';

  return createPortal(
    <div ref={ref} role="menu" style={style} className="fixed z-[60] p-1 rounded-2xl bg-elevated border border-border-default shadow-2xl">
      <button type="button" role="menuitem" onClick={onPin} className={`${item} text-text-secondary hover:text-text-primary hover:bg-surface-hover`}>
        {isPinned ? <PinOff size={14} /> : <Pin size={14} />}
        {isPinned ? 'Unpin' : 'Pin'}
      </button>
      <button type="button" role="menuitem" onClick={onRename} className={`${item} text-text-secondary hover:text-text-primary hover:bg-surface-hover`}>
        <Pencil size={14} />
        Rename
      </button>
      <button
        type="button"
        role="menuitem"
        onClick={() => (confirming ? onDelete() : setConfirming(true))}
        className={`${item} text-status-danger hover:bg-status-danger/10 ${confirming ? 'bg-status-danger/10 font-medium' : ''}`}
      >
        <Trash2 size={14} />
        {confirming ? 'Confirm delete' : 'Delete'}
      </button>
    </div>,
    document.body,
  );
}

function ChatRow({ chat, isActive, isPinned, onSelect, onPin, onDelete, onRename }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState(chat.title);
  const anchorRef = useRef(null);
  const closeMenu = useRef(() => setMenuOpen(false)).current;

  const startRename = () => {
    setDraft(chat.title);
    setRenaming(true);
    setMenuOpen(false);
  };

  const commit = () => {
    const next = draft.trim();
    if (next && next !== chat.title) onRename(chat.id, next);
    setRenaming(false);
  };

  if (renaming) {
    return (
      <div className="px-1 py-0.5">
        <input
          autoFocus
          value={draft}
          aria-label="Conversation name"
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onFocus={(e) => e.target.select()}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') setRenaming(false);
          }}
          className="w-full h-8 px-2 rounded-lg bg-page border border-accent text-[13px] text-text-primary focus:outline-none"
        />
      </div>
    );
  }

  return (
    <div className={`cm-row relative rounded-xl transition-colors ${isActive ? 'bg-surface-hover' : 'hover:bg-surface-hover/60'}`}>
      <button
        type="button"
        onClick={onSelect}
        aria-current={isActive ? 'page' : undefined}
        title={chat.title}
        className={`block w-full h-9 pl-2.5 pr-8 text-left text-[13px] truncate cursor-pointer ${
          isActive ? 'text-text-primary font-medium' : 'text-text-secondary'
        }`}
      >
        {chat.title}
      </button>
      <button
        ref={anchorRef}
        type="button"
        data-open={menuOpen}
        aria-label={`Options for ${chat.title}`}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((open) => !open)}
        className="cm-row-action absolute right-1 top-1 w-7 h-7 flex items-center justify-center rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-hover cursor-pointer"
      >
        <MoreHorizontal size={15} />
      </button>
      {menuOpen && anchorRef.current && (
        <RowMenu
          anchor={anchorRef.current}
          isPinned={isPinned}
          onClose={closeMenu}
          onPin={() => { onPin(chat.id); setMenuOpen(false); }}
          onRename={startRename}
          onDelete={() => { setMenuOpen(false); onDelete(chat.id); }}
        />
      )}
    </div>
  );
}

export default function ChatSidebar({
  isOpen, onClose, chats, activeChatId, onSelectChat, onNewChat, onDeleteChat, onRenameChat, onHome,
}) {
  const [search, setSearch] = useState('');
  const [pinnedIds, setPinnedIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('pinnedChats') || '[]');
    } catch {
      return [];
    }
  });

  const togglePin = (chatId) => {
    setPinnedIds((prev) => {
      const next = prev.includes(chatId) ? prev.filter((id) => id !== chatId) : [...prev, chatId];
      try {
        localStorage.setItem('pinnedChats', JSON.stringify(next));
      } catch {
        /* Pinning still works for this session. */
      }
      return next;
    });
  };

  const groups = useMemo(() => {
    const query = search.trim().toLowerCase();
    const visible = query ? chats.filter((c) => c.title.toLowerCase().includes(query)) : chats;
    return groupChats(visible, pinnedIds);
  }, [chats, search, pinnedIds]);

  return (
    <>
      {isOpen && (
        <div onClick={onClose} aria-hidden="true" className="fixed inset-0 z-40 modal-backdrop lg:hidden" />
      )}

      <aside
        data-open={isOpen}
        aria-label="Conversations"
        className={`cm-sidebar fixed lg:static inset-y-0 left-0 z-40 shrink-0 overflow-hidden bg-surface border-r flex ${
          isOpen
            ? 'translate-x-0 w-[17rem] border-border-default'
            : '-translate-x-full lg:translate-x-0 w-[17rem] lg:w-0 border-transparent'
        }`}
      >
        <div className="w-[17rem] shrink-0 h-full flex flex-col">
          <div className="flex items-center justify-between h-13 pl-3.5 pr-2 shrink-0">
            <button type="button" onClick={onHome} title="Return to home" className="cursor-pointer rounded-lg">
              <CampusLogo size="sm" showTag={false} />
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close sidebar"
              title="Close sidebar"
              className="w-8 h-8 flex items-center justify-center rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors cursor-pointer"
            >
              <PanelLeftClose size={17} strokeWidth={1.8} />
            </button>
          </div>

          <div className="px-2 space-y-1 shrink-0">
            <button
              type="button"
              onClick={onNewChat}
              className="group w-full flex items-center gap-2 h-9 px-2.5 rounded-xl border border-border-default bg-page/40 text-[13px] font-medium text-text-primary hover:border-border-strong hover:bg-surface-hover transition-colors cursor-pointer"
            >
              <Plus size={15} className="text-accent" />
              <span>New chat</span>
              <kbd className="ml-auto font-mono text-[10.5px] text-text-muted">Ctrl K</kbd>
            </button>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
              <input
                type="search"
                aria-label="Search conversations"
                placeholder="Search conversations"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full h-9 pl-8 pr-2.5 rounded-xl bg-transparent border border-transparent hover:bg-surface-hover/60 focus:bg-page focus:border-border-strong text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none transition-colors"
              />
            </div>
          </div>

          <nav className="cm-scroll flex-1 min-h-0 overflow-y-auto px-2 pt-2 pb-3">
            {groups.length === 0 && (
              <p className="px-2.5 py-4 text-[13px] text-text-muted">
                {search.trim() ? 'No conversations match that search.' : 'Your conversations will appear here.'}
              </p>
            )}
            {groups.map(([label, list]) => (
              <section key={label} className="mt-3 first:mt-1">
                <h3 className="px-2.5 pb-1 text-[11.5px] font-medium text-text-muted">{label}</h3>
                <div className="space-y-px">
                  {list.map((chat) => (
                    <ChatRow
                      key={chat.id}
                      chat={chat}
                      isActive={chat.id === activeChatId}
                      isPinned={pinnedIds.includes(chat.id)}
                      onSelect={() => onSelectChat(chat.id)}
                      onPin={togglePin}
                      onDelete={onDeleteChat}
                      onRename={onRenameChat}
                    />
                  ))}
                </div>
              </section>
            ))}
          </nav>

          <p className="shrink-0 px-4 py-2.5 border-t border-border-default text-[11px] leading-snug text-text-muted">
            U.V. Patel College of Engineering, Ganpat University
          </p>
        </div>
      </aside>
    </>
  );
}
