# Goal

Create a first end-to-end vertical slice that is locally believable, easy to review, and ready to harden onto GCP without reworking the product contract.

## Context

- The repo already has strong intent documents, design constraints, and an API contract.
- The implementation is still scaffold-heavy: several handlers return stubs, frontend pages are placeholders, and there are no tests yet.
- The product scope is intentionally bounded. Reliability and demo clarity matter more than speculative completeness, but the implementation standard should still be production-grade.
- The Pipeline Trigger flow is the centerpiece, but it only works if the data model, API shape, and UI slice line up.

## Affected Areas

- Pipeline: [pipeline/main.py](../../pipeline/main.py), [pipeline/fetcher.py](../../pipeline/fetcher.py), [pipeline/storage.py](../../pipeline/storage.py), [pipeline/ai_client.py](../../pipeline/ai_client.py)
- API: [api/openapi.yaml](../../api/openapi.yaml), [api/handlers/indicators.py](../../api/handlers/indicators.py), [api/handlers/countries.py](../../api/handlers/countries.py), [api/handlers/pipeline.py](../../api/handlers/pipeline.py)
- Frontend: [frontend/src/pages/GlobalOverview.jsx](../../frontend/src/pages/GlobalOverview.jsx), [frontend/src/pages/CountryIntelligence.jsx](../../frontend/src/pages/CountryIntelligence.jsx), [frontend/src/pages/PipelineTrigger.jsx](../../frontend/src/pages/PipelineTrigger.jsx)
- Guidance: [GEMINI.md](../../GEMINI.md), [AGENTS.md](../../AGENTS.md), [docs/DECISIONS.md](../DECISIONS.md)

## What We Have

- Clear architecture and scope in the repo docs.
- A defined API contract in [api/openapi.yaml](../../api/openapi.yaml).
- A working fetcher/analyser/AI skeleton in the pipeline.
- A design-system-aligned frontend shell with the main pages already routed.
- Firestore and GCS dependencies already declared.

## What Is Still Missing

- Country and indicator handlers still return placeholders instead of real data.
- The pipeline generates country-level syntheses in memory but does not persist them.
- The frontend does not yet consume real API data.
- Pipeline status and trigger behavior are still stubbed.
- No business-driven tests exist yet in the API or pipeline test folders.

## What We Have Done In This Pass

- Confirmed that the fetcher should be the source of truth for the 15 target countries.
- Aligned [pipeline/main.py](../../pipeline/main.py) to import the country list from [pipeline/fetcher.py](../../pipeline/fetcher.py) instead of maintaining a second, conflicting list.
- Captured the current repo state and next decision points in this document so planning can stay explicit.

## Recommended Implementation Sequence

1. Lock the MVP data shape for indicator insights, country synthesis, and pipeline status.
2. Implement a local vertical slice behind the API before wiring live GCP infrastructure.
3. Make the Pipeline Trigger page and one country detail page consume that real API output.
4. Add tests around the business outcomes of the slice.
5. Replace local storage and trigger adapters with Firestore, GCS, and Cloud Run job wiring.

## Decision Questions

### 1. What should be the first real slice?

Recommendation: build the Pipeline Trigger flow plus one country detail path first.

- Option A: Pipeline Trigger + Country Detail
- Option B: Global Overview first
- Option C: API and pipeline only, frontend after

### 2. How should we develop before GCP is wired?

Recommendation: use a local fixture or local repository adapter first, then swap in Firestore.

- Option A: Local fixture-backed API first
- Option B: Firestore-first implementation
- Option C: Hybrid, but only for storage

### 3. How should one Firestore collection represent country synthesis?

This is the biggest contract question and likely ADR-worthy.

- Option A: Keep one `insights` collection with mixed document types such as `entity_type=indicator|country|pipeline_status`
- Option B: Keep one `insights` collection for indicator docs and embed country synthesis inside selected country records
- Option C: Break the one-collection constraint and use separate collections

Recommendation: Option A unless the brief explicitly forbids mixed document types.

### 4. What should the first implemented API endpoint be?

Recommendation: start with the endpoint that supports the first visible user flow.

- Option A: `POST /pipeline/trigger` and `GET /pipeline/status`
- Option B: `GET /countries/{country_code}`
- Option C: `GET /indicators`

### 5. When should we wire GCP?

Recommendation: only after the local slice is real and testable.

- Option A: After the local slice works end-to-end
- Option B: Immediately after API handlers are implemented
- Option C: In parallel with frontend work

## Selected Answers

- First real slice: Option A — Pipeline Trigger + Country Detail
- Pre-GCP development mode: Option A — local fixture-backed API first
- One-collection model: Option A — mixed document types in a single `insights` collection
- First API endpoint set: Option A — `POST /pipeline/trigger` and `GET /pipeline/status`
- GCP timing: Option A — after the local slice works end-to-end
- LLM mode for first milestone: deterministic fallback for development, real LLM for production-ready demo release
- Deterministic fallback location: separate development adapter, not inside the real provider module
- Pipeline status for first milestone: ephemeral
- First milestone scope: one country
- First milestone country: `ZA`
- Local repository adapter location: shared module from the start, used by both pipeline and API

## Immediate Planning Outcome

- The next planning artifact should focus on a one-country local vertical slice.
- That slice should prove trigger → status → country output before Firestore, GCS, or Cloud Run are wired.
- The storage contract should still be shaped so it can later map cleanly onto the single-collection Firestore design.
- The first country payload and UI path should be built around `ZA`.
- The local repository adapter should be introduced as a shared abstraction, not a pipeline-only temporary module.

## Implementation Steps

1. Confirm the answers to the five decision questions above.
2. Convert those answers into a narrow implementation plan for the first slice.
3. Implement the storage contract and the first API path.
4. Connect the first frontend page to live local data.
5. Add business-driven tests before GCP hardening.

## Validation

- Confirm the pipeline uses the same 15-country list everywhere.
- Confirm the first API slice returns data that already matches the frontend's needs.
- Confirm the frontend renders the slice without hardcoded placeholder content.
- Confirm the chosen storage shape can support [api/openapi.yaml](../../api/openapi.yaml) without awkward translation layers.

## ADR Check

- Country-list alignment itself does not need an ADR.
- The document shape for country synthesis and pipeline status likely does need an ADR because it is a real trade-off with review implications.

## Open Questions

- Should the first demo use live LLM calls, or should we allow a deterministic local fallback for development?
- Do we want pipeline status to be ephemeral in memory first, or persisted from the beginning?
- Do we want the first milestone to support one country only for speed, or all 15 countries from day one?