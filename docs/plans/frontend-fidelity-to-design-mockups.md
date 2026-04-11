# Goal

Implement the frontend-fidelity PRD as a shared World Analyst terminal shell plus high-fidelity page compositions that preserve the existing API contract and business-driven testing discipline.

## Context

- The frontend already has route wiring, live overview data, and tokenized CSS, but it does not yet have the shared shell, reusable component layer, or page structure defined by the finalized mockups.
- The mockups are composition references only. The design system remains the implementation rulebook: no shadows, no blur, 8px radius, token-only styling, and restrained orange usage.
- This phase stays frontend-first. Backend contract changes are out of scope unless the current API proves unable to support a truthful UI.
- Several mockup surfaces are richer than the current backend contract. Those surfaces must remain explicitly representative rather than implying live telemetry or live regional intelligence that does not yet exist.

## Affected Areas

- Frontend shell and routing: `frontend/src/App.jsx`
- Shared frontend components: `frontend/src/components/`
- Shared frontend styling: `frontend/src/index.css`
- Route pages: `frontend/src/pages/GlobalOverview.jsx`, `frontend/src/pages/CountryIntelligence.jsx`, `frontend/src/pages/HowItWorks.jsx`, `frontend/src/pages/PipelineTrigger.jsx`
- Overview derivation logic and tests: `frontend/src/pages/globalOverviewModel.js`, `frontend/tests/globalOverviewModel.test.js`
- Planning and decision trail: `docs/plans/task-board.md`, `docs/DECISIONS.md`

## Implementation Steps

1. Audit the finalized mockups against the design system and normalize the main conflicts up front: shell ownership, orange-accent discipline, and placeholder truthfulness for non-live surfaces.
2. Introduce a shared application shell that owns top navigation, responsive collapse behavior, and the persistent responsible-AI footer.
3. Extract the first reusable UI primitives only where duplication is already justified: page header, KPI card, AI insight panel, status pill, and market switcher.
4. Recompose the four page routes around the shared shell and primitives while preserving current live API behavior on the overview, country, and trigger flows, including map-to-country drill-in and a summary-first country layout.
5. Implement representative but clearly labeled placeholder surfaces where the current API does not yet expose truthful data for maps, regional rollups, or architecture telemetry, and avoid placeholder chart regions on the country page unless they add real signal value.
6. Extend business-driven frontend tests around the new overview derivations and run lint, build, and manual breakpoint QA.

## Validation

- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:overview`
- Manual QA at 1440px, 768px, and 375px for shell integrity, nav state, KPI reflow, dense panel overflow, and representative-surface labeling.
- Manual UX check that orange remains reserved for AI, primary CTA, and pipeline-running emphasis rather than generic active-state decoration.

## ADR Check

- ADR required: yes.
- Record that the frontend-fidelity phase will preserve the current API boundary and use explicitly representative surfaces where the backend does not yet provide truthful data.

## Open Questions

- None blocking for this pass. The current implementation will keep route semantics as-is: `/pipeline` for How It Works and `/trigger` for the pipeline execution console.
