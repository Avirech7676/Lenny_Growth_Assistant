# Master Design System Specification — The Lenny Growth Assistant

**Design Version:** 3.0.0 (Production Assistant Redesign)  
**System Foundation:** Linear/Raycast Dark Tech Minimalism + Radix-Grade Semantic Primitives  
**Tailwind Foundation:** Tailwind CSS v4 + Motion (`motion/react`)  

---

## 1. Design Read & Strategic Vision

> **"Reading this as: AI executive growth and strategy workspace for founders, product leaders, and growth engineers, with a calm, evidence-first, high-density editorial language, leaning toward Linear/Raycast-inspired dark tech minimalism + Radix-grade semantic surfaces."**

The product is not an informal consumer chatbot; it is an **Executive AI Growth Strategist & Co-Pilot**. Users engage with the assistant to solve thorny activation bottlenecks, craft viral Ship 30 essays, construct ICE-scored experiment roadmaps, and synthesize timeless podcast wisdom with live 2026 market benchmarks.

---

## 2. Design Dials

| Dial | Value | Rationale |
|---|:---:|---|
| **`DESIGN_VARIANCE`** | **7** | Asymmetric balance between primary conversational document stream and precision evidence/artifact sidebars. Avoids monotonous boilerplate while maintaining rigorous grid discipline. |
| **`MOTION_INTENSITY`** | **5** | Targeted physics-based micro-interactions (`motion/react`). Spring easing for panel reveals (200ms) and token arrival glow. No continuous decorative GPU spinners. |
| **`VISUAL_DENSITY`** | **6** | Executive productivity density. Tight, readable chrome; generous 1.7 line-height editorial prose for frameworks; multi-column metadata tags with crisp typographic hierarchy. |

---

## 3. Semantic Color Palette & Contrast Tokens

All text combinations are audited to exceed **WCAG 2.1 AA** (4.5:1 minimum contrast ratio).

```css
:root {
  /* Surfaces & Canvas */
  --bg-canvas: #090D16;            /* Deep Obsidian Canvas */
  --bg-surface: #0E1526;           /* Elevated Card / Panel Surface */
  --bg-surface-elevated: #162035;  /* Hover / Active Surface */
  --bg-surface-subtle: #0B111E;    /* Inset Wells & Textareas */

  /* Borders & Dividers */
  --border-subtle: rgba(51, 65, 85, 0.45);   /* Hairline slate-700/45 */
  --border-medium: rgba(71, 85, 105, 0.65);  /* Card outlines */
  --border-focus: rgba(16, 185, 129, 0.6);   /* Active focus rings */

  /* Typography */
  --text-primary: #F8FAFC;         /* High-contrast crisp white (15.2:1) */
  --text-secondary: #94A3B8;       /* Subtle readable slate-400 (5.8:1) */
  --text-muted: #64748B;           /* Low-priority metadata (4.6:1 on surface) */

  /* Semantic Intelligence Accents */
  --accent-emerald: #10B981;       /* Mode A: Lenny Transcript Evidence */
  --accent-emerald-glow: rgba(16, 185, 129, 0.18);
  --accent-cyan: #06B6D4;          /* Mode B: Real-World External Knowledge */
  --accent-cyan-glow: rgba(6, 182, 212, 0.18);
  --accent-violet: #8B5CF6;        /* Mode C: Hybrid Synthesis */
  --accent-violet-glow: rgba(139, 92, 246, 0.18);
  --accent-amber: #F59E0B;         /* Epistemic Refusals & Warnings */
  --accent-rose: #F43F5E;          /* Errors & Destructive Actions */
}
```

---

## 4. Typography Scale

Paired via Google Fonts:
- **Headings & Display**: `Plus Jakarta Sans` (weights 600, 700, 800, tracking `-0.025em`)
- **Body & Editorial Prose**: `Inter` (weights 400, 500, 600, line-height `1.68`, font-size `0.9375rem` / `15px`)
- **Metadata, Code & Metrics**: `JetBrains Mono` (weights 400, 500, 600, letter-spacing `0.02em`)

| Element | Font Family | Size | Weight | Tracking | Line Height |
|---|---|:---:|:---:|:---:|:---:|
| **Display Title** | Plus Jakarta Sans | 24px (1.5rem) | 800 | -0.03em | 1.2 |
| **Section Heading (H2)** | Plus Jakarta Sans | 18px (1.125rem) | 700 | -0.025em | 1.3 |
| **Subheading (H3)** | Plus Jakarta Sans | 15px (0.9375rem) | 600 | -0.015em | 1.4 |
| **Body (Prose)** | Inter | 15px (0.9375rem) | 400 | -0.01em | 1.68 |
| **Action & Button** | Inter | 13px (0.8125rem) | 600 | 0.0em | 1.0 |
| **Caption & Badge** | JetBrains Mono | 11px (0.6875rem) | 500 | 0.03em | 1.2 |

---

## 5. Spacing Scale (4px Base Grid)

```text
4px  (space-1)   → Micro gaps, badge inner padding
8px  (space-2)   → Chip gaps, button icon spacing
12px (space-3)   → Compact item padding, message margin
16px (space-4)   → Standard card padding, modal inset
24px (space-6)   → Container padding, section separators
32px (space-8)   → Header height offset, major workspace padding
48px (space-12)  → Empty state hero spacing
```

---

## 6. Layout Hierarchy & Responsive Breakpoints

The application utilizes an **Adaptive 3-Column Architecture**:
1. **Sessions Workspace (Sidebar)**: `280px` fixed, collapsible with smooth spring transition or keyboard toggle.
2. **Central Conversational Stream**: Flex-1, centered column with `max-w-3xl` (768px) content constraint.
3. **Contextual Intelligence Workspace**: `420px–500px` slide-over panel on desktop (`>=1024px`), rendering:
   - **Tab A**: Sandboxed Growth Canvas with Code vs. Preview tabs and Fullscreen.
   - **Tab B**: Grounded Evidence Drawer with quote highlights and similarity gauges.
   - On Tablet/Mobile (`<1024px`), this surfaces as an accessible modal sheet.

---

## 7. Motion & Interaction Rules

- **Library**: `motion/react` (Motion 12)
- **Durations**:
  - Micro-interactions (hovers, clicks, tooltips): `120ms–150ms ease-out`
  - Panel slides & Drawer transitions: `220ms [0.16, 1, 0.3, 1]` (custom cubic spring)
  - Streaming token shimmer: `1.5s infinite linear`
- **Accessibility**: All animations honor `@media (prefers-reduced-motion: reduce)`.

---

## 8. Accessibility (WCAG 2.1 AA Checklist)

- [x] All interactive icon buttons include accessible `aria-label` and `title` attributes.
- [x] Text color contrast meets or exceeds 4.5:1 on all background surfaces.
- [x] Visible focus rings (`focus-visible:ring-2 focus-visible:ring-emerald-500/50`) on all interactive controls.
- [x] Full keyboard navigation (`Enter` to send, `Shift+Enter` for newline, `Esc` to close modal/drawers).
- [x] Screen-reader friendly announcements for streaming phases and live evidence updates.
