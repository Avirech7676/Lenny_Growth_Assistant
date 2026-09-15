import React, { useEffect, useRef, memo, useState } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import {
  Sparkle,
  Quotes,
  WarningCircle,
  Code,
  ArrowSquareOut,
  Lightning,
  Copy,
  Check,
  Flask,
  BookOpen,
  PenNib,
  ShieldCheck,
  Compass,
  Binoculars,
  PencilSimple,
  ArrowCounterClockwise,
  Cpu,
  Globe,
  MicrophoneStage,
  Wrench,
  Buildings,
} from '@phosphor-icons/react';

marked.setOptions({
  gfm: true,
  breaks: true,
});

// Module-level markdown renderer
const renderMarkdown = (text) => {
  const rawHtml = marked.parse(text || '');
  return { __html: DOMPurify.sanitize(rawHtml) };
};

// Category icon helper (Phosphor icons, no emoji)
const getCategoryIcon = (category, isExternal) => {
  if (isExternal) return <Globe size={11} weight="bold" className="text-cyan-400" />;
  return <MicrophoneStage size={11} weight="bold" className="text-cyan-400" />;
};

// ── Memoized ChatMessage: Only re-renders when this specific message data changes ──
const ChatMessage = memo(
  function ChatMessage({
    msg,
    onOpenArtifact,
    onInspectEvidence,
    onTriggerAction,
    onEditUserMessage,
    onRegenerate,
  }) {
    const [copied, setCopied] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [showTelemetry, setShowTelemetry] = useState(false);
    const [editContent, setEditContent] = useState(msg.content || '');
    const isUser = msg.role === 'user';
    const citations = Array.isArray(msg.citations) ? msg.citations : [];
    const artifacts = Array.isArray(msg.artifacts) ? msg.artifacts : [];
    const isRefusal =
      !isUser &&
      (msg.content?.includes("I don't have enough grounded evidence") ||
        msg.content?.includes('epistemic cutoff') ||
        msg.content?.includes('epistemic refusal') ||
        msg.content?.includes('available lenny transcript material'));

    const handleCopy = () => {
      if (!msg.content) return;
      navigator.clipboard.writeText(msg.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    return (
      <div
        className={`w-full max-w-3xl mx-auto py-3 sm:py-4 transition-all ${
          isUser ? 'flex justify-end' : 'flex justify-start'
        }`}
      >
        {isUser ? (
          /* User Message: Elegant Subtle Surface Pill with Inline Edit */
          <div className="group/user relative flex items-center gap-1.5 max-w-[85%] sm:max-w-[75%]">
            {!isEditing && onEditUserMessage && (
              <button
                onClick={() => {
                  setEditContent(msg.content);
                  setIsEditing(true);
                }}
                className="opacity-0 group/user:opacity-100 p-1 text-slate-500 hover:text-cyan-400 rounded hover:bg-slate-800 transition-all cursor-pointer shrink-0"
                title="Edit message"
              >
                <PencilSimple size={13} />
              </button>
            )}
            {isEditing ? (
              <div className="w-full bg-slate-900 border border-cyan-500/50 rounded-2xl p-2.5 space-y-2 shadow-lg">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full bg-transparent text-sm text-slate-100 resize-none focus:outline-none font-sans"
                  rows={Math.max(2, Math.min(6, editContent.split('\n').length))}
                  autoFocus
                />
                <div className="flex justify-end gap-2 text-xs font-mono">
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-2.5 py-1 text-slate-400 hover:text-white rounded cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (editContent.trim()) {
                        onEditUserMessage(msg.id, editContent.trim());
                        setIsEditing(false);
                      }
                    }}
                    className="px-2.5 py-1 bg-gradient-to-r from-cyan-400 to-violet-500 text-white font-bold rounded hover:opacity-90 transition-opacity cursor-pointer shadow-sm"
                  >
                    Save & Submit
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/80 border border-slate-700/60 text-slate-100 rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-sm leading-relaxed text-sm font-sans selection:bg-cyan-500 selection:text-slate-950">
                {msg.content}
              </div>
            )}
          </div>
        ) : (
          /* Assistant Message: Editorial Document Layout */
          <div className="w-full space-y-3 group">
            {/* Assistant Header Row: Identity, Mode Badge, Model Badge & Actions */}
            <div className="flex items-center justify-between text-xs pb-1 border-b border-slate-800/40">
              <div className="flex items-center gap-2 flex-wrap">
                <div className="w-6 h-6 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.3)]">
                  <Sparkle size={13} weight="fill" />
                </div>
                <span className="font-semibold text-white tracking-tight font-heading">
                  {(() => {
                    const cap = msg.capability || (
                      msg.mode === 'coding' ? 'coding' :
                      msg.mode === 'debugging' ? 'debugging' :
                      msg.mode === 'architecture' ? 'architecture' :
                      msg.mode === 'deep_research' ? 'deep_research' :
                      msg.mode === 'search' ? 'web_research' :
                      msg.mode === 'chat' ? 'general_qa' :
                      msg.mode === 'lenny' ? 'lenny_research' :
                      null
                    );
                    return cap === 'coding' || cap === 'debugging'
                      ? 'Code Intelligence'
                      : cap === 'architecture'
                      ? 'System Architect'
                      : cap === 'deep_research'
                      ? 'Deep Research Engine'
                      : cap === 'web_research'
                      ? 'Web Intelligence'
                      : cap === 'lenny_research' || cap === 'hybrid_research'
                      ? 'Lenny Growth Strategist'
                      : 'Lenny Growth Assistant';
                  })()}
                </span>

                {/* Capability or Intelligence Mode Badge */}
                {(() => {
                  const cap = msg.capability || (
                    msg.mode === 'coding' ? 'coding' :
                    msg.mode === 'debugging' ? 'debugging' :
                    msg.mode === 'architecture' ? 'architecture' :
                    msg.mode === 'deep_research' ? 'deep_research' :
                    msg.mode === 'search' ? 'web_research' :
                    msg.mode === 'chat' ? 'general_qa' :
                    msg.mode === 'lenny' ? 'lenny_research' :
                    null
                  );
                  if (cap) {
                    return (
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider border ${
                          cap === 'lenny_research'
                            ? 'bg-cyan-950/60 border-cyan-500/30 text-cyan-300'
                            : cap === 'hybrid_research'
                            ? 'bg-violet-950/60 border-violet-500/30 text-violet-300'
                            : cap === 'coding'
                            ? 'bg-indigo-950/60 border-indigo-500/30 text-indigo-300'
                            : cap === 'debugging'
                            ? 'bg-rose-950/60 border-rose-500/30 text-rose-300'
                            : cap === 'architecture'
                            ? 'bg-blue-950/60 border-blue-500/30 text-blue-300'
                            : cap === 'deep_research'
                            ? 'bg-purple-950/60 border-purple-500/30 text-purple-300'
                            : cap === 'general_qa'
                            ? 'bg-sky-950/60 border-sky-500/30 text-sky-300'
                            : 'bg-cyan-950/60 border-cyan-500/30 text-cyan-300'
                        }`}
                      >
                        {cap === 'lenny_research' ? (
                          <>
                            <MicrophoneStage size={11} weight="bold" /> Lenny Archive
                          </>
                        ) : cap === 'hybrid_research' ? (
                          <>
                            <Lightning size={11} weight="fill" /> Hybrid Strategy
                          </>
                        ) : cap === 'coding' ? (
                          <>
                            <Code size={11} weight="bold" /> Code Agent
                          </>
                        ) : cap === 'debugging' ? (
                          <>
                            <Wrench size={11} weight="bold" /> Debug Agent
                          </>
                        ) : cap === 'architecture' ? (
                          <>
                            <Buildings size={11} weight="bold" /> Architecture
                          </>
                        ) : cap === 'deep_research' ? (
                          <>
                            <Binoculars size={11} weight="bold" /> Deep Research
                          </>
                        ) : cap === 'general_qa' ? (
                          <>
                            <Lightning size={11} weight="bold" /> General QA
                          </>
                        ) : (
                          <>
                            <Globe size={11} weight="bold" /> Web Search
                          </>
                        )}
                      </span>
                    );
                  }
                  if (msg.intelligence_mode) {
                    return (
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider border ${
                          msg.intelligence_mode === 'lenny'
                            ? 'bg-cyan-950/60 border-cyan-500/30 text-cyan-300'
                            : msg.intelligence_mode === 'hybrid'
                            ? 'bg-violet-950/60 border-violet-500/30 text-violet-300'
                            : 'bg-cyan-950/60 border-cyan-500/30 text-cyan-300'
                        }`}
                      >
                        {msg.intelligence_mode === 'lenny' ? (
                          <>
                            <MicrophoneStage size={11} weight="bold" /> Lenny Archive
                          </>
                        ) : msg.intelligence_mode === 'hybrid' ? (
                          <>
                            <Lightning size={11} weight="fill" /> Hybrid Strategy
                          </>
                        ) : (
                          <>
                            <Globe size={11} weight="bold" /> Real-World
                          </>
                        )}
                      </span>
                    );
                  }
                  return null;
                })()}

                {/* Model Engine Badge */}
                {(msg.model || msg.latency_metrics?.model) && (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold tracking-wider border bg-slate-900 border-slate-700/80 text-cyan-300 shadow-sm"
                    title={`Engine: ${msg.model || msg.latency_metrics?.model} (${msg.provider || msg.latency_metrics?.provider || 'active'})`}
                  >
                    <Cpu size={11} className="text-cyan-400" />
                    <span>{msg.model || msg.latency_metrics?.model}</span>
                  </span>
                )}

                {/* Cross-Model Transition / Circuit Breaker Cascade Badge */}
                {msg.model_transition && (
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold tracking-wider border bg-amber-950/50 border-amber-500/40 text-amber-300 shadow-sm animate-pulse"
                    title={`Cross-Model Transition / Cascaded from ${msg.model_transition.from_model} to ${msg.model_transition.to_model}`}
                  >
                    <Lightning size={11} weight="fill" className="text-amber-400" />
                    <span>{msg.model_transition.from_model} → {msg.model_transition.to_model}</span>
                  </span>
                )}

                {/* Research Depth Badge */}
                {msg.research_depth && msg.research_depth !== 'direct' && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold uppercase tracking-wider border bg-slate-900 border-cyan-500/30 text-cyan-400">
                    {msg.research_depth === 'deep' ? (
                      <>
                        <Binoculars size={11} weight="bold" /> Deep Research
                      </>
                    ) : (
                      <>
                        <Globe size={11} weight="bold" /> Web Research
                      </>
                    )}
                  </span>
                )}

                {/* Evidence Strength Badge */}
                {msg.evidence_strength && (
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold tracking-wider border ${
                    msg.evidence_strength === 'Strong'
                      ? 'bg-cyan-950/40 border-cyan-500/30 text-cyan-300'
                      : msg.evidence_strength === 'Moderate'
                      ? 'bg-violet-950/40 border-violet-500/30 text-violet-300'
                      : 'bg-amber-950/40 border-amber-500/30 text-amber-300'
                  }`}>
                    {msg.evidence_strength === 'Strong' ? (
                      <>
                        <ShieldCheck size={11} weight="bold" /> Strong Evidence
                      </>
                    ) : msg.evidence_strength === 'Moderate' ? (
                      <>
                        <ShieldCheck size={11} weight="regular" /> Moderate Evidence
                      </>
                    ) : (
                      <>
                        <WarningCircle size={11} weight="bold" /> Limited Evidence
                      </>
                    )}
                  </span>
                )}

                {/* Quality Gate Badge */}
                {msg.quality_score != null && (
                  <span
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-mono font-semibold tracking-wider border ${
                      msg.quality_passed !== false
                        ? 'bg-cyan-950/50 border-cyan-500/30 text-cyan-300'
                        : 'bg-amber-950/50 border-amber-500/30 text-amber-300'
                    }`}
                    title={`Quality Gate Score: ${Math.round(msg.quality_score * 100)}%`}
                  >
                    <Sparkle size={11} weight="fill" className="text-cyan-400" />
                    <span>Verified {Math.round(msg.quality_score * 100)}%</span>
                  </span>
                )}
              </div>

              {/* Message Hover Actions (Telemetry HUD, Copy, Regenerate) */}
              <div className="flex items-center gap-1.5">
                {/* Interactive Telemetry HUD Pill & Popover */}
                {msg.latency_metrics && (
                  <div className="relative">
                    <button
                      onClick={() => setShowTelemetry(!showTelemetry)}
                      className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/40 text-[10px] font-mono text-slate-400 hover:text-cyan-300 transition-all cursor-pointer shadow-sm"
                      title="Click to inspect token velocity & latency metrics"
                    >
                      <Lightning size={11} className="text-cyan-400" weight="fill" />
                      <span>{Math.round(msg.latency_metrics.ttft_ms)}ms TTFT</span>
                      {msg.latency_metrics.tokens_per_sec > 0 && (
                        <>
                          <span className="text-slate-600">•</span>
                          <span className="text-cyan-300 font-semibold">{Math.round(msg.latency_metrics.tokens_per_sec)} tok/s</span>
                        </>
                      )}
                    </button>

                    {showTelemetry && (
                      <div className="absolute right-0 top-full mt-1.5 z-50 w-72 bg-[#0B101E] border border-slate-700/90 rounded-xl p-3 shadow-2xl text-[11px] font-mono space-y-2 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150">
                        <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 text-slate-400">
                          <span className="font-bold text-white flex items-center gap-1.5">
                            <Lightning size={13} className="text-cyan-400" weight="fill" />
                            Streaming Telemetry HUD
                          </span>
                          <button
                            onClick={() => setShowTelemetry(false)}
                            className="text-slate-500 hover:text-white p-0.5 cursor-pointer"
                          >
                            ✕
                          </button>
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80">
                            <span className="text-slate-500 block">Time to First Token</span>
                            <span className="text-cyan-300 font-bold text-xs">{Math.round(msg.latency_metrics.ttft_ms)} ms</span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80">
                            <span className="text-slate-500 block">Token Velocity</span>
                            <span className="text-cyan-300 font-bold text-xs">
                              {msg.latency_metrics.tokens_per_sec ? `${Math.round(msg.latency_metrics.tokens_per_sec)} tok/s` : 'N/A'}
                            </span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80">
                            <span className="text-slate-500 block">Retrieval Latency</span>
                            <span className="text-cyan-400 font-semibold">{msg.latency_metrics.retrieval_ms ? `${Math.round(msg.latency_metrics.retrieval_ms)} ms` : '< 50 ms'}</span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800/80">
                            <span className="text-slate-500 block">Total Turn Duration</span>
                            <span className="text-slate-200 font-semibold">{msg.latency_metrics.total_ms ? `${(msg.latency_metrics.total_ms / 1000).toFixed(2)} s` : 'N/A'}</span>
                          </div>
                        </div>

                        <div className="pt-1 border-t border-slate-800/80 text-[10px] space-y-0.5 text-slate-400">
                          <div className="flex justify-between">
                            <span>Active Model:</span>
                            <span className="text-slate-200 font-medium">{msg.model || msg.latency_metrics.model || 'Auto'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Provider Engine:</span>
                            <span className="text-cyan-300 uppercase font-medium">{msg.provider || msg.latency_metrics.provider || 'cloud'}</span>
                          </div>
                          {msg.latency_metrics.token_count > 0 && (
                            <div className="flex justify-between">
                              <span>Tokens Generated:</span>
                              <span className="text-slate-200">{msg.latency_metrics.token_count}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {onRegenerate && !msg.isStreaming && (
                  <button
                    onClick={() => onRegenerate(msg.id)}
                    className="p-1 text-slate-400 hover:text-cyan-400 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                    title="Regenerate Response"
                    aria-label="Regenerate Response"
                  >
                    <ArrowCounterClockwise size={13} />
                  </button>
                )}
                <button
                  onClick={handleCopy}
                  className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors cursor-pointer"
                  title="Copy Response"
                  aria-label="Copy Response"
                >
                  {copied ? (
                    <Check size={13} className="text-cyan-400" />
                  ) : (
                    <Copy size={13} />
                  )}
                </button>
              </div>
            </div>

            {/* Epistemic Refusal Banner */}
            {isRefusal && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                <WarningCircle size={17} className="shrink-0 mt-0.5 text-amber-400" weight="bold" />
                <div className="space-y-0.5">
                  <span className="font-semibold block text-amber-200">
                    Epistemic Cutoff Applied
                  </span>
                  <p className="text-amber-300/90 leading-relaxed">
                    This query lacked grounded evidence in Lenny's indexed corpus and fell outside current domain research. The assistant refuses to fabricate unsupported advice.
                  </p>
                </div>
              </div>
            )}

            {/* Markdown Body (Editorial Prose) */}
            <div
              className="prose-lenny pl-0.5"
              dangerouslySetInnerHTML={renderMarkdown(msg.content || (msg.isStreaming ? ' ' : ''))}
            />

            {/* Streaming Active Cursor */}
            {msg.isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-cyan-400 animate-pulse ml-1 align-middle rounded-sm" />
            )}

            {/* Prominent Grounded Evidence Card */}
            {citations.length > 0 && (
              <div className="mt-4 pt-3 border-t border-slate-800/80 bg-[#0E1526]/80 border border-slate-800/80 rounded-xl p-3 space-y-2 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Quotes size={14} className="text-cyan-400" weight="fill" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                      Grounded Evidence ({citations.length} sources)
                    </span>
                  </div>
                  <button
                    onClick={() => onInspectEvidence(citations)}
                    className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1 hover:underline cursor-pointer"
                  >
                    <span>Inspect Sources</span>
                    <ArrowSquareOut size={12} weight="bold" />
                  </button>
                </div>

                {/* Evidence Source Badges Grid */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {citations.map((c, idx) => {
                    const simScore = Math.round((c.similarity || 0) * 100);
                    const isExternal = c.source_type === 'external';
                    const icon = getCategoryIcon(c.source_category, isExternal);
                    return (
                      <button
                        key={idx}
                        onClick={() => onInspectEvidence(citations)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono border transition-all cursor-pointer ${
                          isExternal
                            ? 'bg-cyan-950/50 border-cyan-500/30 text-cyan-300 hover:border-cyan-400 hover:bg-cyan-900/40'
                            : 'bg-slate-900 border-slate-700/60 text-slate-300 hover:border-cyan-500/50 hover:bg-slate-800'
                        }`}
                        title={c.why_useful ? `${c.why_useful} • ${c.title}` : (c.excerpt ? `"${c.excerpt}"` : c.title)}
                      >
                        <span>{icon}</span>
                        <span className={isExternal ? 'text-cyan-300 font-semibold' : 'text-violet-300 font-semibold'}>
                          {isExternal ? (c.domain || 'External') : (c.guest?.split(' ')?.[1] || c.guest)}
                        </span>
                        {c.source_category && isExternal && (
                          <span className="text-[10px] text-slate-400 font-mono">
                            [{c.source_category}]
                          </span>
                        )}
                        <span className="text-slate-500">•</span>
                        <span className="text-slate-300">{simScore}%</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Generated Artifacts Callout */}
            {artifacts.length > 0 && (
              <div className="mt-3 space-y-2">
                {artifacts.map((art) => (
                  <div
                    key={art.id}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-900/90 border border-cyan-500/35 shadow-[0_0_12px_rgba(6,182,212,0.15)]"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 flex items-center justify-center">
                        <Code size={16} weight="bold" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white block">
                          {art.title || 'Operational Deliverable'}
                        </span>
                        <span className="text-[10px] font-mono text-cyan-300/90 uppercase tracking-wide">
                          {art.artifact_type} • Interactive Sandbox Ready
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => onOpenArtifact(art.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white transition-all shadow-[0_0_12px_rgba(6,182,212,0.3)] active:scale-95 cursor-pointer"
                    >
                      <span>Open in Workspace</span>
                      <ArrowSquareOut size={13} weight="bold" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Contextual Follow-up Actions (Progressive Disclosure) */}
            {!msg.isStreaming && !isRefusal && onTriggerAction && (
              <div className="pt-2 flex flex-wrap items-center gap-1.5 opacity-80 hover:opacity-100 transition-opacity">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mr-1">
                  Next Step:
                </span>
                <button
                  onClick={() =>
                    onTriggerAction(
                      `Turn the previous response into an actionable ICE growth experiment with measurable hypotheses and guardrail metrics.`,
                      'experiments'
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-cyan-400 border border-slate-800 transition-colors cursor-pointer"
                >
                  <Flask size={12} />
                  <span>Turn into Experiment</span>
                </button>
                <button
                  onClick={() =>
                    onTriggerAction(
                      `Build a complete 4-pillar operational playbook based on this strategy.`,
                      'playbooks'
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-cyan-400 border border-slate-800 transition-colors cursor-pointer"
                >
                  <BookOpen size={12} />
                  <span>Build Playbook</span>
                </button>
                <button
                  onClick={() =>
                    onTriggerAction(
                      `Write a Ship 30 for 30 viral essay summarizing the core principles from this strategy.`,
                      'ship30'
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-violet-400 border border-slate-800 transition-colors cursor-pointer"
                >
                  <PenNib size={12} />
                  <span>Write Ship 30</span>
                </button>
              </div>
            )}

            {/* Dynamic Contextual Follow-up Questions */}
            {!msg.isStreaming && !isRefusal && msg.follow_up_suggestions && msg.follow_up_suggestions.length > 0 && (
              <div className="pt-2.5 space-y-1.5">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
                  Suggested Follow-ups:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {msg.follow_up_suggestions.map((sug, idx) => (
                    <button
                      key={idx}
                      onClick={() => onTriggerAction && onTriggerAction(sug, 'chat')}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs bg-slate-900/90 hover:bg-cyan-950/40 text-slate-300 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-all shadow-sm cursor-pointer text-left font-sans"
                    >
                      <span className="text-cyan-400 font-bold">↳</span>
                      <span>{sug}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  },
  (prevProps, nextProps) => {
    const pm = prevProps.msg;
    const nm = nextProps.msg;
    return (
      pm.id === nm.id &&
      pm.content === nm.content &&
      pm.isStreaming === nm.isStreaming &&
      pm.intelligence_mode === nm.intelligence_mode &&
      pm.model === nm.model &&
      pm.provider === nm.provider &&
      JSON.stringify(pm.model_transition) === JSON.stringify(nm.model_transition) &&
      pm.quality_score === nm.quality_score &&
      pm.quality_passed === nm.quality_passed &&
      pm.latency_metrics === nm.latency_metrics &&
      pm.latency_ms === nm.latency_ms &&
      JSON.stringify(pm.citations) === JSON.stringify(nm.citations) &&
      JSON.stringify(pm.artifacts) === JSON.stringify(nm.artifacts) &&
      JSON.stringify(pm.follow_up_suggestions) === JSON.stringify(nm.follow_up_suggestions)
    );
  }
);

export default function ChatWindow({
  messages = [],
  isLoading = false,
  streamingPhase = null,
  researchProgress = null,
  onSelectStarterPrompt,
  onOpenArtifact,
  onInspectEvidence,
  onEditUserMessage,
  onRegenerate,
}) {
  const containerRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [messages, isLoading, streamingPhase, researchProgress]);

  const starterPrompts = [
    {
      title: 'Current Events & Facts',
      prompt: 'Who is the Chief Minister of Andhra Pradesh?',
      mode: 'search',
      category: 'Web Search',
      icon: Globe,
    },
    {
      title: 'Autonomous Deep Research',
      prompt: 'Conduct a deep research report on state-of-the-art AI agent frameworks and production reliability in 2026.',
      mode: 'deep_research',
      category: 'Deep Research',
      icon: Binoculars,
    },
    {
      title: 'Code & Software Architecture',
      prompt: 'Write an async Python connection pool with exponential backoff, circuit breaker, and FastAPI health checks.',
      mode: 'coding',
      category: 'Software Engineering',
      icon: Code,
    },
    {
      title: 'Brian Chesky: Founder Mode',
      prompt: "Explain Brian Chesky's founder mode and why excessive A/B testing can kill bold product design.",
      mode: 'lenny',
      category: 'Growth & Strategy',
      icon: MicrophoneStage,
    },
  ];

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-3 space-y-4">
      {messages.length === 0 ? (
        /* Empty State: High-Agency General AI Platform Hero with ThreeUI Topology Field */
        <div className="relative max-w-2xl mx-auto py-2 sm:py-4 space-y-4 text-center">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-400 via-sky-500 to-fuchsia-500 p-0.5 shadow-[0_0_20px_rgba(56,189,248,0.45)] mx-auto">
              <div className="w-full h-full bg-[#070913] rounded-[10px] flex items-center justify-center">
                <Sparkle size={20} weight="fill" className="text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.85)]" />
              </div>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold font-heading text-white tracking-tight">
              The Lenny Growth Assistant
            </h2>
            <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed font-sans">
              Authoritative AI growth strategist and operational advisory system strictly grounded in Lenny's Podcast transcripts with interactive execution artifacts.
            </p>
          </div>

          {/* Capabilities Summary Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
              <Compass size={13} className="text-cyan-400" />
              Real-Time Web Intelligence
            </span>
            <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
              <Binoculars size={13} className="text-purple-400" />
              Autonomous Deep Research
            </span>
            <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
              <Code size={13} className="text-indigo-400" />
              Code & Repository Inspector
            </span>
            <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
              <ShieldCheck size={13} className="text-cyan-400" />
              Quality Verification Gate
            </span>
          </div>

          {/* Categorized Starter Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left pt-2">
            {starterPrompts.map((sp) => {
              const IconComp = sp.icon;
              return (
                <button
                  key={sp.title}
                  onClick={() => onSelectStarterPrompt(sp.prompt, sp.mode)}
                  className="p-3.5 bg-slate-900/70 hover:bg-slate-900 border border-slate-800/80 hover:border-cyan-500/40 rounded-xl transition-all group text-left cursor-pointer shadow-sm hover:shadow-md active:scale-[0.98]"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-300 group-hover:bg-cyan-500/25 group-hover:border-cyan-500/50 transition-colors shrink-0">
                        <IconComp size={13} weight="bold" />
                      </div>
                      <span className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors font-heading">
                        {sp.title}
                      </span>
                    </div>
                    <span className="text-[9px] font-mono text-slate-500 uppercase">
                      {sp.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {sp.prompt}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        /* Conversation Stream */
        messages.map((m) => (
          <ChatMessage
            key={m.id}
            msg={m}
            onOpenArtifact={onOpenArtifact}
            onInspectEvidence={onInspectEvidence}
            onTriggerAction={onSelectStarterPrompt}
            onEditUserMessage={onEditUserMessage}
            onRegenerate={onRegenerate}
          />
        ))
      )}

      {/* Real-time Streaming Activity & Adaptive Research Progress */}
      {isLoading && (
        <div className="max-w-3xl mx-auto py-2 space-y-2.5">
          {/* Research Progress Card */}
          {researchProgress && (
            <div className="p-3.5 rounded-xl bg-[#0C1322] border border-cyan-500/30 shadow-lg space-y-2.5 animate-in fade-in duration-200">
              <div className="flex items-center justify-between text-xs pb-1 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  <span className="font-bold text-cyan-300 font-mono tracking-wide uppercase text-[11px] flex items-center gap-1.5">
                    {researchProgress.depth === 'deep' ? (
                      <>
                        <Binoculars size={13} weight="bold" /> Multi-Query Deep Research
                      </>
                    ) : (
                      <>
                        <Globe size={13} weight="bold" /> Real-World Web Research
                      </>
                    )}
                  </span>
                  {researchProgress.domain && (
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700/60">
                      {researchProgress.domain}
                    </span>
                  )}
                </div>
                {researchProgress.sub_queries && (
                  <span className="text-[10px] font-mono text-slate-400">
                    {researchProgress.searched_queries?.length || 0} / {researchProgress.sub_queries.length} queries completed
                  </span>
                )}
              </div>

              {/* Sub-queries Checklist */}
              {researchProgress.sub_queries && researchProgress.sub_queries.length > 0 && (
                <div className="space-y-1.5 pt-0.5">
                  {researchProgress.sub_queries.map((sq, i) => {
                    const isSearched = researchProgress.searched_queries?.includes(sq);
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs font-mono">
                        <span className={`w-4 h-4 rounded-md flex items-center justify-center text-[10px] font-bold ${
                          isSearched
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                            : 'bg-slate-800 text-cyan-300 border border-cyan-500/30 animate-pulse'
                        }`}>
                          {isSearched ? '✓' : '•'}
                        </span>
                        <span className={isSearched ? 'text-slate-300' : 'text-cyan-300/80 italic font-medium'}>
                          {sq}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Discovered Sources summary count */}
              {researchProgress.sources_found > 0 && (
                <div className="text-[10px] font-mono text-cyan-300 flex items-center gap-1.5 pt-1.5 border-t border-slate-800/80">
                  <Check size={12} weight="bold" />
                  <span>Discovered {researchProgress.sources_found} authoritative sources across verified categories</span>
                </div>
              )}
            </div>
          )}

          {/* Shimmer Status */}
          <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-mono text-cyan-300 animate-shimmer shadow-sm">
            <Sparkle size={14} className="animate-spin text-cyan-400" />
            <span>{streamingPhase || 'Reasoning and synthesizing evidence...'}</span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
