# PRD: Durable storage, status, and provenance

## 1. Product overview

### 1.1 Document title and version
Durable storage, status, and provenance
Version: 0.1
Date: 2026-04-09
Status: Draft for approval

### 1.2 Product summary
World Analyst already proves the local product loop: a user can trigger the pipeline, watch status progress, and open a country briefing. The remaining gap is that much of this behavior still depends on process-local state. That makes the system good enough for a local slice, but not strong enough for a durable product or a defensible cloud architecture.

This PRD defines the storage hardening phase that follows the landing-dashboard baseline already established in the local slice. Firestore becomes the durable system of record for processed dashboard-facing records, GCS holds raw World Bank payload backups, and the pipeline writes enough provenance to explain where a result came from without turning the product into a full observability platform. The current trigger flow stays in place for now so this PRD remains focused on state contracts and persistence boundaries rather than cloud runtime wiring or job orchestration.

## 2. Goals

### 2.1 Business goals
- Make World Analyst behave like a real product rather than a process-local demo.
- Preserve the current user-facing dashboard flow while strengthening the underlying system.
- Improve trust by making each dashboard result traceable to a pipeline run and a raw data source backup.
- Keep the architecture aligned with the challenge brief: Firestore for processed insights and GCS for raw archival.

### 2.2 User goals
- As a finance user, I want the latest briefing and pipeline status to remain available even after a service restart.
- As a reviewer, I want to understand what data was used and which run produced the current result.
- As an engineer, I want the API and frontend to keep working without contract changes when durable storage is enabled.

### 2.3 Non-goals (explicit out-of-scope)
- Replacing the current in-process trigger with Cloud Run Job dispatch.
- Wiring Secret Manager, Cloud Run permissions, or service-to-service runtime integration. That belongs to the cloud deployment, scheduling, and runtime topology PRD.
- Expanding the current KPI universe beyond the current core six indicators.
- Shipping full AI governance, token accounting, or prompt warehousing.
- Building a complete observability platform with dashboards, traces, and alerts.
- Reworking the frontend information architecture or design system.
- Adding multi-run concurrency as a first-class product feature.

## 3. User personas

### 3.1 Key user types
- Finance reviewer using the dashboard to assess macro risk signals.
- ML6 evaluator reviewing the product for architectural clarity and production-minded design.
- Engineer or maintainer validating that the pipeline and API behave consistently across restarts.

### 3.2 Basic persona details
- Finance reviewer: expects concise, risk-weighted output and does not care about internal implementation unless trust breaks.
- ML6 evaluator: cares about intent-first architecture, explainability, and whether the system is production-grade rather than demo-only.
- Engineer: needs durable state, simple failure diagnosis, and stable contracts across local and Firestore-backed modes.

### 3.3 Role-based access (if applicable)
- All current product users remain behind the existing API key pattern.
- No new role model is introduced in this PRD.
- Internal operators may access raw GCS backups and structured logs through cloud tooling, not through the frontend.

## 4. Functional requirements

- **Durable processed storage** (Priority: High)
  - Firestore must store indicator insight records, country briefing records, and current pipeline status records.
  - All processed records must live in one mixed `insights` collection with an explicit record-type field so the storage contract stays aligned with ADR-009 and ADR-016.
  - Firestore must remain the single processed document store for this phase.
  - The current API response shapes must remain stable when Firestore mode is enabled.

- **Raw data archival linkage** (Priority: High)
  - Each pipeline run must archive the raw World Bank response payloads to GCS before processed persistence completes.
  - Processed records must retain a reference to the raw backup location for auditability.
  - Raw backups must use a stable run-scoped naming scheme so reviewers can inspect one run without guessing which files belong together.
  - Raw backups must be organized by run and fetch scope so they can be found later without ambiguity.

- **Run-level provenance** (Priority: High)
  - Every processed record written during a run must include a UUID v4 run identifier generated at pipeline entry.
  - This PRD defines the persisted provenance envelope and field locations for durable records.
  - Indicator and country records must include source provenance fields such as source name, source date range, and source last-updated value when available.
  - AI-generated records must include minimal provenance only: provider and model identifier when available. The live AI integration PRD may extend that baseline with prompt-version lineage where it can be carried at low cost.
  - The live data integration PRD adds source-specific provenance fields, and the live AI integration PRD adds AI-specific provenance fields, but this PRD owns how those fields are persisted and surfaced in stored records.
  - The full provenance field set should be finalized during implementation in alignment with the live-data and live-AI PRDs.

- **Stable current-status model** (Priority: High)
  - The system must persist the current pipeline status in Firestore using the same contract expected by the frontend.
  - Status must include step names, step states, start time, completion time when available, and failure summary when a run fails.
  - The current status must be stored as one authoritative `current` record that is overwritten on each new run. Historical run browsing remains out of scope.
  - The current product only needs one authoritative current-status record, not full concurrent run tracking.

