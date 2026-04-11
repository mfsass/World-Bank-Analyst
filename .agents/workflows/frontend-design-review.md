---
description: Review and polish frontend components against the three design layers — appearance tokens, animation craft, and design taste. Use when building new components, touching existing UI, or doing a design quality pass before presentation.
---

## When to Use

Run this agent when you:
- Build a new React component or page
- Modify existing frontend UI code
- Want a design quality audit before a demo or PR
- Suspect a component "works but feels off"
- Need to add interaction states, animation, or polish to an existing surface

## The Three Layers

This agent orchestrates three complementary skills. Read each one before starting work:

| Layer | Skill | What it decides |
|-------|-------|-----------------|
| Appearance | `.github/skills/world-analyst-design-system/SKILL.md` | Colors, fonts, surfaces, spacing, borders, component structure |
| Motion | `.github/skills/emil-design-eng/SKILL.md` | Easing curves, durations, springs, gesture thresholds, transform-origin, stagger |
| Judgment | `.github/skills/design-taste-frontend/SKILL.md` | Layout philosophy, anti-AI-slop, interactive states, creative proactivity |

**Precedence:** Appearance layer wins on any visual token conflict. Motion layer wins on any animation decision. Judgment layer provides the overarching quality filter.

## Steps

### Phase 1: Audit

1. Read the target component(s) and `frontend/src/index.css` to understand the current state.
// turbo

2. Run the **Appearance Audit** — check every visual property against `world-analyst-design-system`:
   - Surface hierarchy: canvas `#0E0E0E`, card `#1A1A1A`, nested `#201F1F`, popover `#262626`
   - Accent `#FF4500` used only for AI content or primary CTAs
   - All colors via CSS custom properties, never hardcoded hex in components
   - Typography: Inter for narrative, Commit Mono for metrics/labels
   - Labels: uppercase, 0.05em tracking, Commit Mono 0.6875rem/700
   - All radius = 8px, all borders = 1px solid `#262626`
   - No box-shadow, no backdrop-filter, no blur, no gradients (except AI insight card)
   - 32px gap between major sections, 4/8px grid increments

3. Run the **Design Taste Audit** — check against `design-taste-frontend` Section 7 (AI Tells):
   - No generic 3-column card rows
   - No pure black (`#000000`) — use design system surfaces
   - No oversaturated accents
   - No generic placeholder names/numbers in mock data
   - No filler words ("Elevate", "Seamless", "Unleash")
   - Loading, empty, and error states exist for data-dependent components
   - Interactive elements have `:hover`, `:focus`, and `:active` states
   - Forms follow label-above-input pattern

4. Run the **Motion Audit** — check against `emil-design-eng`:
   - No `transition: all` — specify exact properties
   - No `ease-in` on UI elements — use `ease-out` or custom curve
   - No `scale(0)` entry animations — start from `scale(0.95)` minimum
   - Durations under 300ms for UI elements
   - Hover animations gated behind `@media (hover: hover) and (pointer: fine)`
   - `prefers-reduced-motion` media query present when animations exist
   - Buttons have `transform: scale(0.97)` or similar on `:active`
   - Stagger delays between 30-80ms for list/grid entries

### Phase 2: Report

5. Produce a **Design Review Table** with all findings:

```markdown
| Component | Layer | Issue | Fix | Priority |
|-----------|-------|-------|-----|----------|
| KpiCard | Appearance | Hardcoded #737373 | Use var(--color-text-secondary) | High |
| MarketSwitcher | Motion | transition: all 0.3s | transition: opacity 200ms ease-out | Medium |
| GlobalOverview | Judgment | No empty state | Add composed empty state for no-data | High |
```

Priority levels:
- **High** — Design system violation or broken interaction state
- **Medium** — Polish issue visible to users
- **Low** — Craft refinement, nice-to-have

### Phase 3: Fix

6. Apply High-priority fixes first, then Medium. Low-priority fixes are optional unless the user requests a full polish pass.

7. For each fix, verify:
   - CSS uses custom properties from `index.css`, not hardcoded values
   - New animations follow the decision framework (should it animate? what easing? how fast?)
   - No new anti-patterns introduced from the AI Tells list
   - Component still renders correctly (run `cd frontend && npm run build` to verify)

8. Run the frontend build to confirm no regressions:
```bash
cd frontend && npm run build
```

## Rules

- **Never override design system tokens.** If a token feels wrong, flag it — don't change it inline.
- **Never add dependencies without checking `package.json` first.** If Framer Motion or another library is needed, confirm with the user before installing.
- **Motion is invisible when done right.** If a user would consciously notice an animation on their 50th use, it's too much.
- **Match motion to mood.** This is a data-dense, engineering-grade dashboard. Shorter durations, no bounce, strong ease-out curves. The data is the star; motion stays supportive.
- **Anti-slop is non-negotiable.** Every pattern in Section 7 of `design-taste-frontend` is a hard filter, not a suggestion.
