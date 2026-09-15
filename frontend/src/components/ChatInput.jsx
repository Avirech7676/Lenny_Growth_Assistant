import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  CircleNotch,
  ChatCircleText,
  Globe,
  Binoculars,
  Code,
  MicrophoneStage,
  PenNib,
  Flask,
  BookOpen,
  SlidersHorizontal,
  Paperclip,
  Stop,
  FileText,
  X,
  Lightning,
} from '@phosphor-icons/react';

const CAPABILITY_MODES = [
  { id: 'chat', label: 'Chat', icon: ChatCircleText, placeholder: "Ask any question, analyze concepts, brainstorm, or discuss anything..." },
  { id: 'search', label: 'Web Search', icon: Globe, placeholder: "Ask for current 2026 facts, news, people, or technical documentation..." },
  { id: 'deep_research', label: 'Deep Research', icon: Binoculars, placeholder: "Enter a topic for autonomous multi-query deep investigation..." },
  { id: 'coding', label: 'Code & Debug', icon: Code, placeholder: "Ask to write code, inspect repository files, debug errors, or review architecture..." },
  { id: 'lenny', label: 'Lenny Archive', icon: MicrophoneStage, placeholder: "Ask about SaaS growth, PLG, retention loops, or Lenny podcast episodes..." },
  { id: 'ship30', label: 'Ship 30 Essay', icon: PenNib, placeholder: "Topic for viral atomic essay (e.g. 'Shreyas Doshi LNO framework')..." },
  { id: 'experiments', label: 'ICE Test', icon: Flask, placeholder: "Growth hypothesis (e.g. 'Remove upfront payment to improve activation')..." },
];

const RESEARCH_DEPTHS = [
  { id: 'auto', label: 'Auto', icon: Lightning, desc: 'Autonomous depth routing' },
  { id: 'search', label: 'Web Search', icon: Globe, desc: 'Targeted live web search' },
  { id: 'deep_research', label: 'Deep Research', icon: Binoculars, desc: 'Autonomous multi-query report' },
];

const MODEL_OPTIONS = [
  { value: '', label: 'Auto Router', provider: 'Intelligent', available: true },
  { value: 'gemini', label: 'Gemini 3.5 Flash', provider: 'Google', available: true },
  { value: 'groq', label: 'Groq Llama 3.3', provider: 'Groq', available: true },
  { value: 'ollama', label: 'Local Ollama', provider: 'Ollama', available: false },
  { value: 'openai', label: 'OpenAI GPT-4o', provider: 'OpenAI', available: false },
  { value: 'anthropic', label: 'Claude 3.5 Sonnet', provider: 'Anthropic', available: false },
];

