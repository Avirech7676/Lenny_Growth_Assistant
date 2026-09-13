"""Growth Experiment Generator specification, ICE scoring engine, and interactive widget builder."""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ExperimentValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether all core experiment fields are present")
    has_objective: bool = Field(..., description="Clear objective statement")
    has_hypothesis: bool = Field(..., description="Hypothesis (If/Then/Because structure)")
    has_metrics: bool = Field(..., description="Primary and guardrail metrics defined")
    ice_impact: Optional[float] = Field(None, description="Impact score (1-10)")
    ice_confidence: Optional[float] = Field(None, description="Confidence score (1-10)")
    ice_ease: Optional[float] = Field(None, description="Ease score (1-10)")
    ice_composite: Optional[float] = Field(None, description="Calculated composite ICE score")
    has_precedent: bool = Field(..., description="Transcript precedent / case study present")
    has_smoke_test: bool = Field(..., description="48-hour lowest-cost smoke test defined")
    feedback: List[str] = Field(default_factory=list, description="Diagnostic validation feedback")


def validate_growth_experiment(content: str) -> ExperimentValidationResult:
    """Deterministically parse and validate a Growth Experiment specification."""
    text_only = re.sub(r'<artifact.*?</artifact>', '', content, flags=re.DOTALL).strip()
    feedback: List[str] = []

    # 1. Objective check
    has_objective = bool(re.search(r'(?:###?\s*Objective|Objective\b)', text_only, re.IGNORECASE))
    if not has_objective:
        feedback.append("Objective section is missing.")

    # 2. Hypothesis check
    has_hypothesis = bool(re.search(r'(?:###?\s*Hypothesis|Hypothesis\b)', text_only, re.IGNORECASE))
    if not has_hypothesis:
        feedback.append("Hypothesis section is missing.")

    # 3. Metrics check (primary and guardrail)
    has_metrics = bool(re.search(r'(?:Primary|Target)\s*Metric', text_only, re.IGNORECASE)) and \
                  bool(re.search(r'Guardrail\s*Metric', text_only, re.IGNORECASE))
    if not has_metrics:
        feedback.append("Primary or Guardrail metrics are missing.")

    # 4. ICE Score extraction (ignoring any parenthetical scale like (1-10))
    impact_match = re.search(r'\bImpact\b(?:\s*\([^\)]*\))?[^\d\n]*?(\d+(?:\.\d+)?)', text_only, re.IGNORECASE)
    conf_match = re.search(r'\bConfidence\b(?:\s*\([^\)]*\))?[^\d\n]*?(\d+(?:\.\d+)?)', text_only, re.IGNORECASE)
    ease_match = re.search(r'\bEase\b(?:\s*\([^\)]*\))?[^\d\n]*?(\d+(?:\.\d+)?)', text_only, re.IGNORECASE)

    ice_impact = float(impact_match.group(1)) if impact_match else None
    ice_conf = float(conf_match.group(1)) if conf_match else None
    ice_ease = float(ease_match.group(1)) if ease_match else None

    ice_composite = None
    if ice_impact is not None and ice_conf is not None and ice_ease is not None:
        ice_composite = round((ice_impact + ice_conf + ice_ease) / 3.0, 1)
    else:
        feedback.append("Complete ICE scores (Impact, Confidence, Ease) could not be parsed.")

    # 5. Transcript Precedent check
    has_precedent = bool(re.search(r'(?:Transcript\s*(?:Precedent|Evidence)|Case\s*Study)', text_only, re.IGNORECASE))
    if not has_precedent:
        feedback.append("Transcript precedent or case study reference is missing.")

    # 6. 48-Hour Smoke Test check
    has_smoke_test = bool(re.search(r'(?:48-Hour|Smoke\s*Test|Lowest-Cost)', text_only, re.IGNORECASE))
    if not has_smoke_test:
        feedback.append("48-Hour lowest-cost smoke test is missing.")

    is_valid = (has_objective and has_hypothesis and has_metrics and (ice_composite is not None) and has_smoke_test)

    return ExperimentValidationResult(
        is_valid=is_valid,
        has_objective=has_objective,
        has_hypothesis=has_hypothesis,
        has_metrics=has_metrics,
        ice_impact=ice_impact,
        ice_confidence=ice_conf,
        ice_ease=ice_ease,
        ice_composite=ice_composite,
        has_precedent=has_precedent,
        has_smoke_test=has_smoke_test,
        feedback=feedback,
    )


def generate_ice_calculator_artifact(
    title: str,
    guest_name: str,
    impact: float = 9.0,
    confidence: float = 8.0,
    ease: float = 7.0,
) -> str:
    """Generate an interactive, dark-mode ICE Calculator widget for the Growth Canvas."""
    composite = round((impact + confidence + ease) / 3.0, 1)
    return f"""<artifact type="html" title="{title} — Interactive ICE Calculator">
<div class="p-6 bg-slate-900 rounded-xl border border-slate-800 font-sans text-slate-100 shadow-2xl">
  <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
    <div>
      <span class="text-[11px] font-mono tracking-wider uppercase text-emerald-400 font-semibold">Growth Experiment • ICE Prioritization</span>
      <h3 class="text-lg font-bold text-white mt-0.5">{title}</h3>
    </div>
    <span class="px-2.5 py-1 text-[11px] font-mono font-medium rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60">{guest_name}</span>
  </div>

  <div class="grid grid-cols-3 gap-3 mb-5">
    <div class="p-3 bg-slate-800/80 rounded-lg border border-slate-700/60 text-center">
      <span class="block text-[10px] font-mono uppercase tracking-wider text-slate-400">Impact (1-10)</span>
      <span class="text-2xl font-extrabold text-emerald-400 mt-1 block">{impact}</span>
      <span class="text-[10px] text-slate-400 mt-0.5 block">High Revenue Lift</span>
    </div>
    <div class="p-3 bg-slate-800/80 rounded-lg border border-slate-700/60 text-center">
      <span class="block text-[10px] font-mono uppercase tracking-wider text-slate-400">Confidence (1-10)</span>
      <span class="text-2xl font-extrabold text-cyan-400 mt-1 block">{confidence}</span>
      <span class="text-[10px] text-slate-400 mt-0.5 block">Transcript Backed</span>
    </div>
    <div class="p-3 bg-slate-800/80 rounded-lg border border-slate-700/60 text-center">
      <span class="block text-[10px] font-mono uppercase tracking-wider text-slate-400">Ease (1-10)</span>
      <span class="text-2xl font-extrabold text-indigo-400 mt-1 block">{ease}</span>
      <span class="text-[10px] text-slate-400 mt-0.5 block">Rapid Smoke Test</span>
    </div>
  </div>

  <div class="p-4 bg-slate-950/80 rounded-lg border border-emerald-900/40 flex items-center justify-between">
    <div>
      <span class="text-xs font-semibold text-slate-300">Composite ICE Score</span>
      <p class="text-[11px] text-slate-500">Arithmetic mean: (I + C + E) / 3</p>
    </div>
    <div class="flex items-baseline gap-1">
      <span class="text-3xl font-black text-emerald-400">{composite}</span>
      <span class="text-xs text-slate-500 font-mono">/ 10.0</span>
    </div>
  </div>
</div>
</artifact>"""
