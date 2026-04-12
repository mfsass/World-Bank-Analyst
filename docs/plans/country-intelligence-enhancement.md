# Plan: Country Intelligence & Overview Enhancement

## Goal

Transform World Analyst from a single-year snapshot dashboard into a multi-year intelligence terminal where any country is reachable in two interactions and every quantitative surface communicates trajectory.

## Context

- PRD: [docs/prds/country-intelligence-enhancement.md](../prds/country-intelligence-enhancement.md)
- The pipeline already fetches 15 years of data (2010–2024) but `prepare_llm_context()` discards everything except the latest row before storage. The full series exists in-pipeline and is thrown away at the boundary.
- The `/country` landing page is a dead-end that tells users to go back to the overview.
- The map has no hover preview, no click-away reset, and no signal density in the market command list below it.
- Country drill-in still depends on a cold detail fetch even though the monitored set is fixed and known ahead of navigation.
- 3 phases, 9 features. Phase 1 is frontend-only, Phase 2 is backend+API, Phase 3 is frontend-intensive depending on Phase 2.

## Affected Areas

### Phase 1 — Direct Access & Map Polish (frontend only)

| File                                                | Change                                                                                                                         |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `frontend/src/pages/CountryIntelligenceLanding.jsx` | Gut-replace with searchable country directory                                                                                  |
| `frontend/src/pages/GlobalOverview.jsx`             | Add hover preview on markers, click-away reset on Geography/SVG, replace `overview-market-command-list` with dense signal grid |
| `frontend/src/pages/globalOverviewModel.js`         | Add helper for building signal grid data (lead KPI delta per country)                                                          |
| `frontend/src/lib/countryDetailCache.js`            | **New file** — shared in-memory preload queue and session cache for country detail payloads                                    |
| `frontend/src/index.css`                            | New styles for directory cards, hover tooltip, signal grid, updated market command list styles                                 |
| `frontend/src/App.jsx`                              | No route changes needed — `/country` already renders `CountryIntelligenceLanding`                                              |
| `frontend/src/api.js`                               | Add cache-aware country-detail read path or shared fetch helper                                                                |

### Phase 2 — Historical Data Pipeline (backend + API)

| File                             | Change                                                                                        |
| -------------------------------- | --------------------------------------------------------------------------------------------- |
| `api/openapi.yaml`               | Add `time_series` array to `IndicatorInsight`, add `regime_label` to `CountryDetail`          |
| `pipeline/analyser.py`           | New `prepare_time_series()` function                                                          |
| `pipeline/storage.py`            | Persist time series alongside indicator records; persist `regime_label` on country records    |
| `pipeline/ai_client.py`          | Extend `MacroSynthesis` Pydantic schema with `regime_label` field; update Step 2 prompt       |
| `shared/repository.py`           | Add `regime_label` to `COUNTRY_PUBLIC_FIELDS`; add `time_series` to `INDICATOR_PUBLIC_FIELDS` |
| `shared/local_repository.py`     | No structural changes needed — mixed-doc shape handles new fields                             |
| `shared/firestore_repository.py` | No structural changes needed — `merge=True` handles new fields                                |
| `api/handlers/countries.py`      | No changes — handler delegates to repository, which now returns enriched data                 |
| `pipeline/main.py`               | Pass `regime_label` from synthesis result into country record                                 |

### Phase 3 — Country Timeline & Enriched Popover (frontend-intensive)

| File                                          | Change                                                                                         |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `frontend/src/pages/CountryIntelligence.jsx`  | New timeline section with Recharts `LineChart` per indicator; regime label in header           |
| `frontend/src/pages/GlobalOverview.jsx`       | Enriched popover with metric values; regime label in popover                                   |
| `frontend/src/components/CountryTimeline.jsx` | **New file** — extracted Recharts chart component                                              |
| `frontend/src/components/SignalGrid.jsx`      | **New file** — dense market signal grid component (can be extracted during Phase 1 or Phase 3) |
| `frontend/src/index.css`                      | Timeline chart theming, enriched popover metrics layout, regime label pill style               |

### Skills to consult

- `world-analyst-design-system` — Surface hierarchy, accent rules, typography
- `emil-design-eng` — Hover timing, tooltip animation, chart interaction feel
- `design-taste-frontend` — Anti-AI-slop patterns for the directory and signal grid
- `connexion-api-development` — Spec-first schema changes
- `world-bank-api` — Time series data shape
- `llm-prompting-and-evaluation` — Regime label prompt extension

