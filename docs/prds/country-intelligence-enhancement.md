# PRD: Country Intelligence & Overview Enhancement

> **Product goal:** Transform World Analyst from a static snapshot dashboard into a premium economic intelligence terminal where finance professionals can reach any country in two interactions or fewer and immediately see direction-of-travel across a multi-year window — not just a single frozen frame.

---

## 1. Context & Motivation

World Analyst tracks 17 countries across 6 macro indicators. The pipeline already fetches 15 years of World Bank data (2010–2024) and computes year-over-year changes, z-score anomaly flags, and a two-step LLM narrative per country. The frontend renders a global overview with an interactive choropleth map and per-country intelligence pages.

Despite solid data infrastructure, the product _feels_ like a data dashboard rather than an intelligence terminal. A finance professional using Bloomberg, Macrobond, or CEIC would identify four friction points within the first 30 seconds:

1. **The map is observation-only.** Markers toggle a popover with country name and outlook, but there is no hover preview, no visible urgency signal per marker, and no way to dismiss a selection by clicking empty canvas. The space below the map is occupied by a text-button command list that duplicates marker function without adding signal density.
2. **Country access is gated.** The Country Intelligence landing page (`/country`) instructs users to start from the global overview. There is no searchable country list, no jump-to-market shortcut, and no A–Z directory. A user who knows they want Turkey's briefing must navigate home first.
3. **Single-year tunnel vision.** Every data surface shows `latest_value` and one YoY `percent_change`. A professional looking at Turkey's 67% CPI cannot tell whether inflation is accelerating, plateauing, or decelerating from a prior shock — context that requires at minimum the trailing 5–10 year curve.
4. **Country drill-in still feels colder than it should.** The Overview and `/country` directory teach the user which market to open next, but opening `/country/:id` still depends on a fresh detail fetch even though the monitored set is fixed and known in advance. The delay is short, but it is visible enough to weaken the terminal feel.

This PRD scopes the enhancement track that fixes these four problems.

---

## 2. Target Users

| Persona                              | Profile                                                                            | Key need                                                                                                                    |
| ------------------------------------ | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Macro analyst**                    | Sovereign risk, EM fixed income, or country-allocation desk. Uses Bloomberg daily. | Direction of travel across a multi-year window. Wants to see whether a 5% GDP growth is accelerating or reverting to trend. |
| **Development finance professional** | World Bank, IFC, EBRD, bilateral donors. Reviews country exposure quarterly.       | Rapid cross-country comparison. Needs to reach a country directly, not navigate a funnel.                                   |
| **Portfolio manager**                | Allocating across EM/FM. Reads macro notes from sell-side.                         | The "so what" — regime context (expansion, contraction, recovery, overheating) and anomaly severity, not just raw numbers.  |

All three personas share a common trait: they treat time series as the default unit of analysis. Showing them a single data point without historical context is like showing a stock price with no chart.

---

## 3. Business Value

- **Perception shift:** The product moves from "student dashboard" to "credible intelligence terminal" — critical for an ML6 engineering demonstration where evaluators are likely experienced in data products.
- **Density gain:** Current dead space below the map and on the country page becomes high-signal territory (sparklines, regime labels, historical context), increasing the information-to-scroll ratio.
- **Completeness story:** The pipeline already fetches 15 years of data (`LIVE_DATE_RANGE = "2010:2024"` in `fetcher.py`). The enhancement surfaces what the system already knows rather than building new data pipelines.
- **Perceived speed:** Warming likely country detail payloads before navigation removes a visible route-level pause and makes the product feel closer to a terminal than a dashboard.

---

## 4. Scope

### 4.1 In Scope

**Track A — Map & Overview Interaction**

- Hover preview on map markers (country name, outlook pill, lead KPI on hover — before click)
- Click-away reset: clicking empty map canvas dismisses the active popover
- Enriched map popover: add 2–3 sparkline-scale trend indicators to the existing popover
- Replace the flat market-command text-button list below the map with a denser signal grid (country code, outlook pill, lead KPI delta) that still drives map focus

**Track B — Direct Country Access**

- Replace the CountryIntelligenceLanding dead-end with a searchable, browsable country directory
- Support keyboard-first search (`/` to focus, type-ahead filter, Enter to navigate)
- Every country card in the directory shows: flag, name, region, outlook pill, lead KPI, and a direct link to its intelligence page
- Preserve `/country/:id` deep links unchanged

