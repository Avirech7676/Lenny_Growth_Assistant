import React from 'react';
import {
  FileText,
  Quotes,
  User,
  ShieldCheck,
  WarningCircle,
  Tag,
} from '@phosphor-icons/react';

export default function EvidenceDrawer({
  evidence = [],
  topSimilarity = 0,
  isGrounded = true,
  query = '',
}) {
  const getSpeakerColor = (guest) => {
    const lower = (guest || '').toLowerCase();
    if (lower.includes('chesky')) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    if (lower.includes('doshi')) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
  };

  return (
    <div className="h-full flex flex-col bg-slate-950/60 overflow-hidden">
      {/* Evidence Summary Header */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-900/60 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Quotes size={18} className="text-emerald-400" weight="fill" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
              Grounding Evidence
            </span>
          </div>
          <div className="flex items-center gap-2">
            {isGrounded ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ShieldCheck size={12} weight="bold" />
                Grounded ({Math.round(topSimilarity * 100)}%)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <WarningCircle size={12} weight="bold" />
                Below Cutoff (&lt;28%)
              </span>
            )}
          </div>
        </div>

        {query && (
          <p className="text-xs text-slate-400 italic truncate">
            Query: "{query}"
          </p>
        )}
      </div>

      {/* Chunks List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {evidence.length === 0 ? (
          <div className="text-center py-12 px-4 text-slate-500 text-xs space-y-2">
            <FileText size={32} className="mx-auto text-slate-600 mb-2" />
            <p>No citations active for this query turn.</p>
            <p className="text-[11px] text-slate-600">
              Submit a prompt to retrieve semantic evidence from Lenny's transcripts.
            </p>
          </div>
        ) : (
          evidence.map((chunk, idx) => {
            const simPercent = Math.round((chunk.similarity || 0) * 100);
            return (
              <div
                key={chunk.chunk_id || idx}
                className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition-colors shadow-sm"
              >
                {/* Speaker & Score Bar */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium border ${getSpeakerColor(
                        chunk.guest
                      )}`}
                    >
                      <User size={12} weight="bold" />
                      {chunk.guest || 'Podcast Guest'}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 font-mono text-[11px] text-slate-400">
                    <span>{simPercent}%</span>
                    <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-400 transition-all"
                        style={{ width: `${Math.min(100, Math.max(5, simPercent))}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Episode Title */}
                {chunk.title && (
                  <p className="text-xs font-semibold text-slate-200">
                    {chunk.title}
                  </p>
                )}

                {/* Excerpt Quote */}
                <blockquote className="text-xs text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border-l-2 border-emerald-500/80 italic leading-relaxed font-sans">
                  "{chunk.excerpt || chunk.text || 'No transcript text available'}"
                </blockquote>

                {chunk.chunk_id && (
                  <div className="text-[10px] font-mono text-slate-500 text-right">
                    chunk:{chunk.chunk_id}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
