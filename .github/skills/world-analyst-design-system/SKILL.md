---
name: world-analyst-design-system
description: Engineering Intelligence design system for World Analyst. Use when designing UI components, writing CSS, choosing colors, implementing layouts, or reviewing frontend code. This skill defines the RULES — violations produce interfaces that fail the ML6 evaluation.
---

# World Analyst Design System — Engineering Intelligence

> **Purpose**: Define the visual language of the World Analyst terminal. Every CSS rule,
> every color choice, every font pairing must pass through these constraints.

---

## When to Apply

Use this skill when the task involves:

- Writing or modifying CSS (any file)
- Creating React components with visual output
- Choosing colors, spacing, typography, or layout patterns
- Reviewing frontend code for design consistency
- Building charts, KPI cards, maps, or data visualisations

**Skip** for backend logic, API design, pipeline code, or tests.

---

## The Aesthetic: Tactical Command Center

Premium through precision, not decoration. High-density, engineering-grade, unapologetically digital. If it feels like a consumer web app, it's wrong. If it feels like a Bloomberg terminal designed by Dieter Rams, it's right.

---

## Hard Constraints (Never Violate)

### 1. Surface Hierarchy

| Level | Background | Use |
|-------|-----------|-----|
| Level 0 (Canvas) | `#0E0E0E` | Page background |
| Level 1 (Card) | `#1A1A1A` | Cards, panels |
| Level 2 (Nested) | `#201F1F` | Inner containers, nested elements |
| Level 3 (Popover) | `#262626` | Tooltips, dropdowns |

**Rule:** Depth = tonal shift. Never use `box-shadow`, `backdrop-filter`, or any transparency effect.

### 2. Color Discipline

| Token | Hex | Reserved For |
|-------|-----|-------------|
| `--color-accent` | `#FF4500` | AI insights, primary CTAs, pipeline status |
| `--color-success` | `#22C55E` | Positive trends, operational status |
| `--color-warning` | `#F59E0B` | Caution indicators |
| `--color-critical` | `#EF4444` | Negative trends, errors |
| `--color-text-primary` | `#F5F5F5` | Primary text |
| `--color-text-secondary` | `#737373` | Secondary text — drop immediately, no mid-greys |
| `--color-border` | `#262626` | All structural borders |

**Rule:** `#FF4500` is ONLY for AI-generated content and primary actions. Using it for general decoration dilutes its semantic weight.

### 3. Typography: Dual-Font System

| Role | Font | Size | Weight | CSS Variable |
|------|------|------|--------|-------------|
| Display heading | Inter | 2.75rem | 700 | `--font-display` |
| Section heading | Inter | 1.5rem | 600 | `--font-headline` |
| Card title | Inter | 1rem | 600 | `--font-title` |
| Body text | Inter | 0.875rem | 400 | `--font-body` |
| Metric value | Commit Mono | 1.125rem | 500 | `--font-metric` |
| Label/micro | Commit Mono | 0.6875rem | 700 | `--font-label` |

**Rules:**
- Labels (`label-sm`): ALWAYS `uppercase` with `letter-spacing: 0.05em`
- Metrics: ALWAYS Commit Mono. If a number changes dynamically, it uses Commit Mono.
- Never use more than these 6 type sizes on a single page.

### 4. Spacing & Rhythm

- **Major sections:** 32px vertical gap (non-negotiable)
- **Grid base:** 4px / 8px increments: `4, 8, 12, 16, 24, 32, 48`
- **Card padding:** 24px internal padding
- **KPI row:** 4 columns, equal width, 16px gap

### 5. Borders & Radius

- **All borders:** 1px solid `#262626`
- **All radius:** 8px. Never more. Never less.
- **Focus state:** Border transitions to `#FF4500` (hard edge, no glow blur)
- **AI insight cards:** 4px left border in `#FF4500`

### 6. Components

| Component | Specification |
|-----------|--------------|
| Button (Primary) | Background `#FF4500`, text `#FFFFFF`, 8px radius, no gradient |
| Button (Ghost) | Background `transparent`, border 1px `#262626`, text `#F5F5F5` |
| Input | Background `#0E0E0E`, border 1px `#262626`, focus border `#FF4500` |
| KPI Card | `#1A1A1A` background, `label-sm` header, `custom-mono` value, data freshness label |
| AI Insight | Gradient background `#1A1A1A → #0E0E0E`, 4px left border `#FF4500`, `auto_awesome` icon |

---

## AI Insight Pattern (Signature Component)

The AI-Generated Insights panel is the crown jewel. It gets MORE visual energy than standard data:

```css
.ai-insight {
  background: linear-gradient(180deg, #1A1A1A 0%, #0E0E0E 100%);
  border-left: 4px solid #FF4500;
  border-radius: 8px;
  padding: 24px;
}
.ai-insight__icon {
  color: #FF4500; /* auto_awesome Material icon */
}
.ai-insight__highlight {
  font-family: 'Commit Mono', monospace;
  color: #FF4500;
}
```

---

## Pre-Commit Checklist

Before submitting any frontend code:

- [ ] All colors use CSS custom properties, never hardcoded hex
- [ ] No `box-shadow` anywhere
- [ ] No `backdrop-filter` or `blur`
- [ ] No `border-radius` value other than `8px`
- [ ] Commit Mono used for all dynamic numbers and labels
- [ ] Inter used for all narrative text
- [ ] 32px gap between major sections
- [ ] Secondary text uses `#737373`, not a custom grey
- [ ] `#FF4500` only appears on AI content or primary CTAs
- [ ] All interactive cards have 1px `#262626` border

---

## Anti-Patterns (Immediate Rejection)

- ❌ Tailwind classes
- ❌ Box shadows of any kind
- ❌ Glassmorphism, blur, transparency
- ❌ Border radius ≠ 8px
- ❌ Using `#FF4500` for non-AI, non-CTA elements
- ❌ Sans-serif font for metrics/numbers
- ❌ Icons used for decoration (icons are functional cues only)
- ❌ Missing hover/focus/active states on interactive elements
- ❌ Gradient backgrounds (except the AI insight card)