**Track C — Multi-Year Country Timeline**

- New API endpoint or extended response: expose the full historical time series per country (all years in the 2010–2024 window, per indicator)
- Country Intelligence page: add a timeline section with one Recharts line chart per indicator showing the trailing series
- Per-chart: highlight the latest value, annotate anomaly years, show the long-run mean as a reference line
- Timeline section header: data window label and a regime summary line (see §6 recommendation)
- Current KPI cards remain — the timeline is additive, not a replacement

**Track D — Frontend Snappiness via Preloading & Cache Reuse**

- Warm country detail payloads in the background for the fixed monitored set once the initial view is interactive
- Prioritize hovered, selected, and above-the-fold countries ahead of the rest of the preload queue
- Reuse one shared frontend cache across Overview, the `/country` directory, and `/country/:id` route transitions
- Revalidate on freshness change instead of forcing a blocking fetch on every country-page entry

### 4.2 Non-Goals

| Item                                                  | Why excluded                                                                                                         |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Multi-country comparison view                         | Useful but separate feature; requires a different layout and selection model.                                        |
| Real-time or sub-annual data                          | World Bank data is annual. Adding quarterly sources (IMF WEO, OECD) is a pipeline scope expansion.                   |
| Custom date-range picker                              | The window is fixed at 2010–2024. Letting users narrow it adds UI complexity without analytical value at this scale. |
| Country search in the AppShell / global nav           | A nav-level search is a larger UX commitment. The directory page serves the same intent with clearer scope.          |
| BigQuery migration                                    | The historical series fits comfortably in Firestore documents (see §8 trade-off).                                    |
| New batch endpoint for country detail                 | The monitored set is small enough to keep this phase inside the existing `/countries/{code}` contract.               |
| Persistent offline browser cache                      | This phase optimizes in-session snappiness, not offline behavior or cross-session staleness management.              |
| Additional countries beyond the 17-country core panel | Scope guardrail from AGENTS.md.                                                                                      |
| Additional indicators beyond the current 6            | Same guardrail.                                                                                                      |

---

## 5. UX Principles

These extend the design system in `.github/skills/world-analyst-design-system/SKILL.md`:

1. **Time is the x-axis.** Every quantitative surface should communicate trajectory, not just level. If a number is shown without its recent history, it should at least carry a directional annotation (▲/▼ and magnitude).
2. **Two interactions to any country.** From any page: (a) click a map marker → popover → "Open intelligence," or (b) navigate to `/country` → type-ahead → Enter. No more than two deliberate actions.
3. **Hover before commit.** Map markers preview on hover (tooltip-weight, not modal-weight). Click commits to the full popover with navigation. This matches the Bloomberg terminal pattern where hover shows the summary and click opens the full view.
4. **Density over whitespace.** Dead space is a design failure in a terminal product. Below-map area should carry analytical signal. The country page should fill vertical space with the timeline before the user scrolls past the fold.
5. **Monospace for moving numbers.** All time-series values, axis labels, and sparkline annotations use Commit Mono per the design system. The font must not reflow when values change.
6. **Warm the next likely move.** Because the monitored set is fixed at 17 countries, the frontend should treat country detail as a warmable working set. After first paint, the next likely country should already be on hand.

---

## 6. Recommendation: Timeline, Regime View, and Direct Access

The user brief asks for a recommendation on three capabilities. Here is the position, grounded in what finance professionals actually use:

### 6.1 Multi-Year Country Timeline — **Strong yes. Ship it.**

**Why:** The pipeline already fetches 2010–2024 data via `LIVE_DATE_RANGE = "2010:2024"` in `fetcher.py`. The analyser computes full YoY changes across this window. But `prepare_llm_context()` discards everything except the latest year before handing data to storage. The 15-year history exists in-pipeline and is thrown away at the boundary.

Surfacing this data requires:

