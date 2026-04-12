# Global Overview Hero Redesign — Risk-First Terminal

**Goal:** Replace the double-header `PageHeader` + `AIInsightPanel` above-the-fold combo with a single unified hero section that leads with numbers and risk signals, not redundant labels and prose walls.

**Status:** PLANNING  
**Created:** 2026-04-12

---

## Problem Statement

The current above-the-fold landing wastes prime screen real estate:

1. **Double header pattern** — `PageHeader` renders "GLOBAL OVERVIEW / Global Overview", then `AIInsightPanel` repeats "GLOBAL SYNTHESIS / Global economic outlook". Two layers of labeling before any useful content.
2. **Text-heavy, metric-poor** — The AI synthesis paragraph (4+ lines) dominates arrival. Key numbers (anomalies, stress point, tracked markets, data year) are buried in small cards below the fold inside the `AIInsightPanel` body.
3. **Flat hierarchy** — Risk flags, narrative, and status pills all compete at equal visual weight.
4. **No visual tension** — No focal point, no information scent, no reason for the eye to stop.
5. **CTAs float without context** — "Open pipeline" and "Review country queue" sit in a detached `PageHeader` actions slot with no spatial relationship to the data they act on.

---

## Affected Files

| File | Change Type | Scope |
|------|-------------|-------|
| `frontend/src/pages/GlobalOverview.jsx` | **Major edit** | Replace `PageHeader` + `AIInsightPanel` section in ready/error/loading states with unified hero |
| `frontend/src/index.css` | **Major edit** | New `.overview-landing-*` styles; deprecate some `.page-header` / `.ai-insight-panel` usage on this page |
| `frontend/tests/globalOverview.test.jsx` | **Minor edit** | Update selectors to match new DOM structure |
| `docs/DECISIONS.md` | **Append** | ADR for the structural redesign |

**NOT touched:** Map panel, drilldown panel, queue section, `AIInsightPanel.jsx` component (still used on other pages), `PageHeader.jsx` component (still used on other pages), model functions, backend.

---

## Design Specification

### Current DOM structure (above the fold)

```
<div class="page page--overview container">
  <PageHeader eyebrow="GLOBAL OVERVIEW" title="Global Overview" meta="..." description="..." actions={buttons} />
  <section class="section-gap">
    <AIInsightPanel eyebrow="GLOBAL SYNTHESIS" title="Global economic outlook" ...>
      <p class="text-body">  ← 4+ lines of AI synthesis prose
      <div class="overview-signal-list">  ← risk flags (2 items)
      <div class="overview-hero-grid">  ← 3 stat cards (data year, anomalies, stress point)
    </AIInsightPanel>
  </section>
  ... map, drilldown, queue ...
</div>
```

### Target DOM structure

```
<div class="page page--overview container">
  <section class="overview-landing">
    <div class="overview-landing__inner">

      <!-- LEFT COLUMN (~60%): Identity + Narrative -->
      <div class="overview-landing__narrative">
        <div class="overview-landing__eyebrow">
          <span class="material-symbols-outlined ...">insights</span>
          <span class="overview-landing__eyebrow-text">GLOBAL OVERVIEW</span>
          <StatusPill tone={panelOutlookTone}>{panelStatusLabel}</StatusPill>
        </div>

        <h1 class="overview-landing__title">Global Overview</h1>

        <p class="overview-landing__synthesis text-body">
          {panelOverview?.summary || headerNarrative}   ← max ~2-3 lines; same data, tighter container
        </p>

        <div class="overview-landing__meta">
          <span class="text-label">Source window // {sourceWindowLabel}</span>
          <span class="overview-landing__meta-sep" aria-hidden="true">·</span>
          <span class="text-label">Latest data // {latestDataYearLabel}</span>
          <span class="overview-landing__meta-sep" aria-hidden="true">·</span>
          <span class="text-label">Refresh // {pipelineRefreshLabel}</span>
        </div>

        <div class="overview-landing__actions">
          <Link class="btn-primary" to="/trigger">Open pipeline</Link>
          <button class="btn-ghost" ...>Review country queue</button>
        </div>
      </div>

      <!-- RIGHT COLUMN (~40%): Signal density — 2×2 metric grid -->
      <div class="overview-landing__signals">
        <article class="overview-landing__metric overview-landing__metric--{tone}">
          <span class="text-label">Tracked markets</span>
          <span class="overview-landing__metric-value">{liveCoverageLabel}</span>
          <p class="overview-landing__metric-desc text-body text-secondary">
            Live briefings across the monitored panel.
          </p>
        </article>
        <article class="overview-landing__metric overview-landing__metric--success">
          <span class="text-label">Latest data year</span>
          <span class="overview-landing__metric-value">{latestDataYearLabel}</span>
          ...
        </article>
        <article class="overview-landing__metric overview-landing__metric--{anomalyTone}">
          <span class="text-label">Anomalies detected</span>
          <span class="overview-landing__metric-value">{anomalyCount}</span>
          ...
        </article>
        <article class="overview-landing__metric overview-landing__metric--{stressTone}">
          <span class="text-label">Primary stress point</span>
          <span class="overview-landing__metric-value">{leadPressureValue}</span>
          ...
        </article>
      </div>

    </div>
  </section>

  <!-- RISK FLAG STRIP — sits between hero and map/drilldown -->
  {panelOverview?.risk_flags?.length > 0 && (
    <section class="overview-risk-strip section-gap">
      {panelOverview.risk_flags.slice(0, 3).map((flag, i) => (
        <article class="overview-risk-strip__flag">
          <span class="text-label">Risk flag {i + 1}</span>
          <p class="text-body text-secondary">{flag}</p>
        </article>
      ))}
    </section>
  )}

  ... anomaly banner, pipeline status notice, map, drilldown, queue (UNCHANGED) ...
</div>
```

