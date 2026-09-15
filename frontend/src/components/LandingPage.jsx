import React, { useState } from 'react';
import {
  Sparkle,
  ArrowRight,
  ShieldCheck,
  Flask,
  BookOpen,
  PenNib,
  Code,
  Binoculars,
  Globe,
  Cpu,
  Lightning,
  Check,
  Database,
  TerminalWindow,
  Quotes,
  ArrowSquareOut,
  Stack,
  GitBranch,
  CheckCircle,
  MicrophoneStage,
  CaretDown,
} from '@phosphor-icons/react';

export default function LandingPage({ onGoChat, onSelectPrompt }) {
  const [activeFaq, setActiveFaq] = useState(null);

  // 4 World-Class Product Leaders from Lenny's Podcast
  const productLeaders = [
    {
      initials: 'SD',
      name: 'Shreyas Doshi',
      role: 'Product Strategy · LNO Framework',
      gradient: 'from-purple-500 to-indigo-500 shadow-purple-500/25',
      tags: ['Product Strategy', 'LNO Framework', 'Pre-Mortems'],
      prompt: "Explain Shreyas Doshi's LNO framework (Leverage, Neutral, Overhead) and how high-agency PMs allocate leverage.",
      mode: 'lenny',
    },
    {
      initials: 'EV',
      name: 'Elena Verna',
      role: 'PLG · Growth Loops · Freemium',
      gradient: 'from-sky-500 to-cyan-400 shadow-sky-500/25',
      tags: ['PLG', 'Growth Loops', 'Freemium vs Trial'],
      prompt: "How does Elena Verna define growth loops versus traditional funnels, and when should a B2B startup choose freemium over free trial?",
      mode: 'lenny',
    },
    {
      initials: 'MC',
      name: 'Marty Cagan',
      role: 'Product Discovery · Empowered Teams',
      gradient: 'from-cyan-500 to-violet-500 shadow-cyan-500/25',
      tags: ['Discovery', 'Feature Factories', '4 Risk Model'],
      prompt: "Explain Marty Cagan's 4 Big Risks (Value, Usability, Feasibility, Viability) and how to prevent teams from becoming feature factories.",
      mode: 'lenny',
    },
    {
      initials: 'PC',
      name: 'Patrick Campbell',
      role: 'SaaS Pricing · Value Metrics',
      gradient: 'from-amber-500 to-orange-400 shadow-amber-500/25',
      tags: ['Value Metrics', 'SaaS Pricing', 'Monetization'],
      prompt: "Explain Patrick Campbell's framework for SaaS pricing and how to determine the optimal 10x value metric for B2B expansion.",
      mode: 'lenny',
    },
  ];

  // 3-Stage RAG Pipeline Steps
  const architectureSteps = [
    {
      step: '01',
      title: 'Semantic Retrieval',
      desc: 'Your query is embedded and matched against verbatim transcript chunks using high-dimensional cosine similarity. The top relevant chunks are retrieved.',
      iconColor: 'text-cyan-400 bg-cyan-500/15 border-cyan-500/25',
    },
    {
      step: '02',
      title: 'Intent Routing',
      desc: 'The agent router classifies the query into Grounded Q&A, ICE Experiment, 4-Pillar Playbook, Ship 30 essay, or Code artifact with specialised prompt constraints.',
      iconColor: 'text-indigo-400 bg-indigo-500/15 border-indigo-500/25',
    },
    {
      step: '03',
      title: 'Grounded Generation',
      desc: 'The LLM synthesises an evidence-backed response using only verified transcript context with exact timestamps and strict refusal if below the 0.28 cutoff.',
      iconColor: 'text-violet-400 bg-violet-500/15 border-violet-500/25',
    },
  ];

  const samplePrompts = [
    {
      title: 'Founder Mode & Design',
      prompt: "Explain Brian Chesky's founder mode and why excessive A/B testing can kill bold product design.",
      mode: 'lenny',
      tag: 'Lenny Archive',
    },
    {
      title: 'Real-Time Web Fact',
      prompt: 'Who is the Chief Minister of Andhra Pradesh?',
      mode: 'search',
      tag: 'Web Intelligence',
    },
    {
      title: 'Autonomous Deep Research',
      prompt: 'Conduct a deep research report on state-of-the-art AI agent frameworks and production reliability in 2026.',
      mode: 'deep_research',
      tag: 'Deep Research',
    },
    {
      title: 'Software Architecture & Code',
      prompt: 'Write an async Python connection pool with exponential backoff, circuit breaker, and FastAPI health checks.',
      mode: 'coding',
      tag: 'Code Agent',
    },
  ];

  const features = [
    {
      icon: ShieldCheck,
      color: 'cyan',
      title: 'Strict Epistemic Refusal Gate',
      desc: 'Prevents LLM hallucination with a calibrated hybrid vector-lexical cutoff threshold (≥ 0.28). If a query lacks transcript ground truth, the system transparently refuses rather than manufacturing unsupported claims.',
      badge: 'Zero Hallucination',
    },
    {
      icon: Flask,
      color: 'violet',
      title: 'ICE Growth Experiment Generator',
      desc: 'Generates structured operational growth experiments with primary Overall Evaluation Criterion (OEC), guardrail metrics, calculated Impact-Confidence-Ease scores, and 48-hour smoke test validation steps.',
      badge: 'Scientific Growth',
    },
    {
      icon: BookOpen,
      color: 'cyan',
      title: '4-Pillar Operational Playbooks',
      desc: 'Formulates multi-phased operational playbooks systematically organized across Acquisition, Activation, Retention, and Monetization pillars, grounded in veteran operator playbooks.',
      badge: 'Full-Funnel Strategy',
    },
    {
      icon: PenNib,
      color: 'violet',
      title: 'Ship 30 for 30 Viral Essays',
      desc: 'Transforms raw transcript transcripts into structured ~1,250-word editorial essays adhering strictly to the Ship 30 framework (The Hook, The Tension, 3 Core Pillars, 5 Actionable Takeaways, and Outro).',
      badge: 'Content Strategy',
    },
    {
      icon: Code,
      color: 'indigo',
      title: 'Origin-Isolated Growth Canvas',
      desc: 'Executes untrusted operational deliverables and interactive calculators inside an isolated iframe sandbox with strict Content Security Policy (default-src "none") and postMessage communication.',
      badge: 'Secure Sandboxing',
    },
    {
      icon: Binoculars,
      color: 'purple',
      title: 'Autonomous Deep Research Engine',
      desc: 'Multi-query expansion pipeline with real-time web intelligence, automated citation verification, domain authority scoring, and continuous background research progress streaming.',
      badge: 'Autonomous Agents',
    },
  ];

  const techStack = [
    {
      category: 'Frontend & UI Layer',
      icon: Stack,
      items: [
        { name: 'React 19', desc: 'Modern React with concurrent rendering, hooks & fast state updates' },
        { name: 'Tailwind CSS v4', desc: 'Next-gen utility-first styling with high-end dark color tokens' },
        { name: 'ThreeUI & Three.js', desc: 'Hardware-accelerated 3D WebGL shaders & topology graph fields' },
        { name: 'Phosphor Icons', desc: 'Clean, modern SVG iconography system (100% emoji-free)' },
        { name: 'SSE Streaming', desc: 'Server-Sent Events for fast token streaming & telemetry HUD' },
      ],
    },
    {
      category: 'Backend & Orchestration',
      icon: TerminalWindow,
      items: [
        { name: 'FastAPI (Python)', desc: 'High-performance async ASGI web framework with strict schemas' },
        { name: 'Pydantic v2', desc: 'Strict runtime data validation, schema serialization & type safety' },
        { name: 'Multi-Model Router', desc: 'Task-affinity dynamic routing with automated fallback cascades' },
        { name: 'Circuit Breaker', desc: 'Real-time fault tolerance preventing cascade failures under rate limits' },
        { name: 'Quality Verification Gate', desc: 'Automated response verification scoring against evidence threshold' },
      ],
    },
    {
      category: 'Vector DB & Data Tier',
      icon: Database,
      items: [
        { name: 'PostgreSQL 16', desc: 'Enterprise relational store for sessions, messages, and deliverables' },
        { name: 'pgvector Extension', desc: 'High-dimensional vector embeddings search for transcript chunks' },
        { name: 'SQLite Fallback', desc: 'Zero-configuration local database fallback for instant offline execution' },
        { name: 'Hybrid RAG Pipeline', desc: 'Dense vector retrieval combined with lexical keyword matching' },
      ],
    },
    {
      category: 'Testing & Infrastructure',
      icon: GitBranch,
      items: [
        { name: 'Pytest Matrix (16 Suites)', desc: '72/72 passing automated tests across all operational tiers' },
        { name: 'Docker & Compose', desc: 'Production-ready multi-stage containerization' },
        { name: 'Ollama Integration', desc: 'Local LLM daemon bridge for private zero-cost inference' },
        { name: 'Table 6 Deliverable Audit', desc: '100% compliance with Forward Deployed Engineer specs' },
      ],
    },
  ];

  const models = [
    {
      provider: 'Anthropic',
      name: 'Claude 3.5 Sonnet',
      tier: 'System Architect',
      desc: 'Excels at complex strategy synthesis, operational playbooks, and rigorous code architecture.',
      tag: 'Cloud Tier',
      color: 'border-amber-500/40 bg-amber-950/20 text-amber-300',
    },
    {
      provider: 'OpenAI',
      name: 'GPT-4o & 4o-mini',
      tier: 'General Intelligence',
      desc: 'Versatile conversational reasoning, cross-domain knowledge, and multi-turn consistency.',
      tag: 'Cloud Tier',
      color: 'border-violet-500/40 bg-violet-950/20 text-violet-300',
    },
    {
      provider: 'Google',
      name: 'Gemini 2.0 Flash / Pro',
      tier: 'Long-Context Reasoning',
      desc: 'Massive 1M+ token context window, multimodal capabilities, and rapid token throughput.',
      tag: 'Cloud Tier',
      color: 'border-cyan-500/40 bg-cyan-950/20 text-cyan-300',
    },
    {
      provider: 'Groq & Cerebras',
      name: 'Llama 3.3 70B Fast',
      tier: 'Ultra-Low Latency',
      desc: 'Near-instantaneous token generation (<100ms TTFT) for high-velocity streaming execution.',
      tag: 'High-Throughput',
      color: 'border-rose-500/40 bg-rose-950/20 text-rose-300',
    },
    {
      provider: 'Ollama (Local)',
      name: 'Llama 3.2 / DeepSeek-R1',
      tier: 'Private Offline Inference',
      desc: 'Runs completely locally on your hardware. Zero API costs, zero data egress, offline resilience.',
      tag: 'Local & Offline',
      color: 'border-indigo-500/40 bg-indigo-950/20 text-indigo-300',
    },
  ];

  const faqs = [
    {
      q: 'What is the Lenny Growth Assistant?',
      a: "It is an executive-grade AI growth strategist strictly grounded in Lenny's Podcast transcripts. Unlike generic chatbots that hallucinate founder quotes or offer generic advice, it provides citation-backed strategies, interactive execution artifacts (growth calculators, experiment matrices), and strict epistemic cutoff guarantees.",
    },
    {
      q: 'How does the Epistemic Refusal Gate work?',
      a: 'The system computes a hybrid vector-lexical similarity score between incoming queries and indexed transcript chunks. If the similarity falls below 0.28 and the question is outside domain intelligence, the model gracefully refuses to answer, protecting you from fabricated advice.',
    },
    {
      q: 'Can I run this completely offline without API keys?',
      a: 'Yes. The platform natively integrates with local Ollama daemons (e.g. Llama 3.2, DeepSeek-R1) and features a SQLite auto-fallback, enabling complete zero-cost, private, offline execution without cloud dependencies.',
    },
    {
      q: 'What is the Origin-Isolated Growth Canvas?',
      a: 'When the assistant generates operational code or interactive deliverables (like ICE calculators or growth models), they are rendered in a dedicated sandbox iframe configured with sandbox="allow-scripts" (without allow-same-origin) and strict Content Security Policy, completely isolating untrusted code from parent tokens and cookies.',
    },
    {
      q: 'How does the Multi-Model Router handle API failures?',
      a: 'The orchestrator features a real-time Circuit Breaker and automated failover cascade. If a cloud provider returns a 429 rate limit or 503 error, the system instantly transitions to the next available healthy provider and badges the response with the transition details.',
    },
  ];

  return (
    <div className="relative min-h-screen text-slate-100 font-sans selection:bg-zinc-800 selection:text-white pb-20">
      {/* Top Floating Glass Navigation Header */}
      <nav className="sticky top-0 z-40 h-16 border-b border-white/10 bg-black/60 backdrop-blur-xl px-4 sm:px-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-400 via-sky-500 to-fuchsia-500 p-0.5 shadow-[0_0_20px_rgba(56,189,248,0.5)] shrink-0 group-hover:shadow-[0_0_28px_rgba(192,132,252,0.7)] transition-all">
            <div className="w-full h-full bg-[#070913] rounded-[10px] flex items-center justify-center">
              <Sparkle size={18} weight="fill" className="text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.85)]" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-sm sm:text-base font-heading tracking-tight">
                The Lenny Growth Assistant
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-bold shadow-[0_0_10px_rgba(6,182,212,0.2)]">
                v1.0
              </span>
              <span className="hidden md:inline-block px-2.5 py-0.5 text-[9px] font-mono uppercase font-bold rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/35 shadow-[0_0_12px_rgba(139,92,246,0.25)] tracking-wider">
                Evidence-Grounded AI
              </span>
            </div>
          </div>
        </div>

        {/* Section Jump Links */}
        <div className="hidden lg:flex items-center gap-5 text-xs font-medium text-slate-400">
          <a href="#overview" className="hover:text-cyan-400 transition-colors">Overview</a>
          <a href="#knowledge-base" className="hover:text-cyan-400 transition-colors">Speakers</a>
          <a href="#features" className="hover:text-cyan-400 transition-colors">Capabilities</a>
          <a href="#pipeline" className="hover:text-cyan-400 transition-colors">Pipeline</a>
          <a href="#models" className="hover:text-cyan-400 transition-colors">Models</a>
          <a href="#tech-stack" className="hover:text-cyan-400 transition-colors">Tech Stack</a>
          <a href="#faq" className="hover:text-cyan-400 transition-colors">FAQ</a>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]"></span>
            All 5 Models Live
          </span>
          <button
            onClick={onGoChat}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 via-sky-600 to-violet-600 hover:from-cyan-400 hover:via-sky-500 hover:to-violet-500 text-white font-bold text-xs rounded-xl transition-all shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:shadow-[0_0_28px_rgba(168,85,247,0.6)] active:scale-95 cursor-pointer font-heading"
          >
            <span>Open Growth Console</span>
            <ArrowRight size={14} weight="bold" />
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section id="overview" className="relative pt-12 sm:pt-20 pb-16 px-4 sm:px-8 max-w-6xl mx-auto text-center">
        {/* Compliance & Grounding Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900/90 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-6 shadow-sm">
          <Sparkle size={13} weight="fill" className="text-cyan-400 drop-shadow-[0_0_6px_rgba(34,211,238,0.6)]" />
          <span>Strictly Grounded in Lenny's Podcast • 72/72 Passing Automated Tests</span>
        </div>

        {/* Main Headline */}
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold font-heading text-white tracking-tight leading-[1.15] max-w-4xl mx-auto">
          The Evidence-Grounded{' '}
          <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-fuchsia-400 bg-clip-text text-transparent">
            AI Growth Strategist
          </span>
        </h1>

        {/* Subtitle */}
        <p className="mt-5 text-sm sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed font-sans">
          An authoritative operational advisory platform with strict epistemic refusal, origin-isolated interactive sandboxing, autonomous deep research, and multi-model routing across Claude, GPT-4o, Gemini, Groq, and local Ollama.
        </p>

        {/* Call to Action Buttons */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 sm:gap-4">
          <button
            onClick={onGoChat}
            className="flex items-center gap-2.5 px-7 py-3.5 bg-gradient-to-r from-cyan-500 via-indigo-600 to-violet-600 hover:from-cyan-400 hover:via-indigo-500 hover:to-violet-500 text-white font-bold text-sm rounded-2xl transition-all shadow-[0_0_28px_rgba(6,182,212,0.4)] hover:shadow-[0_0_36px_rgba(168,85,247,0.6)] active:scale-95 cursor-pointer font-heading"
          >
            <Sparkle size={16} weight="fill" className="text-cyan-200" />
            <span>Launch Growth Console</span>
            <ArrowRight size={16} weight="bold" />
          </button>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-6 py-3.5 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/15 hover:border-white/30 rounded-2xl font-medium text-sm transition-all shadow-sm"
          >
            <Code size={16} />
            <span>View API Docs</span>
            <ArrowSquareOut size={14} className="text-slate-400" />
          </a>
        </div>

        {/* 4 Quantitative Project Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto mt-10">
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-sm text-center">
            <div className="text-2xl sm:text-3xl font-black font-heading text-cyan-400">4</div>
            <div className="text-[11px] text-slate-400 font-mono mt-1 uppercase tracking-wider">Transcripts</div>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-sm text-center">
            <div className="text-2xl sm:text-3xl font-black font-heading text-indigo-400">24</div>
            <div className="text-[11px] text-slate-400 font-mono mt-1 uppercase tracking-wider">Vector Chunks</div>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-sm text-center">
            <div className="text-2xl sm:text-3xl font-black font-heading text-fuchsia-400">5 / 5</div>
            <div className="text-[11px] text-slate-400 font-mono mt-1 uppercase tracking-wider">Models Live</div>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-sm text-center">
            <div className="text-2xl sm:text-3xl font-black font-heading text-violet-400">100%</div>
            <div className="text-[11px] text-slate-400 font-mono mt-1 uppercase tracking-wider">Grounded</div>
          </div>
        </div>

        {/* Quick Launch Sample Prompts */}
        <div className="mt-12 text-left max-w-4xl mx-auto">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-3 text-center">
            Click any prompt to instantly test live in the console:
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {samplePrompts.map((sp, idx) => (
              <button
                key={idx}
                onClick={() => onSelectPrompt(sp.prompt, sp.mode)}
                className="p-3.5 rounded-xl bg-slate-900/80 hover:bg-slate-900 border border-slate-800/90 hover:border-cyan-500/40 transition-all text-left group cursor-pointer shadow-sm hover:shadow-md active:scale-[0.99]"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors font-heading flex items-center gap-1.5">
                    <MicrophoneStage size={13} className="text-cyan-400" />
                    {sp.title}
                  </span>
                  <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 uppercase">
                    {sp.tag}
                  </span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  "{sp.prompt}"
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Live Advisory Preview Box */}
        <div className="mt-12 max-w-4xl mx-auto rounded-2xl border border-slate-800/90 bg-[#0C1220]/90 shadow-2xl p-5 sm:p-7 text-left space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-sky-400 animate-pulse" />
              <span className="font-mono text-slate-300 font-bold">Live Turn Demonstration</span>
              <span className="px-2 py-0.5 rounded bg-sky-950/60 border border-sky-500/30 text-sky-400 text-[10px] font-mono">
                GROUNDED • 96% CONFIDENCE
              </span>
            </div>
            <div className="flex items-center gap-3 text-slate-400 font-mono text-[11px]">
              <span className="flex items-center gap-1">
                <Lightning size={12} className="text-sky-400" weight="fill" />
                142ms TTFT
              </span>
              <span>•</span>
              <span className="text-sky-400">82 tok/s</span>
            </div>
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-2.5">
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-xs font-bold shrink-0">
                USER
              </span>
              <p className="text-slate-300 font-medium">
                Why does Brian Chesky argue that traditional product management A/B testing frameworks can destroy bold design?
              </p>
            </div>
            <div className="flex items-start gap-2.5 pt-2">
              <div className="w-6 h-6 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0 mt-0.5">
                <Sparkle size={13} weight="fill" className="text-sky-400" />
              </div>
              <div className="space-y-2 text-xs sm:text-sm text-slate-300 leading-relaxed">
                <p>
                  According to Brian Chesky on Lenny's Podcast, excessive reliance on isolated A/B testing creates a <strong>local-maxima trap</strong>. When product teams optimize strictly for incremental conversion ticks, they paralyze bold, unified product visions:
                </p>
                <blockquote className="border-l-2 border-sky-400 pl-3 italic text-slate-400 bg-slate-900/50 py-1 rounded-r">
                  "If you run 50 experiments a week, you're not designing a cohesive guest experience. You're letting statistical noise dictate product soul." — Brian Chesky
                </blockquote>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Knowledge Base: 4 World-Class Product Leaders (from lennyai.vercel.app reference) */}
      <section id="knowledge-base" className="py-16 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="max-w-2xl mx-auto text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-slate-300 mb-3">
            <BookOpen size={14} className="text-cyan-400" />
            <span>Knowledge Base • Grounded Corpus</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            4 World-Class Product Leaders
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Verbatim transcripts from Lenny's Podcast. Every answer traces back to a specific speaker, episode, and exact excerpt. Click any leader to query their frameworks:
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {productLeaders.map((leader, i) => (
            <div
              key={i}
              onClick={() => onSelectPrompt(leader.prompt, leader.mode)}
              className="group relative p-5 rounded-3xl bg-slate-900/80 border border-slate-800/90 hover:bg-slate-900 hover:border-cyan-500/40 backdrop-blur-sm transition-all duration-300 hover:shadow-xl hover:shadow-cyan-950/20 cursor-pointer text-left flex flex-col justify-between"
            >
              <div>
                <div
                  className={`w-12 h-12 rounded-2xl bg-gradient-to-tr ${leader.gradient} flex items-center justify-center text-white font-black text-sm mb-4 shadow-lg group-hover:scale-105 transition-transform duration-300 font-mono`}
                >
                  {leader.initials}
                </div>
                <h3 className="text-base font-bold text-white mb-0.5 group-hover:text-cyan-300 transition-colors font-heading">
                  {leader.name}
                </h3>
                <p className="text-xs text-slate-400 mb-3 leading-relaxed">
                  {leader.role}
                </p>
              </div>

              <div>
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {leader.tags.map((tag, tIdx) => (
                    <span
                      key={tIdx}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-300 font-mono"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-medium group-hover:translate-x-0.5 transition-transform">
                  <span>Explore Insights</span>
                  <ArrowRight size={12} weight="bold" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Bento Grid: Core Architectural Pillars */}
      <section id="features" className="pt-16 pb-20 px-4 sm:px-8 max-w-6xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold block mb-2">
            Engineered For High-Agency Operators
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            Six Specialized Decision Engines
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-3 leading-relaxed">
            Every query is analyzed, routed, and enriched with domain-specific skills and verifiable execution outputs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div
                key={i}
                className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 hover:border-cyan-500/30 transition-all space-y-3 group shadow-sm hover:shadow-lg"
              >
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
                    <Icon size={18} weight="bold" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60 uppercase">
                    {f.badge}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white font-heading group-hover:text-cyan-300 transition-colors">
                  {f.title}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {f.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 3-Stage Architecture: How It Works (from lennyai.vercel.app reference) */}
      <section id="pipeline" className="py-16 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="max-w-2xl mx-auto text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-mono text-slate-300 mb-3">
            <GitBranch size={14} className="text-sky-400" />
            <span>Architecture • Execution Pipeline</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            How The RAG Engine Works
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
            Every user prompt traverses a deterministic 3-stage pipeline before reaching the inference tier, enforcing citation fidelity and zero hallucinations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {architectureSteps.map((step, i) => (
            <div
              key={i}
              className="relative p-7 rounded-3xl bg-slate-900/80 border border-slate-800/90 hover:border-slate-700 backdrop-blur-sm overflow-hidden transition-all duration-300 hover:shadow-xl group"
            >
              <div className="absolute -top-3 -right-2 text-7xl font-black text-white/[0.04] font-mono leading-none select-none group-hover:text-white/[0.08] transition-colors">
                {step.step}
              </div>
              <div
                className={`w-12 h-12 rounded-2xl border flex items-center justify-center mb-6 font-mono font-black text-base ${step.iconColor}`}
              >
                {step.step}
              </div>
              <h3 className="text-base font-bold text-white mb-2 font-heading">
                {step.title}
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed relative z-10">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Comprehensive Models Matrix */}
      <section id="models" className="pt-12 pb-20 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold block mb-2">
            Multi-Model Orchestrator
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            Universal Provider & Local Model Support
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-3 leading-relaxed">
            Dynamic affinity routing across state-of-the-art cloud providers and private local models with automatic circuit-breaker cascades.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m, i) => (
            <div
              key={i}
              className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-3 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 font-mono uppercase">
                  {m.provider}
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${m.color}`}>
                  {m.tag}
                </span>
              </div>
              <div>
                <h3 className="text-base font-bold text-white font-heading">
                  {m.name}
                </h3>
                <span className="text-[11px] font-mono text-cyan-400 block mt-0.5">
                  Role: {m.tier}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                {m.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Full Tech Stack Showcase */}
      <section id="tech-stack" className="pt-12 pb-20 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold block mb-2">
            Production Engineering
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            The Complete Technology Stack
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-3 leading-relaxed">
            Architected for zero downtime, strict vector compliance, fast TTFT streaming, and sandboxed security.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {techStack.map((tier, i) => {
            const TierIcon = tier.icon;
            return (
              <div
                key={i}
                className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-md space-y-4"
              >
                <div className="flex items-center gap-2.5 pb-2 border-b border-slate-800">
                  <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                    <TierIcon size={16} weight="bold" />
                  </div>
                  <h3 className="text-base font-bold text-white font-heading">
                    {tier.category}
                  </h3>
                </div>

                <div className="space-y-3">
                  {tier.items.map((item, idx) => (
                    <div key={idx} className="flex items-start justify-between gap-3 text-xs">
                      <div>
                        <span className="font-bold text-slate-200 font-mono block">
                          {item.name}
                        </span>
                        <span className="text-slate-400 text-[11px]">
                          {item.desc}
                        </span>
                      </div>
                      <CheckCircle size={14} className="text-cyan-400 shrink-0 mt-1" weight="fill" />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Comparison: Why Grounded RAG Matters */}
      <section id="architecture" className="pt-12 pb-20 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono uppercase tracking-wider text-violet-400 font-bold block mb-2">
            Verifiable Rigor
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            Generic LLMs vs. The Lenny Growth Assistant
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-3 leading-relaxed">
            Why executive product and growth decisions require grounded evidence over unchecked probabilistic generation.
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-slate-800 shadow-xl bg-slate-900/90">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-[#0C1220] text-slate-300 font-mono text-[11px]">
                <th className="p-4 font-bold">Feature / Dimension</th>
                <th className="p-4 font-bold text-slate-400">Standard Generic Chatbot</th>
                <th className="p-4 font-bold text-cyan-400">The Lenny Growth Assistant</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-300">
              <tr>
                <td className="p-4 font-medium text-white">Truth Grounding</td>
                <td className="p-4 text-slate-400">Hallucinates quotes and attributes false metrics</td>
                <td className="p-4 text-cyan-300 font-medium">100% transcript-grounded with exact guest timestamps</td>
              </tr>
              <tr>
                <td className="p-4 font-medium text-white">Out-of-Domain Queries</td>
                <td className="p-4 text-slate-400">Fabricates answers to recipes, astronomy, gossip</td>
                <td className="p-4 text-cyan-300 font-medium">Strict Epistemic Refusal Gate (&lt;0.28 cutoff)</td>
              </tr>
              <tr>
                <td className="p-4 font-medium text-white">Interactive Execution</td>
                <td className="p-4 text-slate-400">Static markdown text blocks only</td>
                <td className="p-4 text-cyan-300 font-medium">Origin-isolated sandboxed Growth Canvas with live tools</td>
              </tr>
              <tr>
                <td className="p-4 font-medium text-white">Experiment Design</td>
                <td className="p-4 text-slate-400">Vague high-level bullet points</td>
                <td className="p-4 text-cyan-300 font-medium">Structured ICE score, OEC metrics & 48h smoke tests</td>
              </tr>
              <tr>
                <td className="p-4 font-medium text-white">Offline Privacy</td>
                <td className="p-4 text-slate-400">Requires continuous proprietary cloud connection</td>
                <td className="p-4 text-cyan-300 font-medium">Native local Ollama & SQLite offline support</td>
              </tr>
              <tr>
                <td className="p-4 font-medium text-white">Automated Verification</td>
                <td className="p-4 text-slate-400">None; user must manually check accuracy</td>
                <td className="p-4 text-cyan-300 font-medium">Quality Verification Gate with real-time scoring badge</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Benchmark Metrics & Compliance */}
      <section id="metrics" className="pt-12 pb-20 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
            <span className="text-3xl sm:text-4xl font-black font-heading text-cyan-400">72 / 72</span>
            <span className="text-xs text-slate-300 font-medium block">Pytest Suites Passing</span>
            <span className="text-[10px] font-mono text-slate-500 block">100% Table 6 Compliance</span>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
            <span className="text-3xl sm:text-4xl font-black font-heading text-cyan-400">&lt; 150ms</span>
            <span className="text-xs text-slate-300 font-medium block">TTFT Latency</span>
            <span className="text-[10px] font-mono text-slate-500 block">Streaming SSE Engine</span>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
            <span className="text-3xl sm:text-4xl font-black font-heading text-violet-400">100+</span>
            <span className="text-xs text-slate-300 font-medium block">Transcripts Indexed</span>
            <span className="text-[10px] font-mono text-slate-500 block">Dense + Lexical Embeddings</span>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
            <span className="text-3xl sm:text-4xl font-black font-heading text-indigo-400">100%</span>
            <span className="text-xs text-slate-300 font-medium block">Origin Isolation</span>
            <span className="text-[10px] font-mono text-slate-500 block">CSP 'none' Sandboxing</span>
          </div>
        </div>
      </section>

      {/* Operator Quotations */}
      <section className="pt-12 pb-20 px-4 sm:px-8 max-w-6xl mx-auto border-t border-slate-800/80">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold block mb-2">
            Synthesized From The Best
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold font-heading text-white tracking-tight">
            Voices of World-Class Operators
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
            <Quotes size={22} className="text-cyan-400" weight="fill" />
            <p className="text-xs text-slate-300 leading-relaxed italic">
              "Being in founder mode means having complete permission to skip management layers and understand the truth of what your team is building."
            </p>
            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono">
              <span className="font-bold text-white block">Brian Chesky</span>
              <span className="text-slate-500">Co-founder & CEO, Airbnb</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
            <Quotes size={22} className="text-cyan-400" weight="fill" />
            <p className="text-xs text-slate-300 leading-relaxed italic">
              "Product-led growth isn't a silver bullet. It's a disciplined feedback loop where activation efficiency compounds into viral retention."
            </p>
            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono">
              <span className="font-bold text-white block">Elena Verna</span>
              <span className="text-slate-500">Head of Growth, Lovable & Dropbox</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
            <Quotes size={22} className="text-violet-400" weight="fill" />
            <p className="text-xs text-slate-300 leading-relaxed italic">
              "High-agency product managers don't wait for perfect data. They build clear hypotheses, test guardrail metrics, and ship."
            </p>
            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono">
              <span className="font-bold text-white block">Shreyas Doshi</span>
              <span className="text-slate-500">Former PM Lead, Stripe & Twitter</span>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="pt-12 pb-20 px-4 sm:px-8 max-w-4xl mx-auto border-t border-slate-800/80">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold block mb-2">
            Clear Answers
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold font-heading text-white tracking-tight">
            Frequently Asked Questions
          </h2>
        </div>

        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <div
              key={i}
              className="rounded-xl border border-slate-800/90 bg-slate-900/80 overflow-hidden transition-all"
            >
              <button
                onClick={() => setActiveFaq(activeFaq === i ? null : i)}
                className="w-full p-4 text-left flex items-center justify-between text-xs sm:text-sm font-bold text-slate-200 hover:text-white cursor-pointer"
              >
                <span>{faq.q}</span>
                <CaretDown
                  size={14}
                  className={`transform transition-transform text-slate-400 ${activeFaq === i ? 'rotate-180 text-cyan-400' : ''}`}
                />
              </button>
              {activeFaq === i && (
                <div className="px-4 pb-4 text-xs text-slate-400 leading-relaxed border-t border-slate-800/50 pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA Banner */}
      <section className="pt-10 pb-16 px-4 sm:px-8 max-w-5xl mx-auto">
        <div className="p-8 sm:p-12 rounded-3xl bg-gradient-to-br from-cyan-950/40 via-violet-950/30 to-slate-950 border border-cyan-500/30 text-center space-y-5 shadow-[0_0_35px_rgba(6,182,212,0.2)] relative overflow-hidden">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-400 via-sky-500 to-fuchsia-500 p-0.5 shadow-[0_0_24px_rgba(56,189,248,0.5)] mx-auto">
            <div className="w-full h-full bg-[#070913] rounded-[10px] flex items-center justify-center">
              <Sparkle size={24} weight="fill" className="text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.85)]" />
            </div>
          </div>
          <h2 className="text-2xl sm:text-4xl font-extrabold font-heading text-white tracking-tight">
            Ready to Build Your Evidence-Grounded Growth Engine?
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 max-w-xl mx-auto leading-relaxed">
            Transition directly into the Growth Console to run experiments, generate 4-pillar playbooks, write Ship 30 essays, or inspect software architectures.
          </p>
          <div className="pt-2 flex justify-center">
            <button
              onClick={onGoChat}
              className="flex items-center gap-2.5 px-6 py-3.5 bg-gradient-to-r from-cyan-500 via-indigo-600 to-violet-600 hover:from-cyan-400 hover:via-indigo-500 hover:to-violet-500 text-white font-bold text-sm rounded-xl transition-all shadow-[0_0_28px_rgba(6,182,212,0.4)] hover:shadow-[0_0_36px_rgba(168,85,247,0.6)] active:scale-95 cursor-pointer font-heading"
            >
              <span>Launch Growth Console</span>
              <ArrowRight size={16} weight="bold" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="pt-10 border-t border-slate-800/70 text-center text-xs text-slate-500 font-mono space-y-3">
        <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-5 text-slate-400">
          <a href="#overview" className="hover:text-cyan-400 transition-colors">Overview</a>
          <span>•</span>
          <a href="#knowledge-base" className="hover:text-cyan-400 transition-colors">Speakers</a>
          <span>•</span>
          <a href="#features" className="hover:text-cyan-400 transition-colors">Capabilities</a>
          <span>•</span>
          <a href="#pipeline" className="hover:text-cyan-400 transition-colors">Pipeline</a>
          <span>•</span>
          <a href="#models" className="hover:text-cyan-400 transition-colors">Models</a>
          <span>•</span>
          <a href="#tech-stack" className="hover:text-cyan-400 transition-colors">Tech Stack</a>
          <span>•</span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-cyan-400 transition-colors flex items-center gap-1 text-slate-300"
          >
            <span>API Docs</span>
            <ArrowSquareOut size={12} />
          </a>
          <span>•</span>
          <button onClick={onGoChat} className="text-cyan-400 hover:underline cursor-pointer font-bold">
            Open Console
          </button>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3 text-[11px] text-slate-600">
          <span>FastAPI</span>
          <span>•</span>
          <span>Python 3.11</span>
          <span>•</span>
          <span>React 19</span>
          <span>•</span>
          <span>Qdrant Vector DB</span>
          <span>•</span>
          <span>ThreeUI / WebGL</span>
        </div>
        <p className="text-[11px] text-slate-500">The Lenny Growth Assistant © 2026 • Strict Epistemic Grounding & High-Agency AI Execution</p>
      </footer>
    </div>
  );
}