- Persisting the full series to Firestore (each country document grows by ~90 nested data points — well within Firestore's 1MB document limit)
- A new or extended API response shape that includes `time_series: [{year, value, percent_change, is_anomaly}]` per indicator
- A Recharts line chart per indicator on the country page

This is the single highest-impact change in the PRD. A finance professional seeing a 15-year GDP growth curve with anomaly annotations will immediately read the product as credible. A single-year snapshot will always read as a student project, regardless of how polished the UI is.

**Stock-terminal feel:** Use a dark background chart with a thin `#F5F5F5` line, `#FF4500` dots for anomaly years, a dashed `#737373` line for the series mean, and Commit Mono axis labels. No grid lines. No fill. This is the Recharts equivalent of a Bloomberg price chart, not a consumer analytics dashboard.

### 6.2 Market Regime View — **Yes, but lightweight. Label, not a separate page.**

A full "regime classification" model (expansion / contraction / recovery / overheating) requires defining thresholds across multiple indicators simultaneously — e.g., positive GDP growth + rising CPI + falling unemployment = expansion. This is analytically valuable but risks over-engineering for the current scope.

**Recommendation:** Derive a single regime label per country from the existing LLM synthesis step. The Step 2 macro synthesis prompt already produces an `outlook` (bullish / cautious / bearish) and `risk_flags`. Extend the prompt to also emit a `regime_label` from a constrained enum: `expansion`, `contraction`, `recovery`, `stagnation`, `overheating`. Display this as a secondary label on the country page header and in the map popover. The LLM is already reading all six indicators — asking it to also classify the regime adds one field to the structured output, not a new analytical pipeline.

Do not build a separate "regime view" page. The regime label is a property of the country, displayed wherever the country appears.

### 6.3 Direct Country Access Pattern — **Strong yes. Kill the landing dead-end.**

The current `CountryIntelligenceLanding` page tells users to go back to the global overview. This is hostile UX for a professional tool. Replace it with a full country directory: searchable, keyboard-navigable, showing all 17 countries with their current status. This is low-risk, low-effort, and eliminates a genuine usability dead-end.

---

## 7. Core Features & Acceptance Criteria

### Feature 1: Map Hover Preview

**Description:** Map markers show a lightweight tooltip on hover, before the user commits to a click.

| #   | Acceptance Criterion                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1 | Hovering a map marker for ≥150ms shows a tooltip-weight preview: country name, ISO code, and outlook pill.                            |
| 1.2 | The tooltip uses Level 3 surface (`#262626`) with 8px radius per the design system.                                                   |
| 1.3 | Moving the cursor away from the marker dismisses the tooltip within one animation frame.                                              |
| 1.4 | On touch devices, the first tap shows the preview; a second tap opens the full popover.                                               |
| 1.5 | The tooltip never overlaps the marker dot itself — it opens above or below with the same edge-clamping logic as the existing popover. |

### Feature 2: Click-Away Map Reset

**Description:** Clicking empty map canvas (ocean or unmarked land) dismisses the active popover and resets the focused market state.

| #   | Acceptance Criterion                                                                                                         |
| --- | ---------------------------------------------------------------------------------------------------------------------------- |
| 2.1 | Clicking any Geography path (land) or the SVG background (ocean) when a popover is open sets `selectedMapCountry` to `null`. |
| 2.2 | Clicking a different marker switches focus directly — no intermediate null state visible to the user.                        |
| 2.3 | Keyboard: pressing Escape while a popover is open resets focus.                                                              |
| 2.4 | The Country Drilldown sidebar panel returns to its empty/prompt state after reset.                                           |

### Feature 3: Enriched Map Popover

**Description:** The existing map popover includes 2–3 sparkline-scale KPI signals alongside the country name and "Open intelligence" link.

| #   | Acceptance Criterion                                                                                                                                        |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3.1 | If the country has a materialised briefing, the popover shows GDP growth, CPI, and unemployment values in `text-metric` style with directional signal tone. |
| 3.2 | If the briefing is loading, skeleton placeholders appear in the metric positions.                                                                           |
| 3.3 | Popover width increases to accommodate metrics but does not exceed 280px.                                                                                   |
| 3.4 | The regime label (if available per §6.2) appears below the outlook pill.                                                                                    |

### Feature 4: Dense Market Signal Grid

**Description:** Replace the flat market-command text-button list below the map with a structured grid that carries analytical signal.

| #   | Acceptance Criterion                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------ |
| 4.1 | Each cell shows: ISO code, flag (16px frame), outlook pill, and lead KPI delta.                                                |
| 4.2 | The grid replaces the existing `overview-market-command-list` without adding vertical scroll to the map panel.                 |
| 4.3 | Clicking a cell still triggers `toggleMapFocus`.                                                                               |
| 4.4 | Active/focused cell is visually distinguished with the `#FF4500` left border treatment (4px, matching the AI insight pattern). |

### Feature 5: Country Directory (Replace Landing)

**Description:** The `/country` route renders a full browsable, searchable directory of all monitored countries instead of the current instructional dead-end.

| #   | Acceptance Criterion                                                                                                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5.1 | The directory lists all 17 monitored countries in a responsive card grid.                                                                                         |
| 5.2 | Each card shows: flag, country name, region, income level, outlook pill (or "Pending" if no briefing), and a link to `/country/:id`.                              |
| 5.3 | A search input at the top filters countries by name or ISO code. Filtering is instant (client-side, no API call).                                                 |
| 5.4 | Pressing `/` anywhere on the page focuses the search input (unless already in an input).                                                                          |
| 5.5 | With one result remaining, pressing Enter navigates to that country's intelligence page.                                                                          |
| 5.6 | The directory fetches the country list and briefing status on mount via existing `/countries` and optionally `/overview` endpoints. No new API endpoint required. |
| 5.7 | Countries with materialised briefings sort above pending ones. Within each group, sort alphabetically.                                                            |

### Feature 5A: Country Detail Preload & Session Cache

**Description:** The frontend opportunistically warms and reuses country detail responses so country drill-in feels immediate on known high-intent paths.

| #    | Acceptance Criterion                                                                                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5A.1 | After the Overview or Country Directory becomes interactive, the frontend starts background preloading of country detail payloads with a bounded concurrency cap of `3`.         |
| 5A.2 | Hovered or selected map countries, and visible or focused directory cards, move to the front of the preload queue.                                                               |
| 5A.3 | Overview drill-in, `/country`, and `/country/:id` reuse one shared session-scoped cache keyed by `country_code`.                                                                 |
| 5A.4 | When a cached entry is present and still fresh, navigating to `/country/:id` renders from cache immediately and only revalidates in the background if freshness markers changed. |
| 5A.5 | Cache invalidation is triggered by a newer successful pipeline run or by changed country freshness markers in the summary payloads.                                              |
| 5A.6 | This feature uses the existing `/countries/{country_code}` response shape. It does not add a batch detail endpoint or persistent browser storage in this phase.                  |

### Feature 6: Historical Time Series API

**Description:** Expose the full 2010–2024 time series per indicator in the country detail response.

| #   | Acceptance Criterion                                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 6.1 | The `/countries/{country_code}` response includes a `time_series` array per indicator object, containing `{year, value, percent_change, is_anomaly}` for every available year. |
| 6.2 | The openapi.yaml schema is updated **before** the handler is modified (SDD).                                                                                                   |
| 6.3 | The pipeline's storage step persists the full analysed DataFrame rows for each country-indicator pair, not just the latest row.                                                |
| 6.4 | Firestore document size for the largest country (all 6 indicators × ~15 years) does not exceed 100KB.                                                                          |
| 6.5 | Existing fields (`latest_value`, `percent_change`, `data_year`, `ai_analysis`) remain unchanged for backward compatibility.                                                    |
| 6.6 | The existing `/indicators` and `/overview` endpoints are not affected.                                                                                                         |

### Feature 7: Country Timeline View

**Description:** The Country Intelligence page includes a new "Historical Context" section with one Recharts line chart per indicator.

| #    | Acceptance Criterion                                                                                                            |
| ---- | ------------------------------------------------------------------------------------------------------------------------------- |
| 7.1  | Each chart renders the full available time series as a single line on a dark canvas.                                            |
| 7.2  | Chart styling: `#F5F5F5` line (1.5px), no area fill, no grid lines, `#262626` axis lines, Commit Mono axis labels in `#737373`. |
| 7.3  | Anomaly years are marked with `#EF4444` dots (6px radius).                                                                      |
| 7.4  | A dashed reference line at the series mean value uses `#737373` with label "MEAN".                                              |
| 7.5  | The latest data point is highlighted with a `#FF4500` dot (8px radius) with the value label.                                    |
| 7.6  | Each chart shows the indicator name as a `text-label` header, and the data window (e.g., "2010–2024") as secondary text.        |
| 7.7  | Charts are responsive and fill available width. Height is fixed at 180px per chart.                                             |
| 7.8  | The timeline section appears between the KPI row and the existing indicator detail grid.                                        |
| 7.9  | If `time_series` data is absent (backward compat), the section does not render.                                                 |
| 7.10 | Hovering a chart point shows a Recharts tooltip with year, value, and YoY change in a Level 3 surface.                          |

### Feature 8: Regime Label (LLM-Derived)

**Description:** The pipeline emits a regime classification per country alongside the existing outlook.

| #   | Acceptance Criterion                                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 8.1 | The Step 2 macro synthesis prompt includes a `regime_label` field constrained to: `expansion`, `contraction`, `recovery`, `stagnation`, `overheating`. |
| 8.2 | The Pydantic output schema for Step 2 is extended with `regime_label: Literal[...]`.                                                                   |
| 8.3 | The `CountryDetail` response in openapi.yaml includes `regime_label` as an optional string field.                                                      |
| 8.4 | The country page header displays the regime label as a secondary `StatusPill` next to the outlook pill.                                                |
| 8.5 | The map popover displays the regime label when available.                                                                                              |
| 8.6 | Existing briefings without a regime label (generated before this change) display gracefully — no missing-field errors.                                 |

---

## 8. Dependencies & Architecture Notes

### 8.1 Pipeline → Storage Boundary Change

The biggest backend change is in `prepare_llm_context()` and the storage step. Currently, `prepare_llm_context()` takes the latest row per country-indicator pair from the full DataFrame. The full series must now be persisted alongside the latest-row summary.

**Approach:** Add a `prepare_time_series()` function in `analyser.py` that extracts `[{year, value, percent_change, is_anomaly}]` per country-indicator from the full DataFrame. The storage step writes this as a nested array inside the existing Firestore document.

### 8.2 Firestore Document Size

Worst case: 17 countries × 6 indicators × 15 years × ~60 bytes per data point = ~92KB total across all documents, or ~5.4KB per country document for the time series addition. Firestore's 1MB document limit is not a concern. **No migration to BigQuery is needed.** This stays within ADR-001's stated boundary.

### 8.3 API Contract (Spec-First)

All schema changes must be committed to `openapi.yaml` before handler code is modified, per Connexion SDD rules:

- `CountryDetail.indicators[].time_series` — new array field
- `CountryDetail.regime_label` — new optional string field

### 8.4 Frontend Dependencies

- **Recharts** — already in the project's tech stack (GEMINI.md). No new library.
- **react-simple-maps** — already used. Hover interaction uses existing `foreignObject` marker pattern.
- **No new CSS framework** — all chart theming via inline Recharts props and CSS custom properties.

### 8.5 Frontend Cache Model

Use a shared session-scoped country detail cache in the frontend, not persistent browser storage. The monitored set is fixed at 17 countries, and ADR-063 already keeps full time series inline in the existing country detail response. Even if each warmed country detail response approaches ~150KB, the worst-case in-session working set is still roughly `17 × 150KB ≈ 2.55MB`, which is acceptable for the desktop-first demo scope.

The preload queue should start only after the initial page is interactive, run with a small concurrency cap, and prioritize explicit user intent: hovered markers, selected markets, and visible directory cards. Freshness should be tied to existing summary payload markers or the latest successful pipeline run rather than a blind time-based cache TTL.

---

## 9. Risks

| Risk                                                                            | Likelihood | Impact | Mitigation                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------- | ---------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| World Bank API returns sparse data for some country-indicator-year combinations | High       | Low    | The charts handle gaps: Recharts `connectNulls` prop draws through missing years. Label sparse series as "partial coverage" in the UI.                                                                                                   |
| Firestore read latency increases with larger documents                          | Low        | Low    | Documents grow by ~5KB. Firestore is optimised for documents up to 1MB. No measurable impact expected.                                                                                                                                   |
| Hover interaction on mobile is awkward                                          | Medium     | Medium | Feature 1 AC 1.4 specifies a two-tap pattern. Alternatively, skip hover on `(pointer: coarse)` devices and go straight to popover on first tap (current behaviour).                                                                      |
| LLM regime classification is inconsistent                                       | Medium     | Medium | Schema-constrained output (ADR-003) ensures the label is always from the enum. Quality variance is in whether "cautious + low growth" maps to `stagnation` or `contraction`. Acceptable for a derived label — this is not a quant model. |
| Background preloading competes with first paint on slower networks              | Medium     | Medium | Start warming only after the initial screen is interactive, cap concurrency at `3`, and prioritize user-intent countries before the rest of the monitored set.                                                                           |
| Timeline charts add significant bundle weight                                   | Low        | Low    | Recharts is already bundled. Adding `<LineChart>` components is incremental. Lazy-load the timeline section if needed.                                                                                                                   |
| Scope creep into multi-country comparison                                       | Medium     | High   | Explicitly excluded in non-goals. The timeline is per-country only. Cross-country comparison is a separate PRD.                                                                                                                          |

---

## 10. Phased Rollout

### Phase 1 — Direct Access & Map Polish

_Estimated complexity: Medium. No backend changes._

| Deliverable                        | Track |
| ---------------------------------- | ----- |
| Country directory page (Feature 5) | B     |
| Click-away map reset (Feature 2)   | A     |
| Map hover preview (Feature 1)      | A     |

**Why first:** These are pure frontend changes that fix the most visible usability dead-ends. They can ship without any API or pipeline modification and immediately improve the product's perceived quality.

### Phase 2 — Historical Data Pipeline

_Estimated complexity: Medium. Backend + API changes._

| Deliverable                                 | Track |
| ------------------------------------------- | ----- |
| `prepare_time_series()` in analyser.py      | C     |
| Firestore document enrichment in storage.py | C     |
| openapi.yaml schema extension               | C     |
| Handler changes in countries.py             | C     |
| Regime label prompt extension (Feature 8)   | C     |

**Why second:** This is the data-availability prerequisite for the timeline view. It can be validated independently: run the pipeline, inspect the Firestore documents, and confirm the API returns full series. No frontend dependency.

### Phase 3 — Country Timeline & Enriched Popover

_Estimated complexity: Medium-High. Frontend-intensive._

| Deliverable                                                           | Track |
| --------------------------------------------------------------------- | ----- |
| Country timeline view (Feature 7)                                     | C     |
| Enriched map popover with metrics (Feature 3)                         | A     |
| Dense market signal grid (Feature 4)                                  | A     |
| Regime label display on country page and popover (Feature 8 frontend) | C     |

**Why last:** These are the highest-polish features and depend on Phase 2's data availability. The timeline charts in particular require careful design-system alignment (dark chart theming, Commit Mono axes, anomaly dots) and should be implemented with the design review workflow.

---

## 11. Validation Strategy

| Phase   | Validation method                                                                                                                                                                                                                                                                                                      |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 1 | Manual walkthrough: can a new user reach any country's intelligence page in ≤2 interactions from any starting page? Time the path and compare to current state.                                                                                                                                                        |
| Phase 2 | Pipeline integration test: trigger a full pipeline run, then verify that `/countries/US` returns a `time_series` array with ≥10 data points per indicator. Verify document size stays under 100KB.                                                                                                                     |
| Phase 3 | Design review workflow (`.agents/workflows/frontend-design-review.md`): appearance audit, taste audit, motion audit against the design system. Specific check: do timeline charts pass the "Bloomberg not Tableau" test — monospace labels, no decorative fills, no rounded tooltips, information density prioritised. |

---

## 12. Open Questions

| #   | Question                                                                                                                                                            | Blocking?                                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Should the country directory also appear as a sidebar or panel on the Global Overview page (replacing or alongside the pressure queue), or remain a separate route? | No — start with separate route, evaluate promotion later.                                                                                        |
| 2   | Should the timeline charts support a toggle between absolute values and YoY % change view?                                                                          | No — default to absolute values. % change is already shown in the KPI cards. Evaluate after user feedback.                                       |
| 3   | When the pipeline is re-run, should historical time series be re-fetched or only the latest year appended?                                                          | No — re-fetch the full window. The pipeline already fetches `2010:2024` on every run. The cost is in World Bank API calls, not Firestore writes. |
