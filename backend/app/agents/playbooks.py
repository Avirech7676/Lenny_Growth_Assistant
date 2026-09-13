"""Operational Growth Playbook specification, 4-pillar validator, and matrix widget builder."""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class PlaybookValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether all 4 operational pillars are present")
    has_acquisition: bool = Field(..., description="Acquisition pillar defined")
    has_activation: bool = Field(..., description="Activation pillar defined")
    has_retention: bool = Field(..., description="Retention pillar defined")
    has_monetization: bool = Field(..., description="Monetization pillar defined")
    pillars_detected: int = Field(..., description="Count of pillars detected")
    guest_referenced: bool = Field(..., description="Guest case study explicitly referenced")
    feedback: List[str] = Field(default_factory=list, description="Diagnostic validation feedback")


def validate_growth_playbook(content: str) -> PlaybookValidationResult:
    """Deterministically parse and validate an Operational Growth Playbook."""
    text_only = re.sub(r'<artifact.*?</artifact>', '', content, flags=re.DOTALL).strip()
    feedback: List[str] = []

    # 1. Check for the 4 core pillars
    has_acquisition = bool(re.search(r'(?:Acquisition|Organic\s*Loops|Growth\s*Loops)', text_only, re.IGNORECASE))
    has_activation = bool(re.search(r'(?:Activation|Onboarding|Time-to-Value|Click-Depth)', text_only, re.IGNORECASE))
    has_retention = bool(re.search(r'(?:Retention|Habit|High-Agency|Cadence|Orchestra)', text_only, re.IGNORECASE))
    has_monetization = bool(re.search(r'(?:Monetization|Pricing|Efficiency|Performance\s*Marketing)', text_only, re.IGNORECASE))

    pillars_detected = sum([has_acquisition, has_activation, has_retention, has_monetization])

    if not has_acquisition:
        feedback.append("Pillar 1 (Acquisition) is missing.")
    if not has_activation:
        feedback.append("Pillar 2 (Activation) is missing.")
    if not has_retention:
        feedback.append("Pillar 3 (Retention) is missing.")
    if not has_monetization:
        feedback.append("Pillar 4 (Monetization) is missing.")

    # 2. Check for guest attribution / case study
    guest_referenced = bool(re.search(r'(?:Brian\s*Chesky|Shreyas\s*Doshi|Lenny)', text_only, re.IGNORECASE))
    if not guest_referenced:
        feedback.append("No explicit guest case study referenced.")

    is_valid = (pillars_detected == 4 and guest_referenced)

    return PlaybookValidationResult(
        is_valid=is_valid,
        has_acquisition=has_acquisition,
        has_activation=has_activation,
        has_retention=has_retention,
        has_monetization=has_monetization,
        pillars_detected=pillars_detected,
        guest_referenced=guest_referenced,
        feedback=feedback,
    )


def generate_playbook_matrix_artifact(
    title: str,
    guest_name: str,
    acquisition_items: List[str],
    activation_items: List[str],
    retention_items: List[str],
    monetization_items: List[str],
) -> str:
    """Generate an interactive, dark-mode Growth Playbook Matrix widget for the Growth Canvas."""
    def render_items(items: List[str]) -> str:
        return "".join(f'<li class="text-xs text-slate-300 leading-snug">• {it}</li>' for it in items[:3])

    return f"""<artifact type="html" title="{title} — Strategic Growth Matrix">
<div class="p-6 bg-slate-900 rounded-xl border border-slate-800 font-sans text-slate-100 shadow-2xl">
  <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
    <div>
      <span class="text-[11px] font-mono tracking-wider uppercase text-emerald-400 font-semibold">Executive Strategy • Growth Playbook Matrix</span>
      <h3 class="text-lg font-bold text-white mt-0.5">{title}</h3>
    </div>
    <span class="px-2.5 py-1 text-[11px] font-mono font-medium rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60">{guest_name}</span>
  </div>

  <div class="grid grid-cols-2 gap-4">
    <div class="p-4 bg-slate-800/70 rounded-lg border border-slate-700/60">
      <div class="flex items-center gap-2 mb-2">
        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
        <h4 class="text-xs font-bold uppercase tracking-wider text-white">1. Acquisition Loops</h4>
      </div>
      <ul class="space-y-1.5 pl-1">
        {render_items(acquisition_items)}
      </ul>
    </div>

    <div class="p-4 bg-slate-800/70 rounded-lg border border-slate-700/60">
      <div class="flex items-center gap-2 mb-2">
        <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
        <h4 class="text-xs font-bold uppercase tracking-wider text-white">2. Frictionless Activation</h4>
      </div>
      <ul class="space-y-1.5 pl-1">
        {render_items(activation_items)}
      </ul>
    </div>

    <div class="p-4 bg-slate-800/70 rounded-lg border border-slate-700/60">
      <div class="flex items-center gap-2 mb-2">
        <span class="w-2 h-2 rounded-full bg-indigo-400"></span>
        <h4 class="text-xs font-bold uppercase tracking-wider text-white">3. Unified Retention</h4>
      </div>
      <ul class="space-y-1.5 pl-1">
        {render_items(retention_items)}
      </ul>
    </div>

    <div class="p-4 bg-slate-800/70 rounded-lg border border-slate-700/60">
      <div class="flex items-center gap-2 mb-2">
        <span class="w-2 h-2 rounded-full bg-amber-400"></span>
        <h4 class="text-xs font-bold uppercase tracking-wider text-white">4. High-Margin Monetization</h4>
      </div>
      <ul class="space-y-1.5 pl-1">
        {render_items(monetization_items)}
      </ul>
    </div>
  </div>
</div>
</artifact>"""