---

## Implementation Steps

### Phase 1 — Direct Access & Map Polish

**Estimated scope:** ~7 files changed, uses existing APIs plus background country-detail reads, 0 backend changes.

#### Step 1.1: Country Directory (Feature 5)

Replace the dead-end `CountryIntelligenceLanding.jsx` with a searchable directory.

1. Fetch `/countries` and `/overview` on mount (existing endpoints).
2. Build country card grid: flag (react-world-flags), name, region, income level, outlook pill (from overview `country_codes` to determine materialised status), link to `/country/:code`.
3. Add search input at top — client-side filter by name or ISO code.
4. Keyboard: `/` to focus search, Enter with one result navigates.
5. Sort: materialised countries first, then alphabetical.
6. Style with design system tokens — `--surface-card`, `--radius`, `--font-mono` for codes.

**Acceptance criteria:** 5.1–5.7 from PRD.

#### Step 1.2: Click-Away Map Reset (Feature 2)

1. Add `onClick` handler to `<Geography>` elements and the SVG background in `GlobalOverview.jsx`.
2. On click of land or ocean (when not clicking a marker): set `selectedMapCountry` to `null`, clear `selectedMarkerRef`.
3. Add `onKeyDown` handler for Escape key on the map container — same reset.
4. Ensure clicking a different marker switches focus directly without visible null flash.

**Key implementation detail:** The `<Geography>` elements already render inside `<Geographies>`. Add an `onClick` prop that calls a `handleMapBackgroundClick` function. For ocean clicks, wrap the `<ComposableMap>` SVG in a click handler that checks if the target is a marker — if not, reset.

**Acceptance criteria:** 2.1–2.4 from PRD.

#### Step 1.3: Map Hover Preview (Feature 1)

1. Add `onMouseEnter`/`onMouseLeave` handlers to each marker `<button>` in `OverviewMapLayer`.
2. Track `hoveredCountry` state (separate from `selectedMapCountry`).
3. Show lightweight tooltip: country name, ISO code, outlook pill.
4. Tooltip uses `--surface-popover` (`#262626`), `--radius` (8px).
5. Position above or below marker using the same edge-clamping as existing popover, but smaller dimensions.
6. 150ms delay via `setTimeout` on mouseenter; clear on mouseleave.
7. Touch devices: use `(pointer: coarse)` media query to skip hover and rely on existing tap behavior.

**Acceptance criteria:** 1.1–1.5 from PRD.

#### Step 1.4: Country Detail Preload & Cache Reuse (Feature 5A)

1. Create a shared country-detail cache module keyed by ISO country code.
2. Start background preloading only after the Overview or Country Directory is interactive. Use `requestIdleCallback` where available, with a safe timeout fallback.
3. Cap preload concurrency at `3` so warming country detail never outruns first-paint work.
4. Prioritize hovered markers, selected countries, and visible directory cards ahead of the rest of the monitored set.
5. On `/country/:id`, read from the shared cache first. If the cached entry is still fresh, render immediately and revalidate in the background only when summary freshness markers changed.
6. Invalidate the cache when pipeline status reports a newer successful run.

**Acceptance criteria:** 5A.1–5A.6 from PRD.

#### Phase 1 Validation

- `cd frontend && npm run lint` — no new warnings.
- `cd frontend && npm run build` — clean production build.
- Manual: navigate to `/country` — see 17-country grid, search works, keyboard works.
- Manual: hover map markers — tooltip appears/disappears correctly.
- Manual: click ocean/land — popover dismisses. Escape key works.
- Manual: open `/country/:id` after browsing Overview or the directory — country detail should feel immediate for warmed entries.
- Manual: throttle the network in browser devtools — initial render should remain responsive and the preload queue should not block first paint.
- Manual: no regressions on existing overview functionality.

---

### Phase 2 — Historical Data Pipeline

**Estimated scope:** ~6 files changed. Requires pipeline re-run to populate data.

#### Step 2.1: OpenAPI Schema Extension (spec-first, before any code)

