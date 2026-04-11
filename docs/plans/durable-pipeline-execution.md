# Goal

Replace process-local repository state with a durable mixed-document storage/status adapter, then harden pipeline execution onto production boundaries without changing the current frontend contract.

## Context

- The local slice is validated: trigger, status, country detail, Global Overview, and Pipeline Trigger all work against the current API contract.
- The biggest remaining production gap is state ownership. Indicator insights, country briefings, and pipeline status still depend on a shared in-memory repository inside one process.
- The frontend contract is already good enough for the current product surface, so this phase should preserve response shapes and polling behavior.
- This work is substantial enough to justify the dual-lane implementation plus review workflow because it touches shared state, API behavior, tests, and deployment assumptions.
- Relevant skills: `world-analyst-engineering`, `connexion-api-development`, `llm-prompting-and-evaluation`, and `humanizer-pro` for ADR and plan clarity.

## Affected Areas

- Shared repository boundary: `shared/repository.py`, `shared/local_repository.py`, `shared/firestore_repository.py`
- Pipeline orchestration and storage: `pipeline/main.py`, `pipeline/storage.py`
- API handlers that read or write repository state: `api/handlers/pipeline.py`, `api/handlers/countries.py`, `api/handlers/indicators.py`
- Tests covering repository behavior and end-to-end status flows: `api/tests/`, `pipeline/tests/`
- Decision log: `docs/DECISIONS.md`

## Implementation Steps

1. Introduce a backend-selected repository contract that supports both local and Firestore-backed mixed-document storage while preserving the current payload shapes.
2. Keep local mode as the default for tests and deterministic development, but add a Firestore-backed adapter for indicator, country, and pipeline-status records in the same logical collection.
3. Route the API and pipeline through the shared repository selector so both services read and write the same durable state when Firestore mode is enabled.
4. Validate that the current frontend contract remains stable by keeping `GET /pipeline/status`, `GET /countries`, `GET /countries/{country_code}`, and `GET /indicators` unchanged.
5. Add adapter-level tests to prove the Firestore-backed repository returns the same logical shapes as local mode.
6. After the durable repository boundary is stable, implement out-of-process pipeline execution and persisted status transitions on the real job boundary rather than inside the API process.

## Validation

- `cd api && python -m pytest tests/ -v`
- `cd pipeline && python -m pytest tests/ -v`
- `cd frontend && npm run lint && npm run build`
- Manual check: the current frontend still renders idle, running, complete, and country-detail states without contract changes.
- Manual check: enabling Firestore mode through environment configuration materialises pipeline status and country detail across process boundaries.
- Review risk: this phase intentionally fixes durable state first; execution is still in-process until the next hardening step.

## ADR Check

- ADR required: yes.
- This change chooses a durable mixed-document repository boundary and keeps the API contract stable while deferring job-dispatch hardening to the next step.

## Open Questions

- Which service should own the authoritative transition from `running` to terminal states once execution moves to Cloud Run Jobs?
- Do we want a dedicated trigger-run identifier in the API contract, or do we keep the single `current` status document until concurrent runs become a real requirement?
- Should raw data archival to GCS happen inside the same durable execution phase or remain a separate hardening task?