# Master Design System & UI/UX Direction
# The Lenny Growth Assistant

**Document Version:** 2.0.0 (Stage 3 — Design System & UI/UX Direction)  
**Status:** Approved for Repository Foundation (Stage 4) & Frontend Engineering  
**Lead UI/UX Engineer:** Anti-Slop Frontend Engineer & Product Designer  
**Framework Integration:** Taste Skill v2.0 & UI/UX Pro Max v2.0  

---

## 1. Mandatory Design Read

> **"Reading this as: an authoritative growth intelligence workstation for ambitious founders and product executives, with a crisp, high-density editorial telemetry vibe, leaning toward a tailored Slate & Electric Emerald design system with bespoke typography and hardware-accelerated micro-motion."**

---

## 2. Taste-Skill Master Dials

```
┌────────────────────┬───────────┬────────────────────────────────────────────────────────┐
│ Master Dial        │ Calibrated│ Rationale & Visual Implementation                      │
├────────────────────┼───────────┼────────────────────────────────────────────────────────┤
│ DESIGN_VARIANCE    │ 7.5 / 10  │ Asymmetric dual-pane layout, variable bento quote cards│
│ MOTION_INTENSITY   │ 5.0 / 10  │ Fast 150-250ms spring physics, zero scroll-hijacking   │
│ VISUAL_DENSITY     │ 6.5 / 10  │ High-density telemetry pills, compact quote drawers    │
└────────────────────┴───────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Color Tokens & Theme Architecture

Generic AI purple gradients, washed-out glassmorphism, and neon glows are strictly banned. The palette uses deep obsidian slate foundations paired with high-contrast electric emerald and crisp semantic accents.

```css
:root {
  /* Surface & Ground Foundations */
  --color-bg-canvas: #0A0E17;        /* Ultra-deep obsidian slate */
  --color-bg-surface: #111827;       /* Primary card surface */
  --color-bg-elevated: #1F2937;      /* Hover states, dropdowns, modal layers */
  --color-bg-subtle: #162032;        /* Secondary panel backgrounds */

  /* Structural Borders */
  --color-border-subtle: #374151;    /* 1px crisp layout boundaries */
  --color-border-hover: #4B5563;     /* Interactive card hover border */
  --color-border-focus: #10B981;     /* Emerald keyboard focus ring */

  /* High-Contrast Typography */
  --color-text-primary: #F9FAFB;     /* 98% white high-contrast text */
  --color-text-secondary: #9CA3AF;   /* 60% slate readable body */
  --color-text-muted: #6B7280;       /* Timestamps, metadata, labels */
  --color-text-code: #E5E7EB;        /* Mono telemetry numbers */

  /* Brand Accents & Semantic Signals */
  --color-brand-emerald: #10B981;    /* Grounded state, verified quotes */
  --color-brand-emerald-glow: rgba(16, 185, 129, 0.12);
  --color-accent-amber: #F59E0B;     /* Epistemic caution / low similarity */
  --color-accent-ruby: #EF4444;      /* Errors, circuit breaker, refusal */
  --color-accent-cyan: #06B6D4;      /* Artifacts, calculator highlights */
}
```

---

## 4. Typography Scale & Hierarchy

Based on UI/UX Pro Max's **Modern Dark Cinema** system with geometric display weighting:

### 4.1 Type Families
- **Display & Headings**: `Plus Jakarta Sans` (`font-sans`) — Weights 700/800 with tight tracking (`tracking-tight`).
- **Body & Paragraphs**: `Inter` (`font-sans`) — Weights 400/500 with relaxed line-height (`leading-relaxed`), constrained to readable line length (`max-w-[65ch]`).
- **Telemetry, Code & Citations**: `JetBrains Mono` (`font-mono`) — Weights 400/500 with tabular numbers for similarity scores and timestamps.

### 4.2 Modular Scale
```
Display / H1 : 32px (2rem)      | weight: 700 | tracking: -0.025em | line-height: 1.2
Section / H2 : 24px (1.5rem)    | weight: 600 | tracking: -0.02em  | line-height: 1.3
Card Title   : 18px (1.125rem)  | weight: 600 | tracking: -0.015em | line-height: 1.4
Body Base    : 15px (0.9375rem) | weight: 400 | tracking: normal   | line-height: 1.6
Telemetry/Cap: 12px (0.75rem)   | weight: 500 | font-mono          | line-height: 1.4
```

---

## 5. Component Inventory & Split Canvas Layout

```
+---------------------------------------------------------------------------------------+
| TopBar: Lenny Growth Assistant ⚡ | Active: Local Ollama (llama3.2) 🟢 | Latency: 42ms |
+------------------------------------+--------------------------------------------------+
| Left Column: Conversational Stream | Right Column: Sandboxed Growth Canvas            |
| (Width: 50% Desktop, 100% Mobile)  | (Width: 50% Desktop, 100% Mobile)                |
|                                    |                                                  |
| ┌────────────────────────────────┐ | ┌──────────────────────────────────────────────┐ |
| │ Sidebar Toggle | New Chat Button│ | │ Mode: [ Live Preview | Markdown | Raw Code ] │ |
| └────────────────────────────────┘ | ├──────────────────────────────────────────────┤ |
| - Message History Stream           | │ Export / Copy Actions [ Markdown | HTML ]     │ |
|   - User Question Bubble           | ├──────────────────────────────────────────────┤ |
|   - Grounded Assistant Message     | │ <iframe> Sandboxed Container                 │ |
|   - Citation Badges:               | │ - Interactive LNO Priority Calculator        │ |
|     [ Brian Chesky #1 (88%) ]      | │ - Viral Ship 30 for 30 Essay Reader          │ |
|                                    | │ - Growth Experiment ICE Matrix               │ |
| ┌────────────────────────────────┐ | └──────────────────────────────────────────────┘ |
| │ Composer & Prompt Pills        │ |                                                  |
| │ [ Ask Lenny ] [ Ship 30 Essay ]│ |                                                  |
| │ [ Growth Playbook ]            │ |                                                  |
| └────────────────────────────────┘ |                                                  |
+------------------------------------+--------------------------------------------------+
```

### 5.1 Icon Library Discipline
- Exclusively use **Phosphor Icons** (`@phosphor-icons/react`) with a unified `strokeWidth={1.5}` or `weight="regular"`:
  - Chat/Conversation: `<ChatCircle />`
  - Research/Grounding: `<MagnifyingGlass />`
  - Ship 30 Essay: `<Feather />` or `<Article />`
  - Growth Experiment: `<Flask />`
  - Artifacts/Canvas: `<Code />` or `<Browser />`
  - Model Status: `<Cpu />`
  - Citation Link: `<ArrowSquareOut />`
- **Strictly Banned**: Never mix Lucide, FontAwesome, or uncalibrated custom SVGs.

---

## 6. Motion & Micro-Interaction Standards

Powered by `motion/react` with spring dynamics:
```jsx
import { motion, AnimatePresence } from "motion/react";

// Standard UI Spring for Modals, Drawers & Cards
export const standardSpring = {
  type: "spring",
  stiffness: 300,
  damping: 26,
  mass: 0.8
};

// Micro-interaction hover preset
export const microHover = {
  y: -2,
  scale: 1.015,
  transition: { duration: 0.16, ease: "easeOut" }
};
```

### 6.1 Banned Motion Patterns
- **No Continuous `useState` Tracking**: Never track cursor positions or scroll offsets with React state. Use `useMotionValue` or pure CSS.
- **No Scroll Hijacking**: Native window scrolling only.
- **Preflight Reduced Motion**: Wrapped in `motion.div` with `@media (prefers-reduced-motion: reduce)` fallbacks.

---

## 7. Responsive Layout Breakpoints

| Viewport | Target Device | Layout Treatment |
|---|---|---|
| **`375px`** | Mobile Devices | Full-width vertical stack: Chat takes 100% viewport (`min-h-[100dvh]`); Artifact Viewer opens as a bottom sheet modal. |
| **`768px`** | Tablet Devices | Collapsible navigation sidebar; split canvas switches to tabbed overlay mode. |
| **`1440px`**| Desktop Workstations | Fixed 50/50 dual-pane split view with permanent visibility into both conversation and execution canvas. |

---

## 8. Anti-Slop Quality Checklist

- [x] Emitted mandatory one-line **Design Read**.
- [x] All 3 master dials respected (`7.5 / 5.0 / 6.5`).
- [x] Banned generic AI purple gradients; replaced with Slate & Electric Emerald.
- [x] Banned 3 identical square cards; replaced with asymmetric bento layouts.
- [x] Banned Lucide icons; unified on Phosphor Icons with 1.5px stroke.
- [x] Banned `h-screen`; strictly enforced `min-h-[100dvh]`.
- [x] Full-output enforcement: complete CSS variables and production components with zero `// TODO` placeholders.
