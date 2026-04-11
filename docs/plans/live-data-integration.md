# Goal

Implement live World Bank data ingestion for the approved monitored scope while preserving the current analysis, storage, API, and frontend contracts and keeping deterministic local mode available.

## Context

- `pipeline/fetcher.py` already contains a bounded World Bank fetcher for the approved six indicators, but `pipeline/main.py` still falls back to the local ZA fixture path for every run.
- Durable storage, run-scoped raw archive paths, and pipeline status persistence are already in place. This PRD should reuse that seam instead of introducing a second storage or provenance path.
- Scope stays fixed to the approved six indicators, the seven-year `2017:2023` window from ADR-019, and the partial-success policy from ADR-020.
- The monitored-country set is not aligned across the repo. ADR-006, the product brief, and `pipeline/fetcher.py` do not currently describe the same 15-country scope. Resolve that before code work starts.
- This PRD is where real runs should move from the current single-country local slice to the approved monitored-country set. It is not the phase to expand beyond the approved 15-country cap.

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
2. Confirm the canonical 15-country list, keep the approved six indicators, and keep `2017:2023` as the live history window.
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
- Manual check that `GET /countries` returns the approved monitored-country set and that `GET /pipeline/status` exposes incomplete coverage clearly after a partial live run.
- Manual check that run-scoped archives under `runs/{run_id}/raw/` contain request-scoped live payloads rather than only post-normalization records.

## ADR Check

- ADR likely required if the canonical 15-country list changes from ADR-006 or if raw archival is defined as a wrapped request-response envelope rather than a verbatim indicator payload.
- No ADR is needed just to wire the approved live-data path into the current pipeline seam.
- Expanding beyond the approved 15-country cap is out of scope for this PRD and would need its own ADR and follow-on plan.

## Open Questions

- Which 15-country list is canonical? ADR-006, the product brief, and the current fetcher do not match.
- Should the raw archive store the verbatim World Bank response body per request, or a thin envelope that adds request URL, params, fetch timestamp, and the raw body together?
- What is the minimum usable-history rule for analysis eligibility when a live series is sparse after null filtering?