---

## CSS Specification

### New classes

```css
/* --------------------------------------------------------------------------
   Overview Landing — Unified Hero
   -------------------------------------------------------------------------- */

/* Outer container: gradient background, full-width card treatment */
.overview-landing {
  background: linear-gradient(180deg, var(--surface-card) 0%, var(--surface-canvas) 100%);
  border-left: var(--border-accent);           /* 4px left accent = AI content marker */
  border-radius: var(--radius);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
}

/* Inner grid: 60/40 split, collapses to single column on mobile */
.overview-landing__inner {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr);
  gap: var(--space-6);
  align-items: start;
}

/* --- Left Column: Narrative --- */
.overview-landing__narrative {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Eyebrow row: icon + label + inline pill */
.overview-landing__eyebrow {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.overview-landing__eyebrow-text {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--color-accent);
}

/* Title: same as text-display but tighter bottom margin via gap */
.overview-landing__title {
  font-family: var(--font-display);
  font-size: 2.75rem;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

/* Synthesis: constrained width for readability */
.overview-landing__synthesis {
  max-width: 58ch;
  color: var(--color-text-primary);
  font-size: 0.9375rem;
  line-height: 1.75;
}

/* Meta strip: monospace inline labels separated by dots */
.overview-landing__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.overview-landing__meta-sep {
  color: var(--color-text-secondary);
}

/* Actions: button row tucked under meta */
.overview-landing__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

/* --- Right Column: 2×2 Metric Grid --- */
.overview-landing__signals {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  align-self: stretch;
}

/* Individual metric card */
.overview-landing__metric {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  border: var(--border-structural);
  border-radius: var(--radius);
  background: var(--surface-nested);
  border-top: 3px solid var(--color-border);    /* default neutral top-border */
}

/* Semantic top-border overrides */
.overview-landing__metric--success { border-top-color: var(--color-success); }
.overview-landing__metric--warning { border-top-color: var(--color-warning); }
.overview-landing__metric--critical { border-top-color: var(--color-critical); }

/* Metric value: Commit Mono, large */
.overview-landing__metric-value {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--color-text-primary);
}

/* Metric description: one line, truncated */
.overview-landing__metric-desc {
  font-size: 0.8125rem;
  line-height: 1.5;
}

/* --- Risk Flag Strip --- */
.overview-risk-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-3);
}

.overview-risk-strip__flag {
  padding: var(--space-4);
  border: var(--border-structural);
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius);
  background: var(--surface-card);
}

/* --- Responsive: single column below 768px --- */
@media (max-width: 768px) {
  .overview-landing__inner {
    grid-template-columns: 1fr;
  }

  .overview-landing__title {
    font-size: 2rem;
  }

  .overview-landing__metric-value {
    font-size: 1.5rem;
  }

  .overview-risk-strip {
    grid-template-columns: 1fr;
  }
}
```

### Classes to PRESERVE (used elsewhere or below the fold)

| Class | Keep? | Reason |
|-------|-------|--------|
| `.page-header`, `.page-header__*` | **Yes** | Used on CountryIntelligence, HowItWorks, PipelineTrigger |
| `.ai-insight`, `.ai-insight-panel`, `.ai-insight-panel__*` | **Yes** | Component still used on other pages; no longer used on GlobalOverview ready state |
| `.overview-hero`, `.overview-hero__*` | **Remove** | These are the current hero styles that the landing replaces; verify no other page imports them |
| `.overview-hero-grid`, `.overview-hero-stat`, `.overview-hero-stat__*` | **Remove** | Replaced by `.overview-landing__signals` / `.overview-landing__metric` |
| `.overview-hero-summary` | **Remove** | Replaced by `.overview-landing__synthesis` |
| `.overview-hero-footer` | **Remove** | Replaced by `.overview-landing__meta` |
| `.overview-signal-card--hero` | **Remove** | Risk flags moved to `.overview-risk-strip__flag` |