- **Repository mode selection** (Priority: High)
  - The API and pipeline must read from and write to the same configured repository backend.
  - Repository mode must be selected through `REPOSITORY_MODE=local|firestore`.
  - Local mode must remain available for deterministic tests and lightweight development.
  - Firestore mode must be selectable by configuration without changing frontend code, and it is the expected mode for deployed services.

- **Contract preservation** (Priority: High)
  - `GET /pipeline/status`, `POST /pipeline/trigger`, `GET /indicators`, `GET /countries`, and `GET /countries/{country_code}` must keep their existing response contracts.
  - Frontend pages must not need a redesign to support durable storage mode.

- **Minimum viable logging** (Priority: Medium)
  - Pipeline logs must include run start, fetch completion, analysis completion, storage completion, retry warnings, and terminal outcome.
  - Logs must be structured JSON written to stdout so local runs stay readable and cloud runs can flow into Cloud Logging unchanged.
  - Failures must log enough context to tie an error back to a run identifier.
  - This PRD does not require central logging dashboards, only structured, reviewable logs.

- **Backward-compatible execution flow** (Priority: Medium)
  - The durable-storage phase keeps trigger execution inside the API process.
  - The trigger flow must write durable status and records so the user experience survives service restarts after persistence completes.
  - Mid-run restarts are not made durable in this phase. The guarantee is that completed or terminal states survive restart once they have been persisted.
  - The cloud deployment, scheduling, and runtime topology PRD will replace in-process execution with Cloud Run Job dispatch.

## 5. User experience

### 5.1 Entry points and first-time user flow
A user opens the dashboard or Pipeline Trigger page and sees the current status of the latest known pipeline run. If no run has happened yet, the UI still shows an idle state. Once a run completes, the user can return later and still retrieve the same country briefing and status without depending on the original process staying alive.

### 5.2 Core experience
The frontend experience should feel unchanged: the user triggers the pipeline, watches step progress, and opens the resulting briefing. The difference is that the underlying records now persist durably in Firestore and can be tied back to a raw GCS backup and a run identifier.

### 5.3 Advanced features and edge cases
If Firestore is enabled and the API restarts, the latest current status and country briefing must still be available. If a run fails, the status view must show a failed terminal state with an error summary rather than silently resetting. If the raw World Bank backup succeeds but processed storage fails, logs and status must make that failure diagnosable.

### 5.4 UI and UX highlights
- No new page is required for this PRD.
- The existing Pipeline Trigger page remains the main visible control surface for status.
- The current responsible AI disclaimer remains visible on human-facing pages.
- Any user-visible copy changes should clarify persistence only if needed; the preferred outcome is that durability improves without adding interface clutter.

## 6. Narrative

World Analyst should stop behaving like a temporary local run and start behaving like a persistent intelligence surface. This PRD makes the current pipeline output durable, restart-safe, and lightly traceable, while preserving the existing demo flow that already works. GCS raw archival is deliberate here because the challenge explicitly calls for storing raw data as well as processed insights in GCP. The result is a more credible product and a cleaner base for later live-data, live-AI, and cloud-execution work.

## 7. Success metrics

### 7.1 User-centric metrics
- A user can trigger the pipeline, refresh the app, and still retrieve the same latest status and materialized country briefing.
- A user can reopen the app after an API restart and still see the latest completed status and saved briefing.
- Failed runs surface an explicit failed state rather than leaving the user in an ambiguous idle state.

### 7.2 Business metrics
- The product demonstrates the intended Firestore plus GCS architecture instead of a local-only slice.
- The system can be explained clearly in a review: raw source in GCS, processed records in Firestore, stable API contract on top.
- Each displayed dashboard record can be tied back to a pipeline run and raw source backup.

### 7.3 Technical metrics
- Firestore mode serves the same logical payload shapes as local mode.
- Processed indicator and country records include run-level and source-level provenance fields.
- Pipeline status persists across process restarts when Firestore mode is enabled.
- Tests cover repository parity and status persistence behavior.
- Frontend lint and build continue to pass without contract changes.

## 8. Technical considerations

### 8.1 Integration points
- Shared repository boundary in `shared/repository.py`, `shared/local_repository.py`, and `shared/firestore_repository.py`.
- Pipeline persistence flow in `pipeline/storage.py` and orchestration in `pipeline/main.py`.
- Status writes and trigger behavior in `api/handlers/pipeline.py`.
- Existing API contract in `api/openapi.yaml` must remain stable.
- Existing frontend pages must continue to consume the same API shapes.
- This PRD owns the durable record contracts and provenance fields. The cloud deployment PRD owns how deployed services authenticate to and connect with Firestore, GCS, and Secret Manager.

