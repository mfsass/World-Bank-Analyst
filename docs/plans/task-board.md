# World Analyst Task Board

## In Progress

*(Nothing actively in flight.)*

## Next Up

*(No must-ship execution tracks remain. The items below are optional follow-on work rather than blockers for the current presentation build.)*

## Queued (after above)

- [ ] **Country Intelligence Enhancement Phase 2** — `prepare_time_series()`, Firestore enrichment, openapi.yaml schema extension, regime label prompt extension. Backend + API. Blocked by: nothing (independent of Phase 1).
- [ ] **Country Intelligence Enhancement Phase 3** — Enriched map popover, dense signal grid. Frontend-intensive. Blocked by: Phase 2 data availability.
- [ ] Reconcile frontend mocks and presentation copy with the 17-country exact-complete core panel.

## Blocked

- [ ] None currently.

## Done

- [x] Demo polish & presentation: Global Overview default right-rail state, How It Works step navigation, and country panel narrative in the README and UI. Plan: `docs/plans/demo-polish-presentation.md`.
- [x] Technical hardening: trigger cooldown (`429` + `Retry-After`), country timelines, regime badge, and stronger country-entry flow. Plan: `docs/plans/technical-hardening.md`.
- [x] ADR cleanup: trimmed from 72 to 20 fork-in-the-road decisions. Full archive in `private-context/DECISIONS_ARCHIVE_2026-04-13.md`.
- [x] Three-perspective evaluation (CTO / CEO / CFO). Findings in session context, April 2026.
- [x] Cloud deployment: 3-service Cloud Run topology, Cloud Scheduler, Secret Manager, Firestore, GCS. PRD: `cloud-deployment-scheduling-and-runtime-topology.md`.
- [x] Security & hardening: nginx same-origin proxy, fail-fast config, non-wildcard CORS, idempotent trigger. PRD: `security-testing-and-hardening.md`.
- [x] Live AI integration: Gemma 4 baseline, schema-constrained output, evaluation gate. PRD: `live-ai-integration.md`.
- [x] Frontend fidelity: shared shell, 4-page composition, design system tokens. PRD: `frontend-fidelity-to-design-mockups.md`.
- [x] Replace the superseded ML6-market 15-country scope with the 2024 exact-complete 17-country core panel.
- [x] Expand the live seam from the ZA-first slice to the canonical monitored-country set.
- [x] Validate the monitored-country live path end to end against the live World Bank API.
