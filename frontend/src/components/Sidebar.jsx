import React, { useState } from 'react';
import {
  ChatText,
  Trash,
  Plus,
  MagnifyingGlass,
  CheckCircle,
  Clock,
  Broadcast,
} from '@phosphor-icons/react';

export default function Sidebar({
  isOpen,
  sessions = [],
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
}) {
  const [filter, setFilter] = useState('');

  const filteredSessions = sessions.filter((s) =>
    (s.title || 'Untitled Session').toLowerCase().includes(filter.toLowerCase())
  );

  const formatDate = (isoStr) => {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!isOpen) return null;

  return (
    <aside className="w-72 sm:w-80 h-[calc(100vh-4rem)] bg-slate-950 border-r border-slate-800/80 flex flex-col z-20 shrink-0 transition-all duration-300">
      {/* Sidebar Header & Search */}
      <div className="p-4 border-b border-slate-800/80 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            Sessions ({sessions.length})
          </span>
          <button
            onClick={onNewSession}
            className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-900 rounded-md transition-colors"
            title="Create New Session"
          >
            <Plus size={16} weight="bold" />
          </button>
        </div>

        {/* Search input */}
        <div className="relative">
          <MagnifyingGlass
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
          />
          <input
            type="text"
            placeholder="Filter sessions..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50"
          />
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredSessions.length === 0 ? (
          <div className="text-center py-8 px-4 text-slate-500 text-xs">
            {filter ? 'No matching sessions found.' : 'No sessions yet. Start your first growth session!'}
          </div>
        ) : (
          filteredSessions.map((s) => {
            const isActive = s.id === activeSessionId;
            return (
              <div
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`group relative flex items-start justify-between p-3 rounded-xl cursor-pointer transition-all border ${
                  isActive
                    ? 'bg-slate-900 border-emerald-500/30 text-white shadow-[0_0_12px_rgba(16,185,129,0.08)]'
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-900/60 hover:text-slate-200'
                }`}
              >
                <div className="flex items-start gap-2.5 min-w-0 pr-2">
                  <div
                    className={`mt-0.5 p-1.5 rounded-md ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-slate-900 text-slate-500 group-hover:text-slate-400'
                    }`}
                  >
                    <ChatText size={16} weight={isActive ? 'fill' : 'regular'} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium truncate leading-snug">
                      {s.title || 'Untitled Session'}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500 font-mono">
                      <Clock size={12} />
                      <span>{formatDate(s.updated_at || s.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Delete Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Delete this session and all its messages?')) {
                      onDeleteSession(s.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 hover:bg-slate-800/80 rounded transition-all"
                  title="Delete Session"
                >
                  <Trash size={14} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Grounding Source Info Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/80 text-[11px] text-slate-500">
        <div className="flex items-center gap-2 mb-1 text-slate-400 font-medium">
          <Broadcast size={14} className="text-emerald-400" />
          <span>Verified Knowledge Base</span>
        </div>
        <p className="text-[10px] text-slate-500 leading-normal">
          Brian Chesky (Airbnb Founder Mode) & Shreyas Doshi (LNO Framework & Pre-Mortems).
        </p>
      </div>
    </aside>
  );
}