### 8.2 Data storage and privacy
- Firestore stores processed records only: indicator insights, country briefings, and current status.
- GCS stores raw World Bank response payloads for auditability and replay support.
- Firestore should store references to raw archives rather than duplicating raw payloads.
- AI provenance is limited to light metadata in this phase and must not store unnecessary sensitive payloads.

### 8.3 Scalability and performance
- The bounded scope remains 15 countries and 6 indicators.
- One mixed Firestore collection remains acceptable at this scale.
- Current collection scans are acceptable for bounded MVP scope but should be revisited before major expansion.
- This PRD optimizes for correctness and durability, not large-scale throughput.

### 8.4 Potential challenges
- Mixing durability work with runtime orchestration would broaden the scope and slow delivery.
- Firestore and GCS writes may succeed independently, so failure handling needs clear status and logs.
- The current single `current` status model limits future concurrent runs but keeps the current product simple.
- The team must avoid overbuilding observability in this phase; the target is minimal trustable provenance, not a full telemetry platform.

## 9. Milestones and sequencing

### 9.1 Project estimate
This is a medium-sized foundational PRD. It is substantial enough to require coordinated backend, pipeline, storage, and test updates, but small enough to remain one bounded implementation phase.

### 9.2 Team size and composition
- One implementation lane covering repository, storage flow, and API status behavior.
- One review lane checking contract drift, provenance completeness, tests, and ADR updates.

### 9.3 Suggested phases
1. Finalize the processed document shape and provenance fields for indicator, country, and status records.
2. Complete Firestore-backed persistence parity with local mode and keep backend selection configurable.
3. Add GCS raw archival and raw backup references into the processed record flow.
4. Harden status persistence and failure behavior while preserving the frontend contract.
5. Add or update tests to prove repository parity, restart-safe status, and processed record completeness.

## 10. User stories

### 10.1 Persist processed insights across restarts
- **ID**: US-1
- **Description**: As a finance user, I want the latest saved country briefing and indicator insights to remain available after a backend restart so that the dashboard behaves like a persistent product.
- **Acceptance criteria**:
  - [ ] When Firestore mode is enabled and a pipeline run completes, `GET /countries/{country_code}` returns a materialized country briefing after the API process restarts.
  - [ ] When Firestore mode is enabled and a pipeline run completes, `GET /indicators` returns the saved processed indicator records after the API process restarts.
  - [ ] The response shape for saved records matches the current API contract used by the frontend.

### 10.2 Preserve current pipeline status durably
- **ID**: US-2
- **Description**: As a user monitoring a run, I want the latest pipeline status to persist durably so that I can still understand the last known state if the service restarts or a run fails.
- **Acceptance criteria**:
  - [ ] When a run starts, the system writes a `running` pipeline status record with step definitions and a start timestamp.
  - [ ] When a run completes, the system writes a terminal `complete` status with a completion timestamp.
  - [ ] When a run fails, the system writes a terminal `failed` status with an error summary that includes the failing step, the error message, and affected country or indicator scope when available.
  - [ ] `GET /pipeline/status` returns the saved current status from Firestore when Firestore mode is enabled.

### 10.3 Keep raw source data auditable
- **ID**: US-3
- **Description**: As an engineer or reviewer, I want each processed result to be traceable to a raw World Bank backup so that I can verify what source data produced the dashboard output.
- **Acceptance criteria**:
  - [ ] Each pipeline run archives the raw World Bank response payloads to GCS.
  - [ ] Each processed indicator or country record written during a run includes a reference to the raw backup location.
  - [ ] The raw archive naming scheme distinguishes runs and fetch scopes clearly enough for manual inspection.

### 10.4 Record minimum viable AI provenance
- **ID**: US-4
- **Description**: As a reviewer, I want each AI-generated record to include light provenance so that I can explain which model configuration produced the visible output.
- **Acceptance criteria**:
  - [ ] Indicator or country records that include AI-generated narrative store an AI provider field when available.
  - [ ] Indicator or country records that include AI-generated narrative store a model identifier field.
  - [ ] This PRD does not require prompt-version, schema-version, full prompt text, or raw model responses in Firestore.

### 10.5 Preserve frontend contract stability
- **ID**: US-5
- **Description**: As an engineer, I want durable storage to slot behind the existing API contract so that the current frontend does not need a redesign to benefit from persistence.
- **Acceptance criteria**:
  - [ ] The API endpoints consumed by the frontend keep their current response shapes after durable storage is enabled.
  - [ ] The existing Global Overview, Country Intelligence, and Pipeline Trigger flows continue to work without requiring new routes.
  - [ ] Frontend lint and build succeed after the durable-storage changes are implemented.
  - [ ] Contract preservation is validated by comparing local-mode and Firestore-mode responses for the existing frontend endpoints or by running the existing frontend-backed integration flow against both modes.
