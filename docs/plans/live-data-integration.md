# Goal

Implement live World Bank data ingestion for the approved monitored scope while preserving the current analysis, storage, API, and frontend contracts and keeping deterministic local mode available.

## Status

Implemented and validated locally on 2026-04-11.

## Outcome

- The live pipeline now runs through the canonical exact-complete 17-country core panel instead of the original ZA-only slice and replaces the earlier ML6-market 15-country live scope.
- Live fetches are pinned to the World Bank Indicators source (`source=2`), use a configurable timeout with a 45-second default, and fail loudly if the response unexpectedly spans multiple pages.
- Raw archives are stored as thin request-response envelopes per run, preserving URL, params, fetch metadata, and the verbatim response body together.
- Annual series whose latest non-null observation is older than one year from the requested window end are treated as stale coverage and excluded from normalized live output.
- The deterministic ZA local slice remains available for tests and development even though ZA is no longer part of the live monitored panel.
- A live smoke against the full panel succeeded end to end with 1,530 usable data points, 102 indicator insights, 17 country syntheses, 7 raw payload archives, and 0 fetch failures.

## Closure Validation

- `cd pipeline && python -m pytest tests -v` passed (`24 passed`).
- `cd api && python -m pytest tests -v` passed (`11 passed`).
- Live pipeline smoke with `PIPELINE_MODE=live` and `REPOSITORY_MODE=local` confirmed full 17-country coverage for all six indicators: 255 usable rows per indicator, 1,530 total usable data points, 102 indicator insights, 17 country syntheses, and 0 fetch failures.

## Context

- `pipeline/fetcher.py` already contains the bounded World Bank fetch path for the approved six indicators, and the live seam now runs through the canonical monitored-country set resolved in ADR-041.
- Durable storage, run-scoped raw archive paths, and pipeline status persistence are already in place. This PRD should reuse that seam instead of introducing a second storage or provenance path.
- Scope stays fixed to the approved six indicators, the 15-year `2010:2024` window from ADR-041, and the partial-success policy from ADR-020.
- ADR-041 resolves the monitored-country set in favor of the exact-complete 17-country core panel and supersedes the earlier 15-country live scope for active runtime behavior.
- This PRD is where real runs move from the original single-country local slice to the approved monitored-country set. Local mode still keeps the deterministic ZA fixture for tests and development.

## Affected Areas

- Pipeline fetch and orchestration: `pipeline/fetcher.py`, `pipeline/main.py`, `pipeline/local_data.py`
- Analysis and storage seams: `pipeline/analyser.py`, `pipeline/storage.py`
- Shared monitored-country metadata and repository parity: `shared/repository.py`, `shared/local_repository.py`, `shared/firestore_repository.py`
- API surfaces that expose run state and monitored-country coverage: `api/handlers/pipeline.py`, `api/handlers/countries.py`
- Business and contract tests: `pipeline/tests/`, `api/tests/`, and frontend-backed contract checks where country coverage matters
- Decision and context docs: `docs/DECISIONS.md`, `docs/context/world-analyst-project.md`
- Relevant skills: `world-bank-api`, `world-analyst-engineering`

## Implementation Steps

1. Lock the live scope and make it the single source of truth.
2. Confirm the canonical 17-country exact-complete list, keep the approved six indicators, and keep `2010:2024` as the live history window.
3. Centralize the monitored-country catalog so fetch configuration, repository metadata, and API country listing cannot drift.
4. If the approved country set changes from ADR-006, update `docs/DECISIONS.md` and `docs/context/world-analyst-project.md` before implementation.
5. Refactor the fetch stage so `PIPELINE_MODE=local|live` is a real runtime seam.
6. Keep one fetch entry point in `pipeline/main.py`, but make it choose local fixtures or live World Bank ingestion based on configuration.
7. Make the live fetch boundary return both normalized records for analysis and raw response payloads plus request metadata for archival, provenance, and error diagnosis.
8. Detect logical World Bank API errors inside HTTP 200 responses and attach `run_id`, indicator code, and affected scope to logs and failure summaries.
9. Preserve one normalized downstream data shape.
10. Normalize live rows into the same record shape already consumed by `pipeline/analyser.py` and repository-backed storage.
11. Filter null and unusable rows before analysis. Do not interpolate and do not treat null as zero.
12. Validate that each country-indicator series has enough usable history to participate or be reported as missing.
13. Implement the run-level partial-success rules from the PRD.
14. Preserve successful outputs from mixed live runs.
15. End the overall run in terminal `failed` when coverage is incomplete, and surface the missing countries or indicators through status and logs without inventing a new public status enum.
16. Expand monitored-country metadata and contract parity.
17. Replace the ZA-only repository country catalog with the approved monitored-country set so `GET /countries` and overview coverage reflect real scope.
18. Keep deterministic local mode for development and tests, but ensure local and live modes still project the same public contract.
19. Prove the behavior with business-driven tests.
20. Add tests for live fetch normalization, null filtering, invalid indicator failure, payload-level API errors, partial-success preservation, run-scoped provenance, and monitored-country list parity.
21. Re-run existing pipeline, API, and frontend-backed contract checks against the updated country coverage and status behavior.

## Validation

- `cd pipeline && python -m pytest tests/ -v`
- `cd api && python -m pytest tests/ -v`
- Add targeted tests that prove HTTP-200 payload errors fail clearly, null rows are excluded, and partial runs preserve good outputs while ending in terminal `failed`.
- Manual smoke run with `PIPELINE_MODE=live` and `REPOSITORY_MODE=local` to confirm the live fetch path writes records through the existing repository seam before Firestore deployment.
- Manual check that `GET /countries` returns the approved monitored-country set and that run summaries reflect the full 17-country scope without drifting from repository metadata.
- Manual check that run-scoped archives under `runs/{run_id}/raw/` contain request-scoped live payloads rather than only post-normalization records.

## ADR Check

- ADR-041 locked the canonical exact-complete 17-country monitored set and the `2010:2024` live history window, superseding ADR-019 and ADR-037 for active live scope.
- ADR-039 locked the live fetch contract around WDI `source=2`, configurable timeouts, and fail-loudly behavior for unexpected multi-page responses.
- ADR-040 locked the freshness rule that treats annual series older than one year as stale coverage.
- No further ADR is required to close this PRD. Remaining live-source gaps are handled by the explicit partial-success contract rather than by another architectural change.

## Resolved Questions

- Raw archives store a thin request-response envelope that keeps request URL, params, fetch timestamp, response metadata, and the raw response body together.
- For a requested annual range ending in year `Y`, a series remains usable only when its latest non-null observation is at least `Y - 1`. Older tails are treated as stale coverage and excluded before analysis.