1. Add `TimeSeriesPoint` schema to `openapi.yaml`:
   ```yaml
   TimeSeriesPoint:
     type: object
     properties:
       year:
         type: integer
       value:
         type: number
       percent_change:
         type: number
       is_anomaly:
         type: boolean
   ```
2. Add `time_series` to `IndicatorInsight`:
   ```yaml
   time_series:
     type: array
     items:
       $ref: "#/components/schemas/TimeSeriesPoint"
     description: Full historical series for this indicator (2010–2024)
   ```
3. Add `regime_label` to `CountryDetail`:
   ```yaml
   regime_label:
     type: string
     enum: [expansion, contraction, recovery, stagnation, overheating]
     description: LLM-derived macroeconomic regime classification
   ```

**Acceptance criteria:** 6.2, 8.3 from PRD.

#### Step 2.2: `prepare_time_series()` in analyser.py

1. New function: takes the full DataFrame (output of `compute_changes`), groups by `(country_code, indicator_code)`, and returns a dict keyed by `"{country_code}:{indicator_code}"` → list of `{year, value, percent_change, is_anomaly}` dicts, sorted by year ascending.
2. Filter out rows where `value` is NaN.
3. Round values consistently: `value` to 4 decimals, `percent_change` to 2 decimals.

**Implementation note:** This function runs alongside `prepare_llm_context()` — both consume the same DataFrame but extract different projections.

**Acceptance criteria:** 6.1 (data shape).

#### Step 2.3: Storage enrichment in storage.py

1. Modify `store_slice()` to accept a new `time_series_by_key` parameter (output of `prepare_time_series()`).
2. When writing indicator records, attach `time_series` array from the lookup.
3. When writing country records, attach `regime_label` from the synthesis result.

**Key constraint:** Existing fields must remain unchanged (AC 6.5). The `time_series` is additive.

**Acceptance criteria:** 6.3, 6.4 (Firestore size < 100KB per doc).

#### Step 2.4: Regime label prompt extension (Feature 8)

1. Extend `MacroSynthesis` Pydantic model in `ai_client.py`:
   ```python
   regime_label: Literal["expansion", "contraction", "recovery", "stagnation", "overheating"] = Field(
       description="Current macroeconomic regime classification"
   )
   ```
2. Add regime classification instruction to `STEP2_SYSTEM` prompt:
   ```
   5. Classify the country's current macroeconomic regime as one of:
      expansion, contraction, recovery, stagnation, or overheating.
      Base this on the GDP growth direction, CPI trend, and employment data.
   ```
3. Update `STEP2_PROMPT_VERSION` to `"step2.v2.0.0"`.
4. Update the development AI adapter (`dev_ai_adapter.py`) to include `regime_label` in mock responses.

**Acceptance criteria:** 8.1, 8.2 from PRD.

#### Step 2.5: Repository public fields update

1. Add `"regime_label"` to `COUNTRY_PUBLIC_FIELDS` tuple in `shared/repository.py`.
2. Add `"time_series"` to `INDICATOR_PUBLIC_FIELDS` tuple in `shared/repository.py`.

**Why this is needed:** The `project_public_record()` function uses these tuples to filter stored records into API responses. Without adding the new fields, they'd be stripped before reaching the handler.

#### Step 2.6: Pipeline main.py orchestration

1. In `run_pipeline()`, after the ANALYSE step, call `prepare_time_series(df)` to build the time series lookup.
2. Pass `time_series_by_key` to `store_slice()`.
3. When building country synthesis records, extract `regime_label` from the synthesis result (already returned by the AI client after Step 2.4).

#### Phase 2 Validation

- `cd pipeline && python -m pytest tests/ -v` — all existing tests pass.
- `cd api && python -m pytest tests/ -v` — all existing tests pass.
- `cd api && ruff check .` — clean.
- `cd pipeline && ruff check .` — clean.
- Manual: run pipeline locally, inspect local repository output — confirm `time_series` arrays present on indicator records.
- Manual: hit `GET /countries/{code}` — confirm `time_series` appears per indicator and `regime_label` on the country.
- Manual: verify existing fields unchanged — backward compatibility.
- Validation check: largest country document's time_series should be ≈ 6 indicators × ~15 years × ~60 bytes = ~5.4KB. Well within 100KB.

---

### Phase 3 — Country Timeline & Enriched Popover

