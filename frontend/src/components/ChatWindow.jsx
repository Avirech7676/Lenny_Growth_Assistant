import React, { useEffect, useRef } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import {
  User,
  Sparkle,
  Quotes,
  WarningCircle,
  Code,
  ArrowSquareOut,
  Lightning,
  Clock,
} from '@phosphor-icons/react';

// Configure marked options
marked.setOptions({
  gfm: true,
  breaks: true,
});

export default function ChatWindow({
  messages = [],
  isLoading = false,
  onSelectStarterPrompt,
  onOpenArtifact,
  onInspectEvidence,
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const renderMarkdown = (text) => {
    const rawHtml = marked.parse(text || '');
    return { __html: DOMPurify.sanitize(rawHtml) };
  };

  const starterPrompts = [
    {
      title: 'Brian Chesky: Founder Mode',
      prompt: 'Explain Brian Chesky\'s founder mode and why excessive A/B testing can kill bold product design.',
      mode: 'research',
      icon: '🏛️',
    },
    {
      title: 'Shreyas Doshi: LNO Framework',
      prompt: 'Write a Ship 30 for 30 essay on Shreyas Doshi\'s LNO framework for product leader prioritization.',
      mode: 'ship30',
      icon: '✍️',
    },
    {
      title: 'Activation Funnel ICE Test',
      prompt: 'Generate an ICE growth experiment to improve signup-to-activation conversion by removing upfront paywalls.',
      mode: 'experiments',
      icon: '🧪',
    },
    {
      title: '4-Pillars Operational Playbook',
      prompt: 'Build a comprehensive 4-pillar growth playbook (Acquisition, Activation, Retention, Monetization) for B2B SaaS.',
      mode: 'playbooks',
      icon: '📋',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
      {messages.length === 0 ? (
        /* Starter Prompts / Welcome View */
        <div className="max-w-2xl mx-auto py-8 sm:py-12 space-y-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto shadow-[0_0_24px_rgba(16,185,129,0.2)]">
            <Sparkle size={28} weight="fill" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl sm:text-2xl font-bold font-heading text-white tracking-tight">
              Evidence-Grounded Growth Advisory
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed font-sans">
              Strictly grounded in Lenny's Podcast transcripts. Bounded skills include deep research citations, Ship 30 viral essays, ICE experiment generators, and 4-pillar playbooks.
            </p>
          </div>

          {/* Starter Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left">
            {starterPrompts.map((sp) => (
              <button
                key={sp.title}
                onClick={() => onSelectStarterPrompt(sp.prompt, sp.mode)}
                className="p-4 bg-slate-900/80 border border-slate-800/90 hover:border-emerald-500/40 rounded-xl transition-all group hover:bg-slate-900 shadow-sm cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-base">{sp.icon}</span>
                  <span className="text-xs font-bold text-slate-200 group-hover:text-emerald-400 transition-colors font-heading">
                    {sp.title}
                  </span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {sp.prompt}
                </p>
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* Message Stream */
        messages.map((msg) => {
          const isUser = msg.role === 'user';
          const citations = Array.isArray(msg.citations) ? msg.citations : [];
          const artifacts = Array.isArray(msg.artifacts) ? msg.artifacts : [];
          const isRefusal =
            !isUser &&
            (msg.content.includes("I don't have enough grounded evidence") ||
              msg.content.includes('epistemic cutoff'));

          return (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-4xl mx-auto ${
                isUser ? 'justify-end' : 'justify-start'
              }`}
            >
              {/* Assistant Avatar */}
              {!isUser && (
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-1 shadow-sm">
                  <Sparkle size={16} weight="fill" />
                </div>
              )}

              {/* Message Bubble */}
              <div
                className={`space-y-3 rounded-2xl p-4 sm:p-5 max-w-[85%] ${
                  isUser
                    ? 'bg-emerald-600 text-white rounded-tr-sm shadow-md'
                    : 'bg-slate-900/90 border border-slate-800 text-slate-100 rounded-tl-sm shadow-lg'
                }`}
              >
                {/* Epistemic Refusal Banner */}
                {isRefusal && (
                  <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                    <WarningCircle size={18} className="shrink-0 mt-0.5" weight="bold" />
                    <div>
                      <span className="font-semibold block mb-0.5">
                        Epistemic Refusal Gate Triggered
                      </span>
                      <span>
                        The query fell below our hybrid retrieval threshold (cutoff ≥ 0.28). Lenny Assistant refuses to hallucinate ungrounded growth advice.
                      </span>
                    </div>
                  </div>
                )}

                {/* Message Body Content */}
                <div
                  className="prose-lenny"
                  dangerouslySetInnerHTML={renderMarkdown(msg.content)}
                />

                {/* Artifact Action Callout (if any generated in this message) */}
                {artifacts.length > 0 && (
                  <div className="pt-2 border-t border-slate-800 space-y-2">
                    {artifacts.map((art) => (
                      <div
                        key={art.id}
                        className="flex items-center justify-between p-3 rounded-xl bg-slate-950/80 border border-emerald-500/30"
                      >
                        <div className="flex items-center gap-2">
                          <Code size={18} className="text-emerald-400" />
                          <div>
                            <span className="text-xs font-semibold text-white block">
                              {art.title || 'Operational Artifact'}
                            </span>
                            <span className="text-[10px] font-mono text-emerald-400/80 uppercase">
                              {art.artifact_type} • Sandboxed
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => onOpenArtifact(art.id)}
                          className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950 transition-all border border-emerald-500/20"
                        >
                          <span>Open in Canvas</span>
                          <ArrowSquareOut size={12} weight="bold" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Citation Badges (if grounded) */}
                {citations.length > 0 && (
                  <div className="pt-2 border-t border-slate-800">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                        <Quotes size={12} className="text-emerald-400" weight="fill" />
                        Grounded Citations ({citations.length})
                      </span>
                      <button
                        onClick={() => onInspectEvidence(citations)}
                        className="text-[10px] text-emerald-400 hover:underline font-mono"
                      >
                        View in Evidence Drawer &rarr;
                      </button>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {citations.map((c, idx) => {
                        const simScore = Math.round((c.similarity || 0) * 100);
                        return (
                          <span
                            key={idx}
                            onClick={() => onInspectEvidence(citations)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono bg-slate-950 border border-slate-800 hover:border-emerald-500/40 cursor-pointer text-slate-300 transition-colors"
                            title={`"${c.excerpt}"`}
                          >
                            <span className="text-emerald-400 font-semibold">
                              {c.guest?.split(' ')?.[1] || c.guest}:
                            </span>
                            <span>{simScore}% match</span>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Message Meta Info */}
                {!isUser && (
                  <div className="flex items-center justify-between pt-1 text-[10px] font-mono text-slate-500">
                    <span className="capitalize">{msg.model || 'lenny-synthesizer'}</span>
                    {msg.latency_ms && (
                      <span className="flex items-center gap-1">
                        <Clock size={10} />
                        {msg.latency_ms} ms
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* User Avatar */}
              {isUser && (
                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center shrink-0 mt-1">
                  <User size={16} weight="bold" />
                </div>
              )}
            </div>
          );
        })
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="flex gap-3 max-w-4xl mx-auto justify-start">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-1 animate-pulse">
            <Sparkle size={16} weight="fill" />
          </div>
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl rounded-tl-sm p-4 space-y-2.5 max-w-md w-full shadow-lg">
            <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
              <Lightning size={14} className="animate-spin text-emerald-400" />
              <span>Synthesizing grounded growth advisory...</span>
            </div>
            <div className="h-2 bg-slate-800 rounded w-5/6 animate-pulse" />
            <div className="h-2 bg-slate-800 rounded w-4/6 animate-pulse" />
            <div className="h-2 bg-slate-800 rounded w-2/3 animate-pulse" />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