export default function ChatInput({
  onSendMessage,
  activeMode = 'chat',
  onSelectMode,
  disabled = false,
  selectedProvider = '',
  onChangeProvider,
  onStopGeneration,
  availableModels = [],
  inputPrompt = '',
  onInputChange,
}) {
  const [content, setContent] = useState(inputPrompt || '');
  const [researchDepth, setResearchDepth] = useState('auto');
  const [showDepthPicker, setShowDepthPicker] = useState(false);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Sync external inputPrompt updates (e.g. clicking prompt cards or clearing for new session)
  useEffect(() => {
    if (inputPrompt !== undefined && inputPrompt !== null) {
      setContent(inputPrompt);
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
      }
    }
  }, [inputPrompt]);

  // Derive model choices from availableModels if provided
  const modelChoices = React.useMemo(() => {
    if (!Array.isArray(availableModels) || availableModels.length === 0) {
      return MODEL_OPTIONS;
    }
    const autoOption = { value: '', label: 'Auto Router', provider: 'Intelligent', available: true };
    const mapped = availableModels.map((m) => ({
      value: m.provider || m.model_id,
      label: m.display_name || m.model_id,
      provider: m.provider ? m.provider.toUpperCase() : 'AI',
      available: Boolean(m.is_available),
    }));
    return [autoOption, ...mapped];
  }, [availableModels]);

  const activeModelChoice = modelChoices.find(
    (m) => m.value === selectedProvider
  ) || modelChoices[0];

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled, activeMode]);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setAttachedFile(file);
    }
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if ((!content.trim() && !attachedFile) || disabled) return;

    let effectiveResearchMode = researchDepth;
    if (activeMode === 'search') {
      effectiveResearchMode = 'search';
    } else if (activeMode === 'deep_research') {
      effectiveResearchMode = 'deep_research';
    }

    let finalPrompt = content.trim();
    if (attachedFile) {
      finalPrompt = `[Attached User File: ${attachedFile.name}]\n\n${finalPrompt || 'Please analyze this document.'}`;
    }

    onSendMessage(finalPrompt, effectiveResearchMode, attachedFile);
    setContent('');
    if (onInputChange) onInputChange('');
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
    if (onInputChange) onInputChange(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  const currentMode = CAPABILITY_MODES.find((m) => m.id === activeMode) || CAPABILITY_MODES[0];

  return (
    <div className="p-3 sm:p-4 bg-gradient-to-t from-[#090D16] via-[#090D16]/95 to-transparent border-t border-slate-800/80">
      <div className="max-w-3xl mx-auto space-y-2">
        {/* Floating Composer Container */}
        <form
          onSubmit={handleSubmit}
          className="relative bg-[#0E1526] border border-slate-800 rounded-2xl p-2.5 sm:p-3 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/30 transition-all shadow-xl"
        >
          {/* Attached File Preview Badge */}
          {attachedFile && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 mb-2 rounded-lg bg-slate-900 border border-cyan-500/40 text-xs font-mono text-cyan-300 w-fit">
              <FileText size={14} weight="fill" />
              <span className="truncate max-w-[240px] font-semibold">{attachedFile.name}</span>
              <span className="text-[10px] text-slate-400">({Math.round(attachedFile.size / 1024)} KB)</span>
              <button
                type="button"
                onClick={() => {
                  setAttachedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="text-slate-400 hover:text-white p-0.5 ml-1 cursor-pointer"
                title="Remove attached file"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept=".pdf,.docx,.xlsx,.csv,.json,.jsonl,.txt,.md,.py,.ts,.js,.sql,.cpp,.java,.png,.jpg,.jpeg,.webp"
          />

          {/* Main Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={attachedFile ? `Add questions or instructions for ${attachedFile.name}...` : currentMode.placeholder}
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm resize-none focus:outline-none px-1.5 py-1 max-h-40 leading-relaxed font-sans"
          />

          {/* Composer Bottom Toolbar */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 mt-1 flex-wrap gap-y-2">
            {/* Left: Capability Mode Badges & Controls */}
            <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 max-w-[calc(100%-90px)]">
              {/* File Attachment Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={`p-1.5 rounded-lg text-xs transition-colors cursor-pointer shrink-0 ${
                  attachedFile
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                }`}
                title="Attach Document or Image (PDF, DOCX, XLSX, CSV, JSON, Code, Images)"
              >
                <Paperclip size={14} weight={attachedFile ? 'bold' : 'regular'} />
              </button>

              {CAPABILITY_MODES.map((mode) => {
                const Icon = mode.icon;
                const isSelected = activeMode === mode.id;
                return (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => onSelectMode && onSelectMode(mode.id)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                      isSelected
                        ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/35 font-semibold shadow-[0_0_12px_rgba(6,182,212,0.18)]'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                    }`}
                  >
                    <Icon size={13} weight={isSelected ? 'bold' : 'regular'} />
                    <span>{mode.label}</span>
                  </button>
                );
              })}

              {/* Research Depth Mode Selector */}
              <div className="relative pl-1 border-l border-slate-800 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowDepthPicker(!showDepthPicker)}
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors cursor-pointer"
                  title="Select Depth Level"
                >
                  {(() => {
                    const depthObj = RESEARCH_DEPTHS.find((r) => r.id === researchDepth) || RESEARCH_DEPTHS[0];
                    const DepthIcon = depthObj.icon;
                    return <DepthIcon size={12} className="text-cyan-400" />;
                  })()}
                  <span className="text-cyan-400 font-medium">
                    {RESEARCH_DEPTHS.find((r) => r.id === researchDepth)?.label || 'Auto'}
                  </span>
                </button>

                {showDepthPicker && (
                  <div className="absolute left-0 bottom-full mb-1.5 z-40 w-52 bg-slate-900 border border-slate-700 rounded-xl p-1 shadow-xl text-xs font-mono">
                    <div className="px-2 py-1 text-[10px] text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-800 mb-1">
                      Research Depth
                    </div>
                    {RESEARCH_DEPTHS.map((rm) => {
                      const IconComp = rm.icon;
                      return (
                        <button
                          key={rm.id}
                          type="button"
                          onClick={() => {
                            setResearchDepth(rm.id);
                            setShowDepthPicker(false);
                          }}
                          className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors flex items-center justify-between cursor-pointer ${
                            researchDepth === rm.id
                              ? 'bg-cyan-500/20 text-cyan-300 font-bold'
                              : 'text-slate-300 hover:bg-slate-800'
                          }`}
                        >
                          <div className="flex items-center gap-1.5">
                            <IconComp size={13} className="text-cyan-400" />
                            <span>{rm.label}</span>
                          </div>
                          <span className="text-[9px] text-slate-500">{rm.id === 'auto' ? 'Default' : ''}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Quick Model Selector */}
              <div className="relative pl-1 border-l border-slate-800 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowModelPicker(!showModelPicker)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors cursor-pointer"
                  title="Select AI Model"
                >
                  <SlidersHorizontal size={12} />
                  <span className="text-emerald-400 font-medium truncate max-w-[90px] sm:max-w-[130px]">
                    {activeModelChoice ? activeModelChoice.label : 'AUTO'}
                  </span>
                </button>

                {showModelPicker && (
                  <div className="absolute left-0 bottom-full mb-1.5 z-40 w-56 bg-slate-900 border border-slate-700 rounded-xl p-1 shadow-xl text-xs font-mono max-h-60 overflow-y-auto">
                    <div className="px-2 py-1 text-[10px] text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-800 mb-1">
                      Active AI Model
                    </div>
                    {modelChoices.map((opt, idx) => (
                      <button
                        key={`${opt.value}-${idx}`}
                        type="button"
                        onClick={() => {
                          if (onChangeProvider) onChangeProvider(opt.value);
                          setShowModelPicker(false);
                        }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors flex items-center justify-between cursor-pointer ${
                          selectedProvider === opt.value
                            ? 'bg-cyan-500/20 text-cyan-300 font-bold'
                            : 'text-slate-300 hover:bg-slate-800'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          <span
                            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                              opt.available ? 'bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]' : 'bg-slate-600'
                            }`}
                          />
                          <span className="truncate">{opt.label}</span>
                        </div>
                        {opt.provider && (
                          <span className="text-[9px] text-slate-500 px-1 py-0.2 rounded bg-slate-800 shrink-0">
                            {opt.provider}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right: Send or Stop Button */}
            <div className="flex items-center gap-2 shrink-0 ml-auto">
              {disabled ? (
                <button
                  type="button"
                  onClick={onStopGeneration}
                  className="px-2.5 py-1 rounded-xl bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 flex items-center gap-1.5 text-xs font-mono font-bold transition-all active:scale-95 cursor-pointer shadow-sm"
                  title="Stop Generation"
                >
                  <Stop size={14} weight="fill" />
                  <span>Stop</span>
                </button>
              ) : (
                <>
                  <span className="hidden md:inline text-[10px] text-slate-500 font-mono">
                    ↵ to send
                  </span>
                  <button
                    type="submit"
                    disabled={!content.trim() && !attachedFile}
                    className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                      (content.trim() || attachedFile)
                        ? 'bg-gradient-to-tr from-cyan-400 via-sky-500 to-violet-500 text-white hover:from-cyan-300 hover:to-violet-400 shadow-[0_0_16px_rgba(6,182,212,0.4)] active:scale-95 cursor-pointer'
                        : 'bg-slate-800 text-slate-500 cursor-not-allowed opacity-60'
                    }`}
                    title="Send Message (Enter)"
                    aria-label="Send Message"
                  >
                    <ArrowUp size={16} weight="bold" />
                  </button>
                </>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
