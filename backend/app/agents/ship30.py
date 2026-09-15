"""Ship 30 for 30 dedicated viral essay engine, structural analyzer, and artifact builder.

SOURCE & REFERENCE ATTRIBUTION:
Writing principles, essay architecture, and structural invariants are derived directly from
Nicolas Cole & Dickie Bush's official 'Ship 30 for 30' curriculum and foundational text
'The Art and Business of Online Writing: How to Beat the Game of Modern Digital Content' (Nicolas Cole),
specifically:
1. The 1-2 sentence counterintuitive Hook attacking conventional dogma.
2. The Tension / Antagonist defining the cost of status-quo conventional wisdom.
3. 3 Core Pillars with bold anchor sentences, single-concept paragraphs, and direct quotes.
4. The 5-Point Actionable Takeaway checklist actionable immediately.
5. The 1-sentence Punchy Outro creating closure.
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Ship30AnalysisResult(BaseModel):
    is_valid: bool = Field(..., description="Whether all 5 core sections are present")
    word_count: int = Field(..., description="Total word count of essay")
    has_hook: bool = Field(..., description="Hook section detected")
    has_tension: bool = Field(..., description="Tension / Antagonist detected")
    pillar_count: int = Field(..., description="Count of pillars detected")
    has_bold_anchors: bool = Field(..., description="Pillars contain bold anchor sentences")
    takeaway_count: int = Field(..., description="Count of actionable takeaway items")
    has_outro: bool = Field(..., description="Punchy outro detected")
    quotes_found: int = Field(..., description="Number of quoted excerpts detected")
    structural_score: float = Field(..., description="Quality score from 0.0 to 100.0")
    feedback: List[str] = Field(default_factory=list, description="Diagnostic structural feedback")


def analyze_ship30_essay(content: str) -> Ship30AnalysisResult:
    """Perform deterministic structural quality analysis on a Ship 30 for 30 essay."""
    # Strip artifact block for text analysis
    text_only = re.sub(r'<artifact.*?</artifact>', '', content, flags=re.DOTALL).strip()
    words = re.findall(r'\b\w+\b', text_only)
    word_count = len(words)

    feedback: List[str] = []

    # 1. Hook detection: find the first substantive non-heading paragraph
    paragraphs = [p.strip() for p in text_only.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    first_paragraph = paragraphs[0] if paragraphs else ""
    has_hook = len(first_paragraph.split()) >= 10

    # 2. Tension / Antagonist detection
    tension_keywords = ["illusion", "conventional", "fail", "burnout", "chaos", "trap", "myth", "problem", "bloat"]
    has_tension = any(kw in text_only.lower() for kw in tension_keywords)
    if not has_tension:
        feedback.append("Tension section is missing or lacks conflict keywords.")

    # 3. Pillar count and bold anchors
    # Look for "Pillar 1", "Pillar 2", "Pillar 3" or numbered headings
    pillar_matches = re.findall(r'(?:###?\s*(?:Pillar|\d+)[:\.\s]+[^\n]+)', text_only, re.IGNORECASE)
    pillar_count = len(pillar_matches)
    if pillar_count < 3:
        # Fallback: check bold anchors like "**Pillar 1:**" or "### [Heading]"
        alt_pillars = re.findall(r'(?:###\s+[^\n]+|\*\*(?:Pillar|Core|Key|Step)\s*\d+[:\.\s]+[^\*]+\*\*)', text_only)
        pillar_count = max(pillar_count, len(alt_pillars))

    # Bold anchor check: pillars must start or contain bold anchor lines
    bold_anchors = re.findall(r'\*\*[^\*]{10,80}\*\*', text_only)
    has_bold_anchors = len(bold_anchors) >= 3

    if pillar_count < 3:
        feedback.append(f"Detected only {pillar_count} pillars (expected 3).")
    if not has_bold_anchors:
        feedback.append("Pillars require explicit bold anchor statements.")

    # 4. 5-Point Takeaways
    # Match numbered lists (1. , 2. , 3. ...)
    list_items = re.findall(r'^\s*\d+\.\s+[^\n]+', text_only, re.MULTILINE)
    takeaway_count = len(list_items)
    if takeaway_count < 5:
        # Check bullet points under a takeaways heading
        bullet_items = re.findall(r'^\s*[\-\*]\s+[^\n]+', text_only, re.MULTILINE)
        if len(bullet_items) >= 5:
            takeaway_count = len(bullet_items)

    if takeaway_count < 5:
        feedback.append(f"Detected only {takeaway_count} takeaways (expected 5).")

    # 5. Outro detection
    outro_keywords = ["bottom line", "takeaway", "conclusion", "remember", "the real lesson", "in short", "summary"]
    has_outro = any(kw in text_only.lower()[-300:] for kw in outro_keywords) or len(text_only.split("\n\n")[-1].strip()) > 20

    # 6. Quotes count
    quotes = re.findall(r'"([^"]{15,})"', text_only) + re.findall(r'>\s*"?([^"\n]{15,})', text_only)
    quotes_found = len(quotes)
    if quotes_found == 0:
        feedback.append("No direct quotes or cited excerpts found from transcript.")

    # Calculate structural score (0 to 100)
    score = 0.0
    if has_hook:
        score += 15.0
    if has_tension:
        score += 15.0
    score += min(30.0, pillar_count * 10.0)
    if has_bold_anchors:
        score += 10.0
    score += min(20.0, takeaway_count * 4.0)
    if has_outro:
        score += 10.0

    is_valid = (has_hook and has_tension and pillar_count >= 3 and takeaway_count >= 5)

    return Ship30AnalysisResult(
        is_valid=is_valid,
        word_count=word_count,
        has_hook=has_hook,
        has_tension=has_tension,
        pillar_count=pillar_count,
        has_bold_anchors=has_bold_anchors,
        takeaway_count=takeaway_count,
        has_outro=has_outro,
        quotes_found=quotes_found,
        structural_score=round(score, 1),
        feedback=feedback,
    )


def generate_ship30_cheat_sheet_artifact(title: str, guest_name: str, pillars: List[str], takeaways: List[str]) -> str:
    """Generate a high-density, beautifully styled HTML Cheat Sheet widget for the Growth Canvas."""
    pillar_html = "".join(f'<li class="p-2.5 rounded bg-slate-800/80 border border-slate-700/50 text-slate-200 text-xs leading-relaxed"><strong class="text-emerald-400">Pillar {i+1}:</strong> {p}</li>' for i, p in enumerate(pillars[:3]))
    takeaway_html = "".join(f'<li class="flex items-start gap-2 text-xs text-slate-300"><span class="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">{i+1}</span><span>{t}</span></li>' for i, t in enumerate(takeaways[:5]))

    return f"""<artifact type="html" title="{title} — Executive Cheat Sheet">
<div class="p-6 bg-slate-900 rounded-xl border border-slate-800 font-sans text-slate-100 shadow-2xl">
  <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
    <div>
      <span class="text-[11px] font-mono tracking-wider uppercase text-emerald-400 font-semibold">Ship 30 for 30 • Executive Cheat Sheet</span>
      <h3 class="text-lg font-bold text-white mt-0.5">{title}</h3>
    </div>
    <span class="px-2.5 py-1 text-[11px] font-mono font-medium rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60">{guest_name}</span>
  </div>

  <div class="space-y-4">
    <div>
      <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Three Core Strategic Pillars</h4>
      <ul class="space-y-2">
        {pillar_html}
      </ul>
    </div>

    <div>
      <h4 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">9 AM Actionable Checklist</h4>
      <ul class="space-y-2">
        {takeaway_html}
      </ul>
    </div>
  </div>
</div>
</artifact>"""
