import React, { useState } from 'react';
import {
  Code,
  Quotes,
  ArrowsOut,
  ArrowsIn,
  Copy,
  Check,
  ShieldCheck,
  Sparkle,
  ArrowClockwise,
} from '@phosphor-icons/react';
import EvidenceDrawer from './EvidenceDrawer';
import { api } from '../services/api';

export default function GrowthCanvas({
  artifacts = [],
  activeArtifactId,
  onSelectArtifact,
  evidence = [],
  topSimilarity = 0,
  isGrounded = true,
  query = '',
}) {
  const [activeTab, setActiveTab] = useState('artifacts'); // 'artifacts' | 'evidence'
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  // Find currently selected artifact
  const currentArtifact =
    artifacts.find((a) => a.id === activeArtifactId) || artifacts[0] || null;

  const handleCopyRaw = () => {
    if (!currentArtifact) return;
    navigator.clipboard.writeText(
      currentArtifact.sanitized_content || currentArtifact.raw_content || ''
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`h-full flex flex-col bg-slate-950 border-l border-slate-800/80 transition-all duration-300 ${
        isFullscreen ? 'fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-xl' : ''
      }`}
    >
      {/* Top Tab Bar & Actions */}
      <div className="h-12 px-4 border-b border-slate-800/80 bg-slate-900/80 flex items-center justify-between shrink-0">
        {/* Left: Tab Switches */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('artifacts')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'artifacts'
                ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code size={14} weight="bold" />
            <span>Growth Canvas</span>
            {artifacts.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300">
                {artifacts.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('evidence')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'evidence'
                ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Quotes size={14} weight="bold" />
            <span>Grounding Evidence</span>
            {evidence.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300">
                {evidence.length}
              </span>
            )}
          </button>
        </div>

        {/* Right: Iframe Sandbox Controls */}
        {activeTab === 'artifacts' && currentArtifact && (
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setIframeKey((prev) => prev + 1)}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
              title="Reload Sandboxed Sandbox"
            >
              <ArrowClockwise size={15} />
            </button>
            <button
              onClick={handleCopyRaw}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
              title="Copy Clean Markup"
            >
              {copied ? (
                <Check size={15} className="text-emerald-400" weight="bold" />
              ) : (
                <Copy size={15} />
              )}
            </button>
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
              title={isFullscreen ? 'Exit Fullscreen' : 'Expand Fullscreen'}
            >
              {isFullscreen ? <ArrowsIn size={15} /> : <ArrowsOut size={15} />}
            </button>
          </div>
        )}
      </div>

      {/* Artifact Multi-tabs (if more than 1 artifact exists) */}
      {activeTab === 'artifacts' && artifacts.length > 1 && (
        <div className="px-4 py-1.5 bg-slate-950/80 border-b border-slate-800 flex items-center gap-2 overflow-x-auto">
          {artifacts.map((art) => (
            <button
              key={art.id}
              onClick={() => onSelectArtifact(art.id)}
              className={`px-2.5 py-1 text-xs rounded-md font-mono truncate max-w-[180px] transition-all ${
                art.id === (currentArtifact?.id)
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {art.title || art.artifact_type}
            </button>
          ))}
        </div>
      )}

      {/* Tab Content Panels */}
      <div className="flex-1 relative overflow-hidden">
        {activeTab === 'artifacts' ? (
          currentArtifact ? (
            /* Sandboxed Iframe (allow-scripts ONLY, strictly no allow-same-origin) */
            <iframe
              key={`${currentArtifact.id}-${iframeKey}`}
              src={api.getArtifactIframeUrl(currentArtifact.id)}
              title={currentArtifact.title || 'Growth Canvas Artifact'}
              sandbox="allow-scripts"
              className="w-full h-full border-0 bg-[#0A0E17]"
            />
          ) : (
            /* Empty State for Artifact Viewer */
            <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-400 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-emerald-400 shadow-inner">
                <Sparkle size={24} weight="duotone" />
              </div>
              <div className="max-w-xs space-y-1">
                <h3 className="text-sm font-semibold text-slate-200 font-heading">
                  Growth Canvas Workspace
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Interactive operational artifacts (ICE calculators, growth matrices, and Ship 30 cheat sheets) render here in a sandboxed iframe.
                </p>
              </div>
              <div className="p-3 bg-slate-900/60 border border-slate-800/80 rounded-xl text-left text-xs space-y-1.5 max-w-sm">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 font-mono flex items-center gap-1">
                  <ShieldCheck size={12} weight="bold" /> Sandbox Guarantee
                </span>
                <p className="text-[11px] text-slate-400">
                  All LLM-generated HTML runs in an isolated origin with strict Content-Security-Policy (<code className="text-emerald-400 font-mono">sandbox="allow-scripts"</code>, zero parent cookie/DOM access).
                </p>
              </div>
            </div>
          )
        ) : (
          /* Evidence Tab */
          <EvidenceDrawer
            evidence={evidence}
            topSimilarity={topSimilarity}
            isGrounded={isGrounded}
            query={query}
          />
        )}
      </div>
    </div>
  );
}
