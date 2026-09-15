import React, { useState } from 'react';
import {
  Quotes,
  ShieldCheck,
  WarningCircle,
  Globe,
  Microphone,
  ArrowSquareOut,
  Sparkle,
  CheckCircle,
  Buildings,
  GraduationCap,
  Newspaper,
  Code,
  ChartBar,
  ChatCircleDots,
} from '@phosphor-icons/react';

export default function EvidenceDrawer({
  evidence = [],
  topSimilarity = 0,
  isGrounded = true,
  query = '',
}) {
  const [selectedFilter, setSelectedFilter] = useState('all');

  const getCategoryMeta = (category, isExternal) => {
    if (!isExternal) {
      return {
        label: 'Lenny Podcast',
        icon: Microphone,
        color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      };
    }
    switch (category) {
      case 'official':
      case 'government':
        return {
          label: 'Official / Primary',
          icon: Buildings,
          color: 'text-indigo-300 bg-indigo-500/15 border-indigo-500/35',
        };
      case 'academic':
        return {
          label: 'Academic Research',
          icon: GraduationCap,
          color: 'text-purple-300 bg-purple-500/15 border-purple-500/35',
        };
      case 'news':
        return {
          label: 'Journalistic News',
          icon: Newspaper,
          color: 'text-sky-300 bg-sky-500/15 border-sky-500/35',
        };
      case 'technical':
        return {
          label: 'Technical / Docs',
          icon: Code,
          color: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/35',
        };
      case 'industry':
      case 'financial':
        return {
          label: 'Industry / Financial',
          icon: ChartBar,
          color: 'text-blue-300 bg-blue-500/15 border-blue-500/35',
        };
      case 'community':
        return {
          label: 'Community / Forums',
          icon: ChatCircleDots,
          color: 'text-amber-300 bg-amber-500/15 border-amber-500/35',
        };
      default:
        return {
          label: 'Web Reference',
          icon: Globe,
          color: 'text-cyan-300 bg-cyan-500/15 border-cyan-500/35',
        };
    }
  };

  // Group and tally categories
  const categoriesPresent = evidence.reduce((acc, c) => {
    const isExt = c.source_type === 'external';
    const cat = isExt ? (c.source_category || 'reference') : 'transcript';
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {});

  const filteredEvidence = evidence.filter((c) => {
    if (selectedFilter === 'all') return true;
    if (selectedFilter === 'transcript') {
      return c.source_type === 'transcript' || !c.source_type;
    }
    return c.source_category === selectedFilter || (!c.source_category && selectedFilter === 'reference');
  });

  return (
    <div className="h-full flex flex-col bg-[#0B111E] overflow-hidden">
      {/* Evidence Summary Header */}
      <div className="p-3.5 border-b border-slate-800/80 bg-[#0E1526]/90 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Quotes size={16} className="text-emerald-400" weight="fill" />
            <span className="text-xs font-bold uppercase tracking-wider text-white font-mono">
              Multi-Source Grounding Evidence
            </span>
          </div>
          <div>
            {isGrounded ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <ShieldCheck size={12} weight="bold" />
                Verified Grounding
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                <WarningCircle size={12} weight="bold" />
                Adaptive Web Research
              </span>
            )}
          </div>
        </div>

        {/* Category Breakdown Chips / Filter Bar */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-thin">
          <button
            onClick={() => setSelectedFilter('all')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium whitespace-nowrap transition-colors cursor-pointer active:scale-[0.98] ${
              selectedFilter === 'all'
                ? 'bg-slate-800 text-white border border-slate-700 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({evidence.length})
          </button>

          {categoriesPresent.transcript > 0 && (
            <button
              onClick={() => setSelectedFilter('transcript')}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 whitespace-nowrap transition-colors cursor-pointer active:scale-[0.98] ${
                selectedFilter === 'transcript'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-semibold'
                  : 'text-slate-400 hover:text-emerald-400'
              }`}
            >
              <Microphone size={12} weight="bold" />
              <span>Lenny ({categoriesPresent.transcript})</span>
            </button>
          )}

          {Object.entries(categoriesPresent)
            .filter(([cat]) => cat !== 'transcript')
            .map(([cat, count]) => {
              const meta = getCategoryMeta(cat, true);
              const isActive = selectedFilter === cat;
              const IconComp = meta.icon;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedFilter(cat)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 whitespace-nowrap transition-colors cursor-pointer active:scale-[0.98] ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                      : 'text-slate-400 hover:text-cyan-300'
                  }`}
                >
                  <IconComp size={12} weight="bold" />
                  <span className="capitalize">{cat} ({count})</span>
                </button>
              );
            })}
        </div>

        {query && (
          <p className="text-[11px] text-slate-400 truncate italic font-sans">
            Query: "{query}"
          </p>
        )}
      </div>

      {/* Sources Stream */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {filteredEvidence.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-2">
            <Quotes size={24} className="text-slate-600" />
            <p className="text-xs">No citations matching the active filter.</p>
          </div>
        ) : (
          filteredEvidence.map((src, idx) => {
            const isExternal = src.source_type === 'external';
            const catMeta = getCategoryMeta(src.source_category, isExternal);
            const scorePercent = Math.round((src.similarity || 0) * 100);
            const CatIcon = catMeta.icon;

            return (
              <div
                key={src.chunk_id || idx}
                className="p-3.5 bg-slate-900/90 border border-slate-800 rounded-xl space-y-2.5 shadow-sm hover:border-slate-700/80 transition-colors"
              >
                {/* Source Header: Category + Domain + Evidence Strength */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {/* Category Badge */}
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase border ${catMeta.color}`}
                    >
                      <CatIcon size={11} weight="bold" />
                      <span>{catMeta.label}</span>
                    </span>

                    {/* Domain / Speaker */}
                    <span className="text-[11px] font-mono font-semibold text-slate-300">
                      {isExternal ? (src.domain || 'Verified Web') : (src.guest || 'Lenny Rachitsky')}
                    </span>
                  </div>

                  {/* Qualitative Evidence Strength or Similarity Score */}
                  <div className="flex items-center gap-1">
                    {src.evidence_strength && (
                      <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border ${
                        src.evidence_strength === 'Strong'
                          ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400'
                          : src.evidence_strength === 'Moderate'
                          ? 'bg-cyan-950/60 border-cyan-500/40 text-cyan-300'
                          : 'bg-amber-950/60 border-amber-500/40 text-amber-300'
                      }`}>
                        {src.evidence_strength}
                      </span>
                    )}
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                      {scorePercent}%
                    </span>
                  </div>
                </div>

                {/* Episode / Article Title */}
                <h4 className="text-xs font-semibold text-slate-100 line-clamp-2 leading-snug font-heading">
                  {src.title}
                </h4>

                {/* Why it was useful */}
                {src.why_useful && (
                  <div className="px-2.5 py-1.5 rounded-lg bg-[#070D18] border border-cyan-500/20 text-[11px] text-cyan-300/90 font-mono">
                    <span className="text-slate-400 font-medium">Relevance: </span>
                    {src.why_useful}
                  </div>
                )}

                {/* Excerpt Quote */}
                {src.excerpt && (
                  <blockquote className="p-2.5 rounded-lg bg-slate-950/80 border-l-2 border-emerald-500 text-xs text-slate-300 italic leading-relaxed font-sans">
                    "{src.excerpt}"
                  </blockquote>
                )}

                {/* External Link (if available) */}
                {src.url && (
                  <div className="pt-0.5">
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 hover:underline font-mono"
                    >
                      <span>Source Link ({src.domain || 'External'})</span>
                      <ArrowSquareOut size={11} />
                    </a>
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
