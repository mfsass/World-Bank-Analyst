# Goal

Implement the first local vertical slice: trigger a one-country pipeline run, expose ephemeral status, and return one country detail payload that the frontend can render without placeholder content.

## Context

- User-selected direction is local-first, one-country, Pipeline Trigger plus Country Detail.
- The first milestone should avoid premature GCP wiring and avoid live LLM dependency during development.
- The API contract already expects country detail fields including `macro_synthesis`, `risk_flags`, and `outlook`.
- The current repo can generate synthesis in memory but does not yet persist or serve it.

## Affected Areas

- Pipeline: [pipeline/main.py](../../pipeline/main.py), [pipeline/storage.py](../../pipeline/storage.py), [pipeline/ai_client.py](../../pipeline/ai_client.py)
- API: [api/openapi.yaml](../../api/openapi.yaml), [api/handlers/pipeline.py](../../api/handlers/pipeline.py), [api/handlers/countries.py](../../api/handlers/countries.py)
- Frontend: [frontend/src/pages/PipelineTrigger.jsx](../../frontend/src/pages/PipelineTrigger.jsx), [frontend/src/pages/CountryIntelligence.jsx](../../frontend/src/pages/CountryIntelligence.jsx)
- Tests: [api/tests](../../api/tests), [pipeline/tests](../../pipeline/tests)
- Decision log: [docs/DECISIONS.md](../DECISIONS.md)

## Scope

- One country only for the first slice.
- Deterministic fallback AI responses for local development.
- Ephemeral pipeline status in memory.
- Local repository or fixture-backed storage adapter, not Firestore yet.

## Selected Implementation Decisions

- Development target country: `ZA`
- Local repository adapter location: shared module from the start so both `pipeline/` and `api/` use the same contract boundary
- Development AI mode: deterministic fallback locally, real LLM later for the production-ready demo release
- Deterministic fallback placement: separate development adapter, keeping [pipeline/ai_client.py](../../pipeline/ai_client.py) focused on real providers
- Pipeline status mode: ephemeral for the first slice

## Out of Scope

- Full 15-country run
- Firestore and GCS integration
- Cloud Run job dispatch
- Real LLM calls in normal local development
- Global Overview data integration

## Implementation Steps

1. Use `ZA` as the one-country development target and create a deterministic local data path for that country.
2. Add a separate development AI adapter that returns deterministic indicator analysis and country synthesis outputs for local runs.
3. Add a shared local storage/repository adapter that can hold mixed record types for `indicator`, `country`, and `pipeline_status`.
4. Update the pipeline flow so a local run writes both indicator-level outputs and the computed country synthesis payload.
5. Implement `POST /pipeline/trigger` and `GET /pipeline/status` against ephemeral in-memory state.
6. Implement `GET /countries/{country_code}` against the shared local repository adapter using the same contract shape the future Firestore version will serve.
7. Connect the Pipeline Trigger page to the trigger/status endpoints and the Country Intelligence page to the country endpoint.
8. Add business-driven tests for one-country trigger, status transition, and country-detail retrieval.

## Suggested File Targets

- Shared local repository adapter: create a shared module that both `pipeline/` and `api/` can import without circular dependency.
- Deterministic development AI adapter: separate module alongside the pipeline AI layer, but distinct from [pipeline/ai_client.py](../../pipeline/ai_client.py).
- Pipeline orchestration updates: [pipeline/main.py](../../pipeline/main.py)
- Local storage shape and adapter logic: [pipeline/storage.py](../../pipeline/storage.py) or a new shared storage abstraction if cleaner
- Trigger and status handlers: [api/handlers/pipeline.py](../../api/handlers/pipeline.py)
- Country detail handler: [api/handlers/countries.py](../../api/handlers/countries.py)
- Frontend integration points: [frontend/src/pages/PipelineTrigger.jsx](../../frontend/src/pages/PipelineTrigger.jsx) and [frontend/src/pages/CountryIntelligence.jsx](../../frontend/src/pages/CountryIntelligence.jsx)
- Business tests: [api/tests](../../api/tests) and [pipeline/tests](../../pipeline/tests)

## Validation

- Triggering the pipeline changes status from `idle` to `running` to `complete` within the local slice.
- The local run produces a country detail payload containing indicators, `macro_synthesis`, `risk_flags`, and `outlook`.
- The Country Intelligence page renders real API data for the chosen country without placeholder copy.
- The deterministic fallback keeps local runs stable and testable.
- The record shapes remain compatible with the single-collection mixed-document Firestore model chosen for later.

## ADR Check

- ADR required: yes.
- The mixed-document single-collection model and local-first MVP sequence are now selected trade-offs and should be documented.

## Open Questions

- No material planning blockers remain for the first implementation pass.