import React, { useState, useRef, useEffect } from 'react';
import {
  PaperPlaneRight,
  CircleNotch,
  Sliders,
} from '@phosphor-icons/react';

const PROVIDER_OPTIONS = [
  { value: '', label: 'Auto (Recommended)' },
  { value: 'ollama', label: 'Local Ollama (llama3.2)' },
  { value: 'anthropic', label: 'Anthropic (Claude 3.5)' },
  { value: 'openai', label: 'OpenAI (GPT-4o)' },
  { value: 'fallback', label: 'Deterministic Synthesizer' },
];

const PLACEHOLDERS = {
  research: "Ask a grounded growth question (e.g. 'What is Brian Chesky's founder mode principle?')...",
  ship30: "Provide a topic for a Ship 30 viral essay (e.g. 'How to conduct a product pre-mortem')...",
  experiments: "Describe an experiment hypothesis (e.g. 'Streamline onboarding from 5 steps to 2 steps')...",
  playbooks: "Request an operational growth playbook (e.g. 'B2B enterprise activation and retention')...",
};

export default function ChatInput({
  onSendMessage,
  activeMode = 'research',
  disabled = false,
  selectedProvider = '',
  onChangeProvider,
}) {
  const [content, setContent] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!content.trim() || disabled) return;

    onSendMessage(content.trim());
    setContent('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextChange = (e) => {
    setContent(e.target.value);
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  return (
    <div className="p-3 sm:p-4 bg-slate-950/90 border-t border-slate-800/80 backdrop-blur-md">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-2">
        {/* Model Provider Override Pill Bar */}
        <div className="flex items-center justify-between text-xs px-1">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowConfig(!showConfig)}
              className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-slate-200 transition-colors"
            >
              <Sliders size={13} />
              <span>Model Routing:</span>
              <span className="text-emerald-400 font-medium">
                {PROVIDER_OPTIONS.find((p) => p.value === selectedProvider)?.label || 'Auto'}
              </span>
            </button>

            {showConfig && (
              <select
                value={selectedProvider}
                onChange={(e) => onChangeProvider(e.target.value)}
                className="text-[11px] bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
              >
                {PROVIDER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          <span className="hidden sm:inline text-[10px] text-slate-500 font-mono">
            Press <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">Shift+Enter</kbd> for newline
          </span>
        </div>

        {/* Input Box */}
        <div className="relative flex items-end gap-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-2 focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/40 transition-all shadow-inner">
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={PLACEHOLDERS[activeMode] || 'Ask Lenny Growth Assistant...'}
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm resize-none focus:outline-none px-2 py-1.5 max-h-44 leading-relaxed font-sans"
          />

          <button
            type="submit"
            disabled={!content.trim() || disabled}
            className={`p-2.5 rounded-xl transition-all shrink-0 ${
              content.trim() && !disabled
                ? 'bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.3)] active:scale-95'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed'
            }`}
            title="Send Message"
          >
            {disabled ? (
              <CircleNotch size={18} className="animate-spin text-slate-400" />
            ) : (
              <PaperPlaneRight size={18} weight="bold" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