**Estimated scope:** ~4 files changed, 1–2 new component files. Depends on Phase 2 data.

#### Step 3.1: Country Timeline View (Feature 7)

1. Create `frontend/src/components/CountryTimeline.jsx`:
   - Takes `indicators` array (each with `time_series`).
   - Renders one Recharts `<LineChart>` per indicator.
   - Chart styling per PRD §7.2:
     - Line: `#F5F5F5`, 1.5px stroke, no area fill.
     - Background: transparent (inherits dark card).
     - No grid lines. Axis lines `#262626`. Axis labels `#737373` in Commit Mono.
     - Anomaly years: `#EF4444` dots (6px radius) via custom dot renderer.
     - Latest point: `#FF4500` dot (8px radius) with value label.
     - Mean reference: dashed `#737373` line with "MEAN" label via `<ReferenceLine>`.
   - Height: 180px per chart. Width: responsive (100%).
   - Tooltip: year, value, YoY change on Level 3 surface.
   - Guard: if `time_series` is absent or empty, don't render.

2. Integrate into `CountryIntelligence.jsx`:
   - Place timeline section between the KPI row and the indicator detail grid.
   - Section header: "Historical Context" with data window label (e.g., "2010–2024").
   - Only render if at least one indicator has `time_series` data.

**Acceptance criteria:** 7.1–7.10 from PRD.

#### Step 3.2: Enriched Map Popover (Feature 3)

1. In `GlobalOverview.jsx`, expand the existing popover to show GDP growth, CPI, and unemployment values when a briefing is loaded.
2. Use `text-metric` style with directional signal tone (reuse `getSignalTone` from `globalOverviewModel`).
3. Show skeleton placeholders while briefing is loading.
4. Display `regime_label` below the outlook pill when available.
5. Constrain popover max-width to 280px (update `MAP_POPOVER.width` constant and CSS).

**Acceptance criteria:** 3.1–3.4 from PRD.

#### Step 3.3: Dense Market Signal Grid (Feature 4)

1. Replace the `overview-market-command-list` in `GlobalOverview.jsx` with a structured grid.
2. Each cell: ISO code, flag (16px `flag-frame--xs`), outlook pill, lead KPI delta.
3. Still triggers `toggleMapFocus` on click.
4. Active cell distinguished with `#FF4500` left-border treatment (4px, matching AI insight pattern).
5. Grid should not add vertical scroll to the map panel.

**Implementation approach:** Can either inline in GlobalOverview or extract to `SignalGrid.jsx` component. Given complexity, extract.

**Acceptance criteria:** 4.1–4.4 from PRD.

#### Step 3.4: Regime Label Display (Feature 8 frontend)

1. On `CountryIntelligence.jsx` header: display `regime_label` as a secondary `<StatusPill>` next to the outlook pill.
2. Regime label tone mapping:
   - `expansion` → `success`
   - `recovery` → `success`
   - `stagnation` → `warning`
   - `overheating` → `warning`
   - `contraction` → `critical`
3. In map popover: display below outlook when available.
4. Guard: if `regime_label` is absent (old briefings), don't render — no errors.

**Acceptance criteria:** 8.4–8.6 from PRD.

#### Phase 3 Validation

- `cd frontend && npm run lint` — no new warnings.
- `cd frontend && npm run build` — clean production build.
- Manual: country page shows timeline charts with correct styling.
- Manual: hover chart points — tooltip shows year, value, change.
- Manual: anomaly dots appear on correct years.
- Manual: mean reference line renders correctly.
- Manual: map popover shows metrics for materialised countries.
- Manual: regime label appears on country page and in popover.
- Manual: countries without regime label (pre-enhancement) render without errors.
- Manual: signal grid below map is dense, clickable, and shows lead KPI delta.

---

## ADR Decisions Required

### ADR: Time Series Storage Shape — Nested Array vs. Subcollection

**Decision needed:** Store time series as a nested array inside the existing indicator document vs. as a Firestore subcollection.

**Recommendation:** Nested array. Rationale:

- ~15 data points per indicator × ~60 bytes = ~900 bytes per array. Total per country: ~5.4KB across 6 indicators. Well within Firestore's 1MB limit.
- A single `doc.get()` returns everything the frontend needs. No fan-out reads.
- Subcollections add read complexity, billing, and query overhead for a tiny dataset.
- Consistent with ADR-001's key-value access pattern.

