import React, { useState } from 'react';
import {
  Code,
  Quotes,
  ArrowsOut,
  ArrowsIn,
  Copy,
  Check,
  ShieldCheck,
  ArrowClockwise,
  Eye,
  FileCode,
  X,
} from '@phosphor-icons/react';
import EvidenceDrawer from './EvidenceDrawer';

export default function GrowthCanvas({
  artifacts = [],
  activeArtifactId,
  onSelectArtifact,
  evidence = [],
  topSimilarity = 0,
  isGrounded = true,
  query = '',
  onClose,
  initialTab = 'artifacts',
}) {
  const [activeTab, setActiveTab] = useState(initialTab); // 'artifacts' | 'evidence'
  const [viewMode, setViewMode] = useState('preview'); // 'preview' | 'code'
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  // Active artifact lookup
  const currentArtifact =
    artifacts.find((a) => a.id === activeArtifactId) || artifacts[artifacts.length - 1] || null;

  const handleCopy = () => {
    if (!currentArtifact) return;
    const code = currentArtifact.sanitized_content || currentArtifact.raw_content || '';
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`h-full flex flex-col bg-[#0B111E] border-l border-slate-800/80 transition-all duration-200 ${
        isFullscreen ? 'fixed inset-0 z-50 bg-[#090D16]/98 backdrop-blur-xl' : 'w-full'
      }`}
    >
      {/* Top Header & Tab Controls */}
      <div className="h-13 px-3 sm:px-4 border-b border-slate-800/80 bg-[#0E1526]/90 flex items-center justify-between shrink-0">
        {/* Left: Tab Switcher (Canvas vs. Evidence) */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setActiveTab('artifacts')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
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
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'evidence'
                ? 'bg-slate-800 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Quotes size={14} weight="bold" />
            <span>Evidence</span>
            {evidence.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300">
                {evidence.length}
              </span>
            )}
          </button>
        </div>

        {/* Right: Actions (Preview/Code Toggle, Reload, Copy, Fullscreen, Close) */}
        <div className="flex items-center gap-1.5">
          {activeTab === 'artifacts' && currentArtifact && (
            <>
              {/* Preview vs Code Toggle */}
              <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5 mr-1">
                <button
                  onClick={() => setViewMode('preview')}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                    viewMode === 'preview'
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  title="Interactive Preview"
                >
                  <Eye size={12} />
                  <span className="hidden sm:inline">Preview</span>
                </button>
                <button
                  onClick={() => setViewMode('code')}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                    viewMode === 'code'
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  title="View Source Code"
                >
                  <FileCode size={12} />
                  <span className="hidden sm:inline">Code</span>
                </button>
              </div>

              {/* Reload Iframe */}
              <button
                onClick={() => setIframeKey((k) => k + 1)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                title="Reload Canvas"
              >
                <ArrowClockwise size={14} />
              </button>

              {/* Copy Code */}
              <button
                onClick={handleCopy}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                title="Copy Artifact Code"
              >
                {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>
            </>
          )}

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <ArrowsIn size={14} /> : <ArrowsOut size={14} />}
          </button>

          {/* Close Panel Button */}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors ml-1"
              title="Close Workspace"
              aria-label="Close Workspace"
            >
              <X size={15} />
            </button>
          )}
        </div>
      </div>

      {/* Main Tab Body */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'evidence' ? (
          /* Evidence Inspector Tab */
          <EvidenceDrawer
            evidence={evidence}
            topSimilarity={topSimilarity}
            isGrounded={isGrounded}
            query={query}
          />
        ) : currentArtifact ? (
          /* Artifact Viewer (Preview or Code) */
          <div className="h-full flex flex-col">
            {/* Multiple Artifacts Selector Strip */}
            {artifacts.length > 1 && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 border-b border-slate-800 overflow-x-auto shrink-0">
                {artifacts.map((art, idx) => (
                  <button
                    key={art.id}
                    onClick={() => onSelectArtifact(art.id)}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                      art.id === currentArtifact.id
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                    }`}
                  >
                    #{idx + 1} {art.title}
                  </button>
                ))}
              </div>
            )}

            {/* View Mode: Interactive Iframe vs Raw Code */}
            <div className="flex-1 overflow-hidden relative">
              {viewMode === 'preview' ? (
                <iframe
                  key={iframeKey}
                  src={`/api/v1/artifacts/${currentArtifact.id}/iframe`}
                  title={currentArtifact.title}
                  sandbox="allow-scripts"
                  className="w-full h-full border-none bg-slate-950"
                />
              ) : (
                <div className="h-full overflow-auto p-4 bg-[#090D16] text-slate-300 font-mono text-xs leading-relaxed selection:bg-emerald-500 selection:text-slate-950">
                  <pre className="whitespace-pre-wrap break-words">
                    {currentArtifact.sanitized_content || currentArtifact.raw_content}
                  </pre>
                </div>
              )}
            </div>

            {/* Bottom Sandbox Guarantee Footer */}
            <div className="px-3 py-2 border-t border-slate-800/80 bg-slate-950/80 flex items-center justify-between text-[11px] font-mono text-slate-400 shrink-0">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <ShieldCheck size={13} weight="fill" />
                <span>Sandboxed Execution ({currentArtifact.status})</span>
              </span>
              <span className="text-slate-500">Origin: Isolated • CSP: Strict</span>
            </div>
          </div>
        ) : (
          /* Empty Artifact Workspace State */
          <div className="h-full flex flex-col items-center justify-center p-6 text-center text-slate-500 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
              <Code size={22} />
            </div>
            <div className="space-y-1">
              <span className="text-sm font-semibold text-slate-300 block font-heading">
                Growth Canvas Ready
              </span>
              <p className="text-xs text-slate-500 max-w-xs leading-relaxed">
                Generate an ICE calculator, Ship 30 cheat sheet, or 4-pillar growth playbook to render interactive tools here.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