### Classes to ADD

All `.overview-landing__*` and `.overview-risk-strip*` classes listed above.

---

## Implementation Sequence

### Step 1: CSS — Add new styles, mark old ones for removal
1. Add all `.overview-landing__*` and `.overview-risk-strip*` styles to `frontend/src/index.css`
2. Do NOT yet remove old `.overview-hero*` styles (avoid breaking until JSX is updated)

### Step 2: JSX — Replace the above-the-fold section in the ready state
1. In `GlobalOverview()` return statement (`viewState === "ready"`):
   - Remove `<PageHeader>` usage
   - Remove `<AIInsightPanel>` section (including risk flags and hero-grid inside it)
   - Insert new `<section className="overview-landing">` structure per spec above
   - Insert `<section className="overview-risk-strip">` after landing, before anomaly banner
2. Move the `sharedActions` content inline to `.overview-landing__actions` (avoids the detached actions slot)
3. Keep `headerNarrative` as fallback text when `panelOverview?.summary` is null

### Step 3: JSX — Update loading and error states
1. `OverviewLoadingShell`: Replace `<PageHeader>` + skeleton `<AIInsightPanel>` with a skeleton version of the new landing layout (same grid, skeleton blocks in place of text/metrics)
2. Error state: Replace `<PageHeader>` with a minimal version of the landing showing error message

### Step 4: Tests — Update selectors
Assertions that need changing:

| Current assertion | Change |
|-------------------|--------|
| `screen.findByRole("heading", { name: "Country drilldown" })` | **Keep** — below the fold, unchanged |
| `screen.getByText("Cross-market inflation...")` | **Keep** — text still rendered, just in `.overview-landing__synthesis` |
| `screen.getAllByText(/Source window \/\//` | **Update** — the meta strip format changes from `Source window // 2010-2024` to `Source window // 2010-2024` (same text, different container; selector should still match) |
| `screen.getByRole("link", { name: "Open pipeline" })` | **Keep** — CTA text unchanged |
| `screen.getByRole("button", { name: "Review country queue" })` | **Keep** — button text unchanged |
| `screen.getByRole("button", { name: "Open market briefings" })` | **Keep** — below the fold, unchanged |
| `screen.getByText("0 statistical anomalies")` | **Verify** — this comes from `panelSignals` in the queue section, not the hero. Should be unaffected |
| `screen.getByText("Primary stress point")` | **Keep** — label text unchanged, just in new `.overview-landing__metric` |
| `screen.getByText("BR -1.30%")` | **Keep** — value text unchanged, just in new `.overview-landing__metric-value` |
| `screen.getByText("No market focused")` | **Keep** — below the fold, drilldown panel |
| Class-based assertions (`.text-secondary`, `.text-critical`) | **Review** — the `0 statistical anomalies` class assertion may target a different element if we restructured the hero stat rendering |

### Step 5: CSS cleanup — Remove deprecated hero styles
1. Remove `.overview-hero`, `.overview-hero__*` block
2. Remove `.overview-hero-grid`, `.overview-hero-stat`, `.overview-hero-stat__*`
3. Remove `.overview-hero-summary`, `.overview-hero-footer`
4. Remove `.overview-signal-card--hero` variant

### Step 6: ADR — Document the decision
Append to `docs/DECISIONS.md`.

---

## Data Flow — No Changes

All data variables used in the new hero already exist in the component:

| Variable | Source | Used in |
|----------|--------|---------|
| `panelOverview?.summary` | `/overview` API | `.overview-landing__synthesis` |
| `panelOverview?.outlook` | `/overview` API | Status pill |
| `panelOverview?.risk_flags` | `/overview` API | `.overview-risk-strip` |
| `panelStatusLabel` | Derived from `panelOverview.outlook` | Pill text |
| `panelOutlookTone` | Derived | Pill tone |
| `sourceWindowLabel` | `formatSourceDateRange(panelOverview?.source_date_range)` | Meta strip |
| `latestDataYearLabel` | `getLatestDataYear(overview.indicators)` | Metric card |
| `anomalyCount` | `deriveOverviewMetrics(overview)` | Metric card |
| `leadPressureValue` | Derived from `pressureWatchlist` | Metric card |
| `liveCoverageLabel` | `materialisedCountries/monitoredCountries` | Metric card |
| `pipelineRefreshLabel` | `formatTimestamp(latestRefresh)` | Meta strip |
| `pipelineStatus` | `overview.status?.status` | CTA label |
| `headerNarrative` | Derived from view state | Fallback text |

