import React, { useState } from 'react';
import {
  Sparkle,
  SidebarSimple,
  Plus,
  Layout,
  Code,
  Quotes,
  CaretDown,
  Cpu,
  Check,
  ArrowsClockwise,
  Lightning,
  Circle,
} from '@phosphor-icons/react';

// Fallback baseline choices if API has not responded yet
const DEFAULT_MODEL_CHOICES = [
  { id: '', name: 'Auto Router', provider: 'Smart Selection', desc: 'Autonomous routing based on query complexity', available: true },
  { id: 'gemini', name: 'Gemini 3.5 Flash', provider: 'Google', desc: '1M context, multimodal & deep reasoning', available: true },
  { id: 'groq', name: 'Groq Llama 3.3 70B', provider: 'Groq', desc: 'Ultra-low latency, high throughput', available: true },
  { id: 'ollama', name: 'Local Ollama', provider: 'Ollama', desc: 'Private local offline execution', available: false },
  { id: 'openai', name: 'GPT-4o', provider: 'OpenAI', desc: 'General-purpose knowledge', available: false },
  { id: 'anthropic', name: 'Claude 3.5 Sonnet', provider: 'Anthropic', desc: 'System architecture & synthesis', available: false },
];

export default function Header({
  sidebarOpen,
  setSidebarOpen,
  onNewSession,
  onGoHome,
  onGoLanding,
  llmHealth,
  dbHealth,
  activeSessionTitle,
  workspaceOpen,
  onToggleWorkspace,
  artifactCount = 0,
  evidenceCount = 0,
  selectedProvider = '',
  onChangeProvider,
  availableModels = [],
  onDiscoverModels,
  isDiscovering = false,
}) {
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const isHealthy = llmHealth?.status === 'healthy';
  const activeProvider = llmHealth?.provider || 'gemini';

  // Build options list dynamically from availableModels if present
  let modelChoices = DEFAULT_MODEL_CHOICES;
  if (Array.isArray(availableModels) && availableModels.length > 0) {
    const autoOption = {
      id: '',
      name: 'Auto Router',
      provider: 'Intelligent',
      desc: 'Autonomous affinity routing based on task domain',
      available: true,
      context_window: 1000000,
    };

    const mapped = availableModels.map((m) => {
      const p = m.provider || 'custom';
      const providerLabel = p === 'gemini' ? 'Google' : p === 'groq' ? 'Groq' : p === 'ollama' ? 'Ollama' : p.charAt(0).toUpperCase() + p.slice(1);
      return {
        id: p,
        model_id: m.model_id,
        name: m.display_name || m.model_id,
        provider: providerLabel,
        desc: `${m.context_window ? `${Math.round(m.context_window / 1000)}k ctx` : ''} • ${m.latency_tier || 'standard'} latency`,
        available: Boolean(m.is_available),
        context_window: m.context_window,
      };
    });

    // Deduplicate or combine
    modelChoices = [autoOption, ...mapped];
  }

  // Find active display choice
  const currentChoice =
    modelChoices.find((m) => m.id === selectedProvider || m.model_id === selectedProvider) ||
    modelChoices[0];

  return (
    <header className="h-14 border-b border-white/10 bg-black/60 backdrop-blur-md px-3 sm:px-5 flex items-center justify-between sticky top-0 z-30 shrink-0">
      {/* Left: Sidebar Toggle & Brand Title Button */}
      <div className="flex items-center gap-2.5 sm:gap-3.5">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800/80 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500/30 cursor-pointer"
          title={sidebarOpen ? 'Hide Conversations Sidebar' : 'Show Conversations Sidebar'}
          aria-label="Toggle Sidebar"
        >
          <SidebarSimple size={18} weight="bold" />
        </button>

        {/* Brand Home / Landing Button */}
        <button
          onClick={onGoLanding || onGoHome}
          id="home-dashboard-btn"
          className="flex items-center gap-2 text-left group hover:opacity-95 transition-all focus:outline-none focus:ring-2 focus:ring-cyan-500/40 rounded-lg p-1 -m-1 cursor-pointer bg-transparent border-0"
          title="Return to Dashboard & System Overview"
        >
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-400 via-sky-500 to-fuchsia-500 p-0.5 shadow-[0_0_16px_rgba(56,189,248,0.45)] group-hover:scale-105 group-hover:shadow-[0_0_24px_rgba(192,132,252,0.65)] transition-all shrink-0">
            <div className="w-full h-full bg-[#070913] rounded-[10px] flex items-center justify-center">
              <Sparkle size={16} weight="fill" className="text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.85)]" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white tracking-tight font-heading group-hover:text-cyan-300 transition-colors">
                The Lenny Growth Assistant
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.2)]">
                v1.0
              </span>
              <span className="hidden sm:inline-block px-2 py-0.5 text-[9px] font-mono font-medium rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/35 tracking-wider">
                EVIDENCE-GROUNDED AI
              </span>
            </div>
          </div>
        </button>

        {/* Active Session Title Breadcrumb */}
        {activeSessionTitle && (
          <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400 pl-3 border-l border-slate-800">
            <span className="text-slate-600">/</span>
            <span className="truncate max-w-[220px] text-slate-300 font-medium font-sans">
              {activeSessionTitle}
            </span>
          </div>
        )}
      </div>

      {/* Right: Model Selector, Telemetry Health Pill, Workspace Toggle & New Session CTA */}
      <div className="flex items-center gap-2 sm:gap-2.5">
        {/* Dynamic Model Platform Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900/90 hover:bg-slate-800/80 border border-slate-800 text-xs font-mono text-slate-300 hover:text-white transition-all cursor-pointer"
            title="Switch Active AI Model / Provider"
          >
            <Cpu size={14} className="text-cyan-400" />
            <span className="font-semibold text-cyan-300 truncate max-w-[130px] sm:max-w-[180px]">
              {currentChoice.name}
            </span>
            <CaretDown size={11} className="text-slate-500" />
          </button>

          {modelDropdownOpen && (
            <div className="absolute right-0 top-full mt-1.5 z-50 w-80 bg-[#0E1526] border border-slate-700/80 rounded-xl p-1.5 shadow-2xl text-xs font-sans backdrop-blur-xl">
              {/* Dropdown Header */}
              <div className="px-2.5 py-1.5 text-[10px] uppercase font-mono font-semibold text-slate-400 border-b border-slate-800 mb-1 flex items-center justify-between">
                <span>Model Engine Platform</span>
                <span className="text-sky-400 font-normal">Active: {activeProvider}</span>
              </div>

              {/* Models List */}
              <div className="max-h-72 overflow-y-auto space-y-0.5 pr-0.5">
                {modelChoices.map((choice, idx) => {
                  const isSelected = selectedProvider === choice.id || (choice.model_id && selectedProvider === choice.model_id);
                  return (
                    <button
                      key={`${choice.id}-${choice.model_id || idx}`}
                      onClick={() => {
                        if (onChangeProvider) onChangeProvider(choice.id);
                        setModelDropdownOpen(false);
                      }}
                      className={`w-full text-left px-2.5 py-2 rounded-lg transition-all flex items-start justify-between cursor-pointer ${
                        isSelected
                          ? 'bg-cyan-500/15 border border-cyan-500/35 text-white shadow-[0_0_12px_rgba(6,182,212,0.18)]'
                          : 'hover:bg-slate-800/80 text-slate-300 hover:text-white border border-transparent'
                      }`}
                    >
                      <div className="min-w-0 pr-2">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {/* Availability status dot */}
                          <span
                            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                              choice.available ? 'bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]' : 'bg-slate-600'
                            }`}
                          />
                          <span className={`font-semibold truncate ${isSelected ? 'text-cyan-300' : 'text-slate-200'}`}>
                            {choice.name}
                          </span>
                          <span className="text-[9px] font-mono text-slate-400 px-1 py-0.2 bg-slate-800/80 rounded border border-slate-700/50">
                            {choice.provider}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-snug truncate">{choice.desc}</p>
                      </div>
                      {isSelected && <Check size={14} className="text-cyan-400 shrink-0 mt-0.5" />}
                    </button>
                  );
                })}
              </div>

              {/* Dropdown Footer: Live Model Discovery Trigger */}
              <div className="pt-1.5 mt-1 border-t border-slate-800 flex items-center justify-between px-1">
                <span className="text-[10px] font-mono text-slate-500">
                  {modelChoices.length - 1} models discovered
                </span>
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (onDiscoverModels) {
                      await onDiscoverModels();
                    }
                  }}
                  disabled={isDiscovering}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-all border border-cyan-500/25 cursor-pointer disabled:opacity-50"
                  title="Query local Ollama and Cloud APIs for available models"
                >
                  <ArrowsClockwise size={11} className={isDiscovering ? 'animate-spin' : ''} />
                  <span>{isDiscovering ? 'Discovering...' : 'Refresh Models'}</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Telemetry Health Pill */}
        <div
          className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-[11px] font-mono"
          title={`Status: ${isHealthy ? 'Connected' : 'Offline'} | Engine: ${activeProvider} | DB: ${dbHealth?.engine || 'connected'}`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isHealthy ? 'bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]' : 'bg-amber-400'
            }`}
          />
          <span className="text-slate-400 text-[10px]">{isHealthy ? 'Live' : 'Degraded'}</span>
        </div>

        {/* Workspace Toggle Button */}
        {(artifactCount > 0 || evidenceCount > 0) && (
          <button
            onClick={onToggleWorkspace}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all border cursor-pointer ${
              workspaceOpen
                ? 'bg-violet-500/20 text-violet-300 border-violet-500/40 shadow-[0_0_12px_rgba(168,85,247,0.25)]'
                : 'bg-slate-900 text-slate-300 hover:text-white border-slate-800 hover:border-slate-700'
            }`}
            title={workspaceOpen ? 'Close Context Workspace' : 'Open Context Workspace'}
            aria-label="Toggle Context Workspace"
          >
            <Layout size={14} weight="bold" />
            <span className="hidden sm:inline">Workspace</span>
            {artifactCount > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] font-mono text-cyan-300 bg-cyan-500/20 px-1 rounded">
                <Code size={10} />
                {artifactCount}
              </span>
            )}
            {evidenceCount > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] font-mono text-violet-300 bg-violet-500/20 px-1 rounded">
                <Quotes size={10} />
                {evidenceCount}
              </span>
            )}
          </button>
        )}

        {/* Dashboard Navigation Button */}
        <button
          onClick={onGoLanding}
          id="header-landing-page-btn"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer shadow-sm active:scale-95"
          title="Explore System Overview & Dashboard"
        >
          <Sparkle size={13} className="text-cyan-400" weight="fill" />
          <span className="hidden sm:inline">Dashboard</span>
        </button>

        {/* New Session Button */}
        <button
          onClick={onNewSession}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-cyan-500 via-indigo-600 to-violet-600 hover:from-cyan-400 hover:via-indigo-500 hover:to-violet-500 text-white font-semibold text-xs rounded-lg transition-all shadow-[0_0_18px_rgba(6,182,212,0.35)] hover:shadow-[0_0_24px_rgba(168,85,247,0.5)] active:scale-[0.98] cursor-pointer"
          title="Create New Conversation"
          aria-label="New Conversation"
        >
          <Plus size={14} weight="bold" />
          <span>New Chat</span>
        </button>
      </div>
    </header>
  );
}