**Trade-off:** If the data window expands beyond ~50 years or indicators grow to 20+, nested arrays could approach document limits. At projected scale (15 years × 6 indicators), this is not a concern.

→ Add to `docs/DECISIONS.md` as ADR-009 (or next available number).

### ADR: Regime Label Source — LLM-Derived vs. Rule-Based

**Decision needed:** Derive `regime_label` from the LLM synthesis step vs. compute it from thresholds on GDP/CPI/unemployment.

**Recommendation:** LLM-derived (extend Step 2 prompt). Rationale:

- The LLM already reads all 6 indicators to produce the outlook. Adding one constrained-enum field is marginal cost.
- Rule-based classification requires defining precise multi-indicator thresholds that are domain-contentious (what GDP threshold distinguishes "stagnation" from "contraction"?). The LLM can weigh context.
- Schema-constrained output (ADR-003) ensures the label is always valid.

**Trade-off:** LLM regime classifications may be inconsistent across runs (e.g., "cautious + low growth" could be `stagnation` or `contraction`). Acceptable for a derived label — this is not a quant model.

→ Add to `docs/DECISIONS.md` as ADR-010 (or next available number).

---

## Risk Flags & Blockers

| Risk                                                                                                                    | Severity | Mitigation                                                                                                                              |
| ----------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Phase 2 blocks Phase 3.** Timeline charts need `time_series` data. Signal grid needs indicator data in overview.      | High     | Phase 1 is fully independent. Phase 3 work on the signal grid and regime labels can begin in parallel once Phase 2 schema changes land. |
| **Prompt version bump invalidates AI reuse cache.** Changing `STEP2_PROMPT_VERSION` means all country syntheses re-run. | Low      | Expected behavior — the new field requires fresh synthesis. One pipeline run regenerates all 17 countries.                              |
| **Sparse World Bank data for some country-year combinations.**                                                          | Medium   | Recharts `connectNulls` prop handles gaps. `prepare_time_series()` filters NaN values.                                                  |
| **Mobile hover is awkward.**                                                                                            | Medium   | PRD AC 1.4 specifies two-tap. Simpler: skip hover on `(pointer: coarse)` and use existing first-tap-to-popover.                         |
| **Popover width increase (280px) may overflow on narrow viewports.**                                                    | Low      | Existing edge-clamping logic in `getMapPopoverPosition` handles this. May need responsive adjustment for <768px.                        |
| **Bundle size increase from Recharts LineChart.**                                                                       | Low      | Recharts is already bundled. `LineChart` is an incremental import. Tree-shaking handles unused submodules.                              |

## Workflow Recommendation

This is substantial enough to justify the **dual-lane implementation + review workflow** for Phase 2 and Phase 3. Phase 1 is medium complexity and can use a single-lane flow.

- **Phase 1:** Single implementation lane. Reviewer checks design system compliance and keyboard behavior.
- **Phase 2:** Dual-lane. Implementation lane modifies spec → analyser → storage → repository. Review lane audits: spec drift (does the handler return what the spec declares?), backward compatibility (do existing responses still validate?), and Firestore document size.
- **Phase 3:** Dual-lane. Implementation lane builds chart components. Review lane runs the design review workflow (`.agents/workflows/frontend-design-review.md`) for appearance, taste, and motion.

## Open Questions

1. **Should the signal grid (Feature 4) show data from the `/overview` response or require per-country briefing hydration?** The overview response has `country_codes` but no per-country KPIs. The signal grid needs a lead KPI delta per country, which means either (a) the overview endpoint is extended, or (b) the grid fetches briefings lazily. **Recommendation:** Use the existing Phase 2 indicators data (`/indicators` endpoint) which already returns per-country indicator values on page load in the overview's Phase 2 fetch. No new endpoint needed.

2. **Should `prepare_time_series()` include the first year (no `percent_change` available)?** The first observation year has `value` but no prior-year change. **Recommendation:** Include it with `percent_change: null` and `is_anomaly: false`. The chart plots the value; the missing change is expected for year-1.

3. **Should the dev AI adapter produce deterministic `regime_label` values?** **Recommendation:** Yes — hardcode a mapping based on country code for test stability (e.g., TR → `overheating`, US → `expansion`).
