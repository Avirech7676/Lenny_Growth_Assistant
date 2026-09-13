import React from 'react';
import {
  Sparkle,
  SidebarSimple,
  Plus,
  Cpu,
  Database,
  ArrowSquareOut,
} from '@phosphor-icons/react';

export default function Header({
  sidebarOpen,
  setSidebarOpen,
  onNewSession,
  llmHealth,
  dbHealth,
}) {
  const isHealthy = llmHealth?.status === 'healthy';
  const activeProvider = llmHealth?.provider || 'offline_fallback';
  const activeModel = llmHealth?.active_model || 'lenny-synthesizer-v1';

  return (
    <header className="h-16 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Sidebar Toggle & Brand Title */}
      <div className="flex items-center gap-3 sm:gap-4">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800/80 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          title={sidebarOpen ? 'Hide Sessions Sidebar' : 'Show Sessions Sidebar'}
        >
          <SidebarSimple size={20} weight="bold" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.2)]">
            <Sparkle size={18} weight="fill" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-bold text-white tracking-tight font-heading">
                The Lenny Growth Assistant
              </h1>
              <span className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                v2.0
              </span>
            </div>
            <p className="hidden md:block text-[11px] text-slate-400 font-sans">
              Strictly grounded in Lenny's Podcast transcripts
            </p>
          </div>
        </div>
      </div>

      {/* Right: LLM Health Status & New Session CTA */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* DB & LLM Health Indicator Pill */}
        <div
          className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono"
          title={`Provider: ${activeProvider} | Model: ${activeModel} | DB Engine: ${dbHealth?.engine || 'connected'}`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`}
          />
          <span className="text-slate-300 capitalize">{activeProvider.replace('_', ' ')}</span>
          <span className="text-slate-600">/</span>
          <span className="text-slate-400 truncate max-w-[110px]">{activeModel}</span>
        </div>

        {/* New Session Button */}
        <button
          onClick={onNewSession}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs rounded-lg transition-all shadow-[0_0_14px_rgba(16,185,129,0.25)] hover:shadow-[0_0_18px_rgba(16,185,129,0.4)] active:scale-[0.98]"
        >
          <Plus size={16} weight="bold" />
          <span>New Session</span>
        </button>
      </div>
    </header>
  );
}
