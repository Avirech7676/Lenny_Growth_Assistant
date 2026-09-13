import React from 'react';
import {
  MagnifyingGlass,
  PenNib,
  Flask,
  BookOpen,
} from '@phosphor-icons/react';

const MODES = [
  {
    id: 'research',
    label: 'Grounded Research',
    icon: MagnifyingGlass,
    badge: 'Epistemic Gate ≥0.28',
    description: 'Strict evidence-backed answers with transcript citations',
  },
  {
    id: 'ship30',
    label: 'Ship 30 Essay',
    icon: PenNib,
    badge: '~1,250 Words',
    description: 'Viral essay with bold anchors, direct quotes, and 5 takeaways',
  },
  {
    id: 'experiments',
    label: 'Growth Experiments',
    icon: Flask,
    badge: 'ICE Calculator',
    description: 'Structured hypotheses, guardrail metrics, and 48h smoke tests',
  },
  {
    id: 'playbooks',
    label: 'Operational Playbook',
    icon: BookOpen,
    badge: '4 Pillars Matrix',
    description: 'Acquisition, Activation, Retention, and Monetization plays',
  },
];

export default function ModeSelector({ activeMode, onSelectMode, disabled = false }) {
  return (
    <div className="flex flex-wrap items-center gap-2 p-1.5 bg-slate-900/80 border border-slate-800/80 rounded-2xl backdrop-blur-md">
      {MODES.map((m) => {
        const Icon = m.icon;
        const isActive = activeMode === m.id;
        return (
          <button
            key={m.id}
            disabled={disabled}
            onClick={() => onSelectMode(m.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
              isActive
                ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)] font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-[0.98]'}`}
            title={m.description}
          >
            <Icon size={16} weight={isActive ? 'fill' : 'bold'} />
            <span>{m.label}</span>
            <span
              className={`hidden md:inline-block px-1.5 py-0.5 text-[9px] font-mono rounded ${
                isActive
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : 'bg-slate-800/80 text-slate-500'
              }`}
            >
              {m.badge}
            </span>
          </button>
        );
      })}
    </div>
  );
}
