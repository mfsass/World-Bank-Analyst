# Goal

Implement durable storage, status, and provenance behind the current API contract. Keep the trigger flow and frontend response shapes stable while replacing thin process-local state with durable mixed-document persistence, run-scoped raw archival linkage, and persisted-only provenance.

## Approved Choices

- `1A`: Persist run-scoped provenance now, but keep it out of the public API unless a field is required to preserve current behavior.
- `2A`: Standardize on `REPOSITORY_MODE=local|firestore`, with `WORLD_ANALYST_STORAGE_BACKEND` retained only as a backward-compatible alias.
- `3A`: Update this plan artifact in place rather than creating a new implementation brief.

## Context

- The current frontend contract is already acceptable for the bounded product surface. This phase should strengthen the storage and status boundary without forcing new routes or payload redesign.
- The local slice still relies on process-local state ownership. That is the main credibility gap for restart safety, cross-service parity, and reviewable provenance.
- Raw archival now belongs in the same bounded phase as processed persistence because the challenge brief explicitly calls for raw data storage in GCP, and the stored records need a stable raw-backup reference.
- The current pipeline still runs inside the API process. This implementation keeps that execution model and hardens storage/status only.

## Affected Areas

- Shared repository boundary: `shared/repository.py`, `shared/local_repository.py`, `shared/firestore_repository.py`
- Pipeline orchestration and storage: `pipeline/main.py`, `pipeline/storage.py`, `pipeline/local_data.py`, `pipeline/fetcher.py`, `pipeline/dev_ai_adapter.py`
- API status handling: `api/handlers/pipeline.py`
- Contract and parity tests: `api/tests/`, `pipeline/tests/`
- Decision log: `docs/DECISIONS.md`

## Implementation Steps

1. Refactor the shared repository selector to prefer `REPOSITORY_MODE` while keeping the legacy storage env var as an alias, and make repository reads project stored records back to the existing API shapes.
2. Persist richer pipeline status internally: run id, step timestamps, step durations, and failure summary detail, while keeping `GET /pipeline/status` on the current public contract.
3. Generate a UUID v4 run id at pipeline entry and thread it through status, raw archive naming, and stored indicator/country records.
4. Add a raw archive boundary that can write to local filesystem storage in tests and development, or GCS in deployed environments, using the same run-scoped path scheme.
5. Archive raw payloads before processed persistence completes, then write indicator and country records with run id, raw backup reference, source provenance, and minimal AI provenance when available.
6. Extend tests to prove repository parity, API contract stability, persisted provenance, raw archive linkage, and backend-selection semantics.

## Validation

- `cd api && python -m pytest tests/ -v`
- `cd pipeline && python -m pytest tests/ -v`
- `cd api && python -m pytest tests/test_local_vertical_slice.py -v`
- `cd pipeline && python -m pytest tests/test_local_pipeline.py tests/test_firestore_repository.py -v`
- Manual check: the current frontend still renders idle, running, complete, failed, and country-detail states without contract changes.
- Manual check: when Firestore mode is enabled, API and pipeline processes read and write the same persisted status and country detail records.

## ADR Check

- ADR required: yes.
- This implementation introduces a local raw-archive adapter behind the same run-scoped archive contract used by GCS. That trade-off belongs in `docs/DECISIONS.md`.

## Open Questions

- Which service should own the authoritative transition from `running` to terminal states once execution moves to Cloud Run Jobs?
- Do we keep the single `current` status document until concurrent runs become a real requirement, or does a future runtime phase justify exposing a run identifier publicly?
