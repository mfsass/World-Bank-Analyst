# Goal

Integrate the Global Overview landing page with the current local/API slice so the product opens on live, finance-oriented intelligence instead of placeholder content.

## Context

- The first local vertical slice is complete: `POST /pipeline/trigger`, `GET /pipeline/status`, and `GET /countries/{country_code}` work locally for `ZA`.
- The current implementation already materialises live local data through the shared in-memory mixed-document repository, deterministic development AI adapter, and in-process background trigger execution.
- The landing page is still placeholder content even though the API already exposes enough data to render a meaningful top-level dashboard.
- Delivery scope remains intentionally bounded: preserve spec-driven development, avoid casual infrastructure expansion, and keep the presentation finance-user oriented and risk-weighted.
- Create a new plan file for this phase rather than extending the first-slice plan.

## Selected Decision

- Prioritize Global Overview integration next.
- Use the current API surface by default: `GET /pipeline/status`, `GET /countries`, `GET /indicators`, and `GET /countries/{country_code}` are the starting boundary for the page.
- Present the landing page honestly as the currently materialised coverage universe of the local slice; do not fake 15-country or map-heavy breadth before the data exists.
- Defer Firestore repository hardening, Cloud Run Job trigger/status hardening, real LLM provider wiring, and How It Works completion until the landing dashboard is live.
- Comparison against the alternatives:
  - Global Overview integration: highest demo value, lowest incremental risk, and direct reuse of the completed slice.
  - Firestore-backed repository: important next for deployment realism, but lower immediate user-facing value while the landing page remains placeholder.
  - Cloud Run Job trigger/status hardening: depends on durable persistence and deployment wiring, so it is premature for the next implementation phase.
  - Real LLM provider integration: improves narrative quality but adds credentials, variability, and latency risk without broadening the visible product surface.
  - How It Works completion: useful demo polish, but secondary to making the main dashboard itself live.

## Affected Areas

- Frontend: `frontend/src/pages/GlobalOverview.jsx`
- Frontend styles: `frontend/src/index.css`
- Frontend routing and CTA touchpoints if needed: `frontend/src/App.jsx`
- Existing API boundaries expected to be consumed as-is: `api/openapi.yaml`, `api/handlers/indicators.py`, `api/handlers/countries.py`, `api/handlers/pipeline.py`
- Optional API/test changes only if a real data gap appears: `api/tests/`
- Design references: `docs/design-mockups/Global Overview Finalized.html`, `docs/design-mockups/Design System.md`
- Relevant skills/docs: `world-analyst-design-system`, `world-analyst-engineering`, and `connexion-api-development` if the contract must change

## In Scope

- Replace Global Overview placeholder content with live KPI and status content sourced from the existing local/API slice.
- Support explicit idle, running, complete, and failed page states.
- Surface finance-user-relevant summary signals from the current slice, such as materialised coverage, indicator count, anomaly count, and latest outlook/status.
- Add clear navigation and CTA flow between Global Overview, Pipeline Trigger, and Country Intelligence.
- Keep the responsible AI disclaimer visible on the landing page.

## Out of Scope

- Firestore and GCS integration
- Cloud Run Job dispatch or durable status persistence
- Real LLM provider integration
- 15-country expansion
- Choropleth or map implementation
- New frontend test infrastructure
- How It Works page completion beyond any minimal link consistency needed for navigation

## Implementation Steps

1. Define the Global Overview page states against the current slice: pre-run idle, running, complete with `ZA` briefing available, and failed.
2. Wire `frontend/src/pages/GlobalOverview.jsx` to the existing endpoints for pipeline status, country coverage, and indicator insights; only fetch `ZA` detail when a materialised briefing exists.
3. Replace the placeholder KPI row with live metrics that matter to a finance user: pipeline status, countries materialised, indicators analysed, anomalies detected, and refresh context.
4. Replace the placeholder lower panel with a live briefing surface that summarizes the current `ZA` output, highlights risk-weighted signals, and links to `/trigger` and `/country/za`.
5. Extend `frontend/src/index.css` only as needed to support the new layout while preserving the design system's 32px rhythm, 8px radius, tonal depth, and orange-accent rules.
6. Keep backend scope flat by default. If the page exposes a genuine API shape gap, update `api/openapi.yaml` first, then implement the minimal handler and test changes required.
7. Run lint/build and existing backend tests, then manually verify the landing-page-to-trigger-to-country-detail flow end to end.

## Validation

- The landing page loads meaningful live content before and after a pipeline run; no placeholder copy remains.
- From the idle state, the page clearly directs the user to run the pipeline.
- During execution, the landing page reflects the same status as `GET /pipeline/status`.
- After completion, KPI counts and the briefing teaser align with the API payloads and link correctly to the `ZA` detail page.
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd api && python -m pytest tests/ -v`
- `cd pipeline && python -m pytest tests/ -v`

## ADR Check

- ADR required: yes.
- Record that the next implementation phase prioritizes Global Overview integration over persistence, deployment hardening, and live-provider work.

## Open Questions

- Should the landing page keep the `Global Overview` title while only the `ZA` slice is materialised, or should supporting copy explicitly frame it as current monitored coverage?
- Is a dedicated overview endpoint unnecessary for the current bounded scope, or does the page become too chatty once implemented? Default assumption: existing endpoints are sufficient.