No new model functions needed. No new API calls. No backend changes.

---

## Risks and Edge Cases

1. **Empty state (no `panelOverview`):** When the pipeline hasn't run, `panelOverview` is null. The synthesis falls back to `headerNarrative`. Metric values show "Pending". This already works and should continue to work.

2. **Long AI summary:** The current synthesis can be 4+ lines. The new `.overview-landing__synthesis` constrains width to `58ch` but doesn't truncate. If the model produces a very long paragraph, it'll push the meta strip down. **Mitigation:** The paragraph already exists in the current layout; this is an LLM prompt concern, not a UI concern. Could add a CSS `line-clamp: 3` as a safety valve if needed.

3. **Accessible heading structure:** The current page has `<h1>` in `PageHeader` and `<h2>` in `AIInsightPanel`. The new structure uses a single `<h1>` for "Global Overview" in the landing. Below-the-fold `<h2>` elements for "Tracked markets", "Country drilldown", etc. remain unchanged. This improves heading hierarchy.

4. **PageHeader removal breaks other pages?** No — `PageHeader` import is per-page. CountryIntelligence, HowItWorks, and PipelineTrigger each import it independently.

5. **AIInsightPanel still renders risk flags inline?** In the current structure, risk flags are children of `AIInsightPanel`. In the new structure, they're a separate `overview-risk-strip` section. The `AIInsightPanel` component itself is NOT modified — it's just no longer used in the GlobalOverview ready state.

6. **Loading state skeleton mismatch:** The loading shell currently mimics the PageHeader + AIInsightPanel shape. It must be updated to mimic the new landing shape, or the transition from loading→ready will feel jarring (layout shift).

7. **Responsive behavior:** The 2×2 metric grid on the right column needs to collapse gracefully. On mobile (<768px), the grid goes single-column (narrative stack full-width, then signals stack full-width). Metric cards go from 2×2 to 2×1 on narrow screens. Add a sub-breakpoint at ~480px if needed to go to 1×4.

---

## Validation Criteria

- [ ] Above-the-fold shows: eyebrow + pill, h1, synthesis (≤3 visual lines at 1440px), meta strip, CTAs, and 4 metric cards — all without scrolling
- [ ] Risk flags appear as a horizontal strip between hero and map section
- [ ] No double-header pattern (only one "GLOBAL OVERVIEW" label)
- [ ] Metric values use Commit Mono at 2rem
- [ ] Semantic top-border colors match data state (success/warning/critical)
- [ ] Loading skeleton mimics the new layout shape
- [ ] Error state shows the landing with error message in the synthesis slot
- [ ] All existing test assertions pass (with adjusted selectors where needed)
- [ ] Mobile layout stacks to single column below 768px
- [ ] `PageHeader` and `AIInsightPanel` components remain untouched (used on other pages)
- [ ] No console errors, no accessibility regressions (heading hierarchy, aria-live regions)

---

## Workflow Recommendation

**Dual-lane: Yes.** This is a significant structural change to the primary landing surface. The implementation lane handles JSX + CSS; the review lane audits for:
- Design system compliance (accent usage, radius, spacing, font rules)
- Test coverage of the new DOM structure
- Heading hierarchy and accessibility
- Responsive behavior at 768px and 480px breakpoints
- Visual regression against the "numbers first, narrative second" design intent

**ADR: Yes.** This replaces two established patterns (PageHeader + AIInsightPanel) with a custom landing section. The trade-off (custom structure vs. reusable components) warrants documenting.

---

## ADR Draft

### ADR-0XX: Unified Landing Hero for Global Overview

**Context:** The Global Overview page used `PageHeader` + `AIInsightPanel` as its above-the-fold structure. This produced a double-header pattern (two eyebrow+title layers), buried key metrics below prose, and placed CTAs in a detached header actions slot with no spatial relationship to the data.

**Decision:** Replace both components on this page with a single `.overview-landing` section: left column for identity + narrative + CTAs, right column for a 2×2 metric grid, followed by a separate risk flag strip. `PageHeader` and `AIInsightPanel` are preserved as components for other pages.

**Why:**
1. The landing page is the first impression. Redundant labeling and text-heavy layouts reduce information density at the moment when signal density matters most.
2. A split-column layout (60/40) follows the design-taste-frontend rule against centered hero bias when DESIGN_VARIANCE > 4.
3. Inlining CTAs below the meta strip gives them spatial context — they sit adjacent to the data freshness labels they act on.
4. The 2×2 metric grid with semantic top-border colors provides instant visual hierarchy without adding more text.

**Trade-off:** The Global Overview now has a custom hero instead of reusing shared components. This increases the CSS surface area for this page. Acceptable because the landing page has fundamentally different information density requirements from inner pages.
