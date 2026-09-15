import React, { useState, useMemo, useEffect } from 'react';
import {
  ChatText,
  Trash,
  Plus,
  MagnifyingGlass,
  X,
  Sparkle,
  CalendarBlank,
  PencilSimple,
  Check,
  CircleNotch,
} from '@phosphor-icons/react';
import { api } from '../services/api';

export default function Sidebar({
  isOpen,
  sessions = [],
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onRenameSession,
}) {
  const [filter, setFilter] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deepSearchResults, setDeepSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  // Debounced deep search across conversations
  useEffect(() => {
    if (!filter.trim()) {
      setDeepSearchResults(null);
      setIsSearching(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await api.searchSessions(filter.trim());
        setDeepSearchResults(Array.isArray(results) ? results : []);
      } catch (err) {
        console.warn('Deep search error:', err);
        setDeepSearchResults(null);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [filter]);

  // Combined session list: matches from client filter or deep search
  const displayedSessions = useMemo(() => {
    if (!filter.trim()) return sessions;
    if (deepSearchResults !== null) {
      const matchMap = new Map(deepSearchResults.map((r) => [r.id, r]));
      return sessions
        .filter((s) => matchMap.has(s.id) || (s.title || '').toLowerCase().includes(filter.toLowerCase()))
        .map((s) => {
          const match = matchMap.get(s.id);
          return {
            ...s,
            matchedSnippet: match?.matched_snippet || null,
            matchType: match?.match_type || 'title',
          };
        });
    }
    return sessions.filter((s) =>
      (s.title || 'Untitled Session').toLowerCase().includes(filter.toLowerCase())
    );
  }, [sessions, filter, deepSearchResults]);

  // Group sessions by date
  const groupedSessions = useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const last7Days = new Date(today);
    last7Days.setDate(last7Days.getDate() - 7);

    const groups = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    };

    displayedSessions.forEach((session) => {
      const sessionDate = session.created_at ? new Date(session.created_at) : today;
      if (sessionDate >= today) {
        groups.Today.push(session);
      } else if (sessionDate >= yesterday) {
        groups.Yesterday.push(session);
      } else if (sessionDate >= last7Days) {
        groups['Previous 7 Days'].push(session);
      } else {
        groups.Older.push(session);
      }
    });

    return groups;
  }, [displayedSessions]);

  const handleStartEdit = (s, e) => {
    e.stopPropagation();
    setEditingId(s.id);
    setEditTitle(s.title || '');
  };

  const handleSaveEdit = async (sessionId, e) => {
    if (e) e.stopPropagation();
    if (editTitle.trim() && onRenameSession) {
      await onRenameSession(sessionId, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleKeyDownEdit = (sessionId, e) => {
    if (e.key === 'Enter') {
      handleSaveEdit(sessionId, e);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <aside className="w-72 sm:w-80 h-[calc(100vh-3.5rem)] bg-[#090D16]/80 backdrop-blur-xl border-r border-slate-800/80 flex flex-col z-20 shrink-0 select-none">
      {/* Header & Quick Search Bar */}
      <div className="p-3 border-b border-slate-800/80 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
            <ChatText size={14} className="text-cyan-400" weight="fill" />
            Conversations ({sessions.length})
          </span>
          <button
            onClick={onNewSession}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 rounded-lg transition-colors cursor-pointer shadow-sm"
            title="Create New Session"
            aria-label="Create New Session"
          >
            <Plus size={13} weight="bold" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="relative">
          {isSearching ? (
            <CircleNotch
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-cyan-400 animate-spin"
            />
          ) : (
            <MagnifyingGlass
              size={13}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500"
            />
          )}
          <input
            type="text"
            placeholder="Search titles & messages..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-slate-900/80 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/40 font-sans"
          />
          {filter && (
            <button
              onClick={() => setFilter('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Date-Grouped Session List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {displayedSessions.length === 0 ? (
          <div className="text-center py-10 px-4 text-slate-500 text-xs">
            {filter ? 'No matching conversations found.' : 'No conversations yet. Start a new session!'}
          </div>
        ) : (
          Object.entries(groupedSessions).map(([groupTitle, sessionList]) => {
            if (sessionList.length === 0) return null;
            return (
              <div key={groupTitle} className="space-y-1">
                <div className="px-2 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                  <CalendarBlank size={11} />
                  <span>{groupTitle}</span>
                </div>

                {sessionList.map((s) => {
                  const isActive = s.id === activeSessionId;
                  const isConfirming = deleteConfirmId === s.id;
                  const isEditing = editingId === s.id;

                  return (
                    <div
                      key={s.id}
                      onClick={() => onSelectSession(s.id)}
                      className={`group relative flex flex-col justify-center px-2.5 py-2 rounded-xl cursor-pointer transition-all border ${
                        isActive
                          ? 'bg-slate-900/90 border-cyan-500/40 text-white shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                          : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/50 hover:text-slate-200'
                      }`}
                    >
                      {/* Active Left Indicator Bar */}
                      {isActive && (
                        <div className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-gradient-to-b from-cyan-400 to-violet-500" />
                      )}

                      <div className="flex items-center justify-between w-full">
                        <div className="flex items-center gap-2 min-w-0 pr-2 pl-1 flex-1">
                          <ChatText
                            size={14}
                            weight={isActive ? 'fill' : 'regular'}
                            className={`shrink-0 ${
                              isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-400'
                            }`}
                          />
                          {isEditing ? (
                            <div className="flex items-center gap-1 w-full" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="text"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onKeyDown={(e) => handleKeyDownEdit(s.id, e)}
                                autoFocus
                                className="w-full bg-slate-950 text-white text-xs border border-cyan-500/50 rounded px-1.5 py-0.5 focus:outline-none"
                              />
                              <button
                                onClick={(e) => handleSaveEdit(s.id, e)}
                                className="p-1 text-cyan-400 hover:text-cyan-300"
                                title="Save"
                              >
                                <Check size={12} weight="bold" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setEditingId(null);
                                }}
                                className="p-1 text-slate-400 hover:text-white"
                                title="Cancel"
                              >
                                <X size={12} />
                              </button>
                            </div>
                          ) : (
                            <span className="text-xs font-medium truncate font-sans">
                              {s.title || 'Untitled Session'}
                            </span>
                          )}
                        </div>

                        {/* Action Buttons: Rename & Delete */}
                        {!isEditing && (
                          <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => handleStartEdit(s, e)}
                              className="p-1 text-slate-500 hover:text-emerald-400 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                              title="Rename Conversation"
                              aria-label="Rename Conversation"
                            >
                              <PencilSimple size={12} />
                            </button>

                            {isConfirming ? (
                              <div
                                className="flex items-center gap-1 bg-red-950/80 border border-red-500/40 rounded px-1.5 py-0.5"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <button
                                  onClick={() => {
                                    onDeleteSession(s.id);
                                    setDeleteConfirmId(null);
                                  }}
                                  className="text-[10px] font-bold text-red-400 hover:text-red-300"
                                >
                                  Delete
                                </button>
                                <button
                                  onClick={() => setDeleteConfirmId(null)}
                                  className="text-[10px] text-slate-400 hover:text-white"
                                >
                                  ✕
                                </button>
                              </div>
                            ) : (
                              <>
                                <button
                                  onClick={(e) => handleStartEdit(s, e)}
                                  className="p-1 text-slate-500 hover:text-cyan-400 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                                  title="Rename conversation"
                                  aria-label="Rename conversation"
                                >
                                  <PencilSimple size={12} />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setDeleteConfirmId(s.id);
                                  }}
                                  className="p-1 text-slate-500 hover:text-rose-400 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                                  title="Delete conversation"
                                  aria-label="Delete conversation"
                                >
                                  <Trash size={12} />
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Evidence citation count if message contains grounded proof */}
                      {s.message_count > 0 && (
                        <div className="flex items-center gap-2 pl-6 pt-0.5 text-[10px] text-slate-500 font-mono">
                          <span>{s.message_count} {s.message_count === 1 ? 'msg' : 'msgs'}</span>
                          {s.top_similarity && (
                            <>
                              <span>•</span>
                              <span className="text-cyan-400">
                                {Math.round(s.top_similarity * 100)}% grounded
                              </span>
                            </>
                          )}
                        </div>
                      )}

                      {/* Snippet preview if available */}
                      {s.last_message && (
                        <div className="pl-6 pt-1 text-[10px] text-cyan-400/80 font-mono line-clamp-1 italic">
                          "{s.last_message}"
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>

      {/* Sidebar Footer: Operational Specs */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60 text-[11px] font-mono text-slate-500 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Sparkle size={11} className="text-cyan-400" weight="fill" />
          <span className="text-slate-400 font-medium">Lenny Intelligence</span>
        </div>
        <span className="px-1.5 py-0.5 bg-slate-900 border border-slate-800 text-[9px] rounded text-slate-400">
          v1.0.4
        </span>
      </div>
    </aside>
  );
}
