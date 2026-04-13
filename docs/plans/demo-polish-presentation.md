# Plan: Demo Polish & Presentation Readiness

**Track:** CEO — Demo quality and evaluator first impression  
**Status:** Implemented  
**Blocked by:** Nothing  
**Effort estimate:** 1–2 days frontend work  

---

## Goal

Three specific surfaces undermine the demo for a reviewer who clicks around without narration. Fix them before any presentation date.

1. **Global Overview right rail empty state** — the map is the hero but nothing appears when no country is selected. A finance evaluator's first click lands on a dead surface.
2. **How It Works static layout** — it explains mechanics but lacks any interactive element, which means the architecture slide is dead airtime during a live demo walk-through.
3. **Country panel rationale is undocumented for a finance audience** — reviewers will ask why Bahamas and El Salvador are in the panel instead of China and Germany. ADR-041 has the answer but it lives in the ADR log, not the UI or the README hero.

---

## Scope

### In scope

**Fix 1: Global Overview default state**  
When no country is selected on the map, the right rail should show meaningful content rather than an empty or "select a market" placeholder.

Proposed content when idle:
- Top-3 risk signals derived from the existing indicator layer (the same ranking logic already used in the signal pack)
- One-line panel summary from the stored `global_overview` record
- A prompt row directing to the country directory

This uses existing API data — no backend changes. The `overview` endpoint and current indicator payloads are sufficient.

**Fix 2: How It Works — interactive step sequence**  
Add a step-by-step reveal to the architecture page. The current static card layout should animate through the pipeline stages: World Bank fetch → Pandas analysis → Step 1 AI → Step 2 synthesis → Firestore → Dashboard.

Minimal viable: CSS-driven step highlight (current step lit, others dimmed) with a Next / Previous control. Shares the `PIPELINE_STAGES` model from `frontend/src/pipelineStageModel.js` — no duplicate copy.

**Fix 3: Country panel narrative — README and UI**  
Add one clear paragraph to the README Quick Start section explaining the 2024 exact-complete panel rationale: mechanically derived from World Bank completeness data, smallest scope with full 2010–2024 coverage across all 6 indicators, no editorial country selection. Link to ADR-041.

Add a one-line footnote to the Country Intelligence landing page footer: "17-country panel selected for complete 2010–2024 data coverage across all six indicators."

### Out of scope

- New backend endpoints
- Any changes to `api/openapi.yaml`
- Country Intelligence Phase 1 (historical timeline) — that's in the technical hardening plan
- How It Works full redesign — this is a minimal interactive upgrade, not a full page rebuild

---

## Affected files

| File | Change |
|---|---|
| `frontend/src/pages/GlobalOverview.jsx` | Add default-state content to the right rail when `selectedCountry` is null |
| `frontend/src/pages/HowItWorks.jsx` | Add step-by-step navigation using shared stage model |
| `frontend/src/pages/CountryIntelligenceLanding.jsx` | Add one-line panel footnote |
| `frontend/src/index.css` | Any CSS for the default-state rail and step highlight |
| `README.md` | Country panel rationale paragraph in Quick Start or Architecture section |

---

## Acceptance criteria

- [ ] Reviewer opens Global Overview, does not click any country — sees a non-empty right rail with actionable content derived from real API data
- [ ] Reviewer opens How It Works — at least one interactive element (step navigation) exists and responds within 200ms
- [ ] README explains the 17-country selection in plain prose within the first 200 lines, linking to ADR-041
- [ ] Country Intelligence landing page footer includes a visible panel coverage note
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

---

## Execution prompt

Paste this into a new conversation with the **world-analyst-implementer** agent:

---

> **Task:** Demo polish — Global Overview default state, How It Works interactivity, country panel narrative.
>
> **Context:** The project is the World Bank Analyst dashboard (`frontend/src/`). Read the plan at `docs/plans/demo-polish-presentation.md` before making any changes. Read the design system skill at `.github/skills/world-analyst-design-system/SKILL.md` and the design taste skill at `.github/skills/design-taste-frontend/SKILL.md` before touching any component or CSS.
>
> **Work 1 — Global Overview default state:**  
> In `frontend/src/pages/GlobalOverview.jsx`, when `selectedCountry` is null, the right rail should display: (a) the panel summary text from the `overview` API response, (b) the top-3 highest-risk signal cards ranked by z-score from the indicator layer, (c) a "Browse all markets →" CTA that routes to `/country`. Use existing API data — no new endpoints. Style with design system tokens only. No inline styles.
>
> **Work 2 — How It Works step navigation:**  
> In `frontend/src/pages/HowItWorks.jsx`, add a step-by-step highlight that walks through the pipeline stages using `PIPELINE_STAGES` from `frontend/src/pipelineStageModel.js`. Current step is fully lit; other steps are dimmed. Add Next / Previous buttons. Transition time ≤ 200ms. No new libraries.
>
> **Work 3 — Country panel narrative:**  
> In `README.md`, add one paragraph (3–5 sentences) to the Architecture section explaining the 17-country panel selection: mechanically derived from World Bank 2024 exact-completeness data, smallest set with full 2010–2024 coverage across all six indicators, no editorial selection. Link to `docs/DECISIONS.md` ADR-041. In `frontend/src/pages/CountryIntelligenceLanding.jsx`, add a one-line footer note below the country grid: "17-country panel — selected for complete 2010–2024 data across all indicators." Style as subdued metadata text using `var(--text-muted)`.
>
> **Constraints:**  
> - No backend changes, no `openapi.yaml` changes  
> - Design system tokens only — no raw hex values, no inline styles, no shadows  
> - `npm run lint` and `npm run build` must pass before marking done  
> - Log an ADR entry to `docs/DECISIONS.md` only if a genuine fork-in-the-road choice was made
