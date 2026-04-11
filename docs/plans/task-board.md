# World Analyst Task Board

## In Progress

- [ ] Frontend fidelity to design mockups: shared shell, reusable components, and page-level composition against the current API boundary.

## Next Up

- [ ] Cloud deployment: Cloud Run Job (pipeline), Cloud Run service (API + frontend), Secret Manager wiring, Cloud Scheduler (monthly), trigger handler repointed to Jobs API dispatch.
- [ ] Reconcile frontend mocks and presentation copy with the 17-country exact-complete core panel when the frontend fidelity pass resumes.

## Blocked

- [ ] None currently.

## Done

- [ ] Keep only the most recent completed items here, then fold older context back into plans or ADRs.
- [x] Replace the superseded ML6-market 15-country scope with the 2024 exact-complete 17-country core panel in the live backend.
- [x] Expand the live seam from the ZA-first slice to the canonical monitored-country set without changing API/frontend contract shapes.
- [x] Validate the monitored-country live path end to end against the live World Bank API.
- [x] Resolve the canonical monitored-country scope across ADRs, the product brief, and the fetcher in favor of the 2024 exact-complete 17-country core panel.
