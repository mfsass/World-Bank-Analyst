# PRD: Live data integration

## 1. Product overview

### 1.1 Document title and version
Live data integration
Version: 0.1
Date: 2026-04-10
Status: Draft for approval

### 1.2 Product summary
World Analyst already has the structure of a pipeline, but the current end-to-end slice still depends on deterministic local fixture data. That is useful for tests and early UI work, but it means the product is not yet operating on the real World Bank source that the challenge is built around. The next step is to replace the local data path for real runs with live World Bank API ingestion while keeping the product bounded, understandable, and resilient to common data-quality issues.

This PRD covers the live-data layer only. It owns fetching, normalization, verified indicator coverage, historical-window policy, missing-data handling, and partial-success behavior for the six approved indicators across the 15 approved countries. It does not own final live-AI behavior, final cloud scheduling, or deep production hardening. The goal is simple: the same product flow should run on real World Bank data instead of only local fixtures. Exploratory research on other World Bank indicators does not change the approved six-indicator scope unless that change is recorded through an ADR and reflected across planning documents.

This PRD follows the same simplicity rule as the rest of the planning set. The implementation should prefer one clear live fetch path, one normalized internal data shape, and one set of explicit data-quality rules over a broad ingestion framework. A reviewer should be able to see where live data enters the system, how it is cleaned, and how failures are handled without tracing through unnecessary abstraction.

## 2. Goals

### 2.1 Business goals
- Replace the local-only data path with real World Bank API ingestion for the bounded project scope.
- Make the product more credible by grounding dashboard outputs in the real public source named in the challenge brief.
- Keep the data layer understandable enough to explain clearly in review and Q&A.
- Preserve the existing product flow so live data strengthens the system without forcing a frontend redesign.

### 2.2 User goals
- As a reviewer, I want the pipeline to work on real World Bank data so the product feels like a true submission rather than a local simulation.
- As a finance user, I want the dashboard to reflect real indicator history from the selected countries and metrics.
- As an engineer, I want one clear live-data path with predictable normalization and failure handling so the pipeline is easy to maintain.

### 2.3 Non-goals (explicit out-of-scope)
- Replacing deterministic local fixtures for tests and lightweight development.
- Improving the quality of AI narrative generation beyond what the current AI layer already does. That belongs to the live-AI PRD.
- Wiring Cloud Scheduler or Cloud Run Job orchestration. That belongs to the cloud deployment, scheduling, and runtime topology PRD.
- Broadening the scope beyond the approved 15 countries and 6 indicators.
- Building a multi-source ingestion platform or adding alternative economic data providers.
- Deep resilience, load, or security hardening beyond the minimum needed for correct bounded-scope ingestion.

## 3. User personas

### 3.1 Key user types
- ML6 evaluator expecting a real integration with the World Bank API.
- Finance reviewer expecting real macroeconomic signals rather than synthetic data.
- Engineer maintaining the fetch, normalization, and validation path.

### 3.2 Basic persona details
- ML6 evaluator: cares that the system uses the named external data source credibly and handles practical data issues with intent.
- Finance reviewer: cares that the displayed metrics come from a real source and reflect recent historical context, not only one hardcoded country fixture.
- Engineer: needs a bounded and legible data path with clear rules for null values, stale series, deleted indicators, and partial failures.

### 3.3 Role-based access (if applicable)
- No new role model is introduced in this PRD.
- Live data remains an internal pipeline concern surfaced through the same API and frontend flows.
- Cloud operator workflows remain outside the frontend.

## 4. Functional requirements

- **Bounded live source coverage** (Priority: High)
  - The pipeline must fetch live World Bank API data for the approved 15-country, 6-indicator scope.
  - The live indicator list is fixed to the currently approved six verified indicators: `NY.GDP.MKTP.CD`, `NY.GDP.MKTP.KD.ZG`, `FP.CPI.TOTL.ZG`, `SL.UEM.TOTL.ZS`, `BN.CAB.XOKA.GD.ZS`, and `GC.DOD.TOTL.GD.ZS`.
  - Any candidate indicator outside that set is exploratory only until an ADR updates the approved scope.
  - Local fixture mode must remain available for tests and deterministic development, but live mode becomes the default path for real runs.

- **Single normalized internal data shape** (Priority: High)
  - Raw World Bank responses must be normalized into one consistent internal record shape before statistical analysis.
  - The normalized shape must preserve country code, country name, ISO3 where available, indicator code, indicator name, year, and numeric value.
  - Downstream analysis and storage should not need to know whether data came from fixtures or the live API.

- **Historical window policy for analysis** (Priority: High)
  - Live fetching must retrieve a seven-year history window rather than only the latest point.
  - The initial implementation uses `2017:2023` to match the current analysis and fixture baseline. Any later change to that window must be recorded through an ADR (ADR-019).
  - The chosen history window must be stable, documented, and shared across indicators unless there is a clear reason to vary it.
  - The history policy should remain proportionate to the bounded scope and the current analysis design.

- **Data-quality and null-handling rules** (Priority: High)
  - The live-data path must define how to handle null values, missing years, sparse country-indicator coverage, and stale source series.
  - Null values must be filtered out rather than interpolated or treated as zero.
  - Deleted or invalid indicators must fail clearly through tests and runtime validation rather than silently producing empty results.
  - The World Bank API can return HTTP 200 responses that still contain logical API errors in the payload. Those must be detected from the response body, logged with run identifier and indicator code, and surfaced through the pipeline status error summary.
  - The pipeline must filter or flag unusable source rows in a predictable way before analysis.

- **Partial-success execution policy** (Priority: High)
  - A run may succeed partially when some countries or indicators fail, as long as the failure is explicit in logs and status reporting (ADR-020).
  - If at least one country-indicator record is successfully produced but coverage is incomplete, successful outputs must still be preserved while the overall run ends in a terminal `failed` status with explicit incomplete-coverage context.
  - Successful records from a partial run must remain traceable to the same run identifier and source fetch context.
  - The system must not silently treat incomplete live coverage as a full success.

- **Shared live-data path for manual and scheduled runs** (Priority: Medium)
  - Manual trigger and future scheduled execution must use the same fetch and normalization logic.
  - This PRD does not own scheduler wiring, but it must avoid creating separate code paths for manual versus scheduled live data.
  - `pipeline/main.py` remains the shared entry point for both manual and scheduled live-data execution unless a later ADR changes that contract.
  - The data layer should remain usable regardless of which execution model invokes it.

- **Source provenance at fetch time** (Priority: High)
  - The live-data path must capture enough source context to support provenance in later storage and explainability phases.
  - At minimum, the system must preserve source name, indicator code, fetch scope, date range, and source-updated information when available.
  - This PRD owns raw fetch metadata capture. The durable storage PRD owns how that metadata is persisted, linked to raw archives, and surfaced through stored records.
  - Provenance fields should stay light and useful rather than becoming a full source-metadata warehouse.

- **Contract preservation downstream** (Priority: High)
  - Live data integration must feed the existing analysis, storage, API, and frontend flow without requiring a redesign of downstream contracts.
  - The PRD should strengthen the data source while preserving the current product surface as much as possible.
  - Normalized live records must be validated against the current analyser and repository expectations before this PRD can be considered complete.
  - If a contract change becomes necessary, it must be treated as an explicit decision rather than an incidental side effect.

- **Simple, reviewable fetch architecture** (Priority: Medium)
  - The implementation should prefer a small number of clear functions and boundaries over a broad ingestion framework.
  - Country and indicator scope should stay explicit and easy to inspect in code.
  - The data layer should be simple enough that a reviewer can understand it quickly.

## 5. User experience

### 5.1 Entry points and first-time user flow
A reviewer opens the app or triggers a run and sees the same product flow they already understand. The difference is not a new interface. The difference is that the pipeline is now materializing results from the real World Bank source. The user should not need to understand the fetch logic to benefit from it, but the product should be able to explain that it is using real source data.

### 5.2 Core experience
The product continues to fetch, analyze, store, and display economic indicators. With this PRD in place, that loop is grounded in live World Bank data for the full bounded scope instead of only South Africa fixture data. Users should still see the same high-level flow through the dashboard and trigger surface, while engineers gain a clearer live-data path underneath.

### 5.3 Advanced features and edge cases
If some source series are missing recent data, the run should continue where it still can and make the gap explicit. If one indicator fails due to API or validation issues, the system should not discard healthy results from the rest of the scope. If the World Bank API returns null rows or sparse coverage, the normalization layer should handle that deterministically instead of leaking raw source oddities into downstream logic. If the live source changes shape or invalidates an indicator, the failure should be visible and diagnosable.

### 5.4 UI and UX highlights
- No new page is required for this PRD.
- Existing dashboard and trigger flows should continue to work against live-backed results.
- User-visible status and documentation should be able to describe that the source is the live World Bank API.
- Failure communication should favor clarity over false completeness.

## 6. Narrative

World Analyst should analyze the real source it claims to use. This PRD replaces the local-only data path for real runs with a bounded, understandable integration to the World Bank API. It keeps the scope narrow: verified indicators, approved countries, one normalized shape, one clear history policy, and explicit rules for incomplete or imperfect source data. The result is a more credible pipeline without turning the project into a complex ingestion platform.

## 7. Success metrics

### 7.1 User-centric metrics
- A reviewer can trigger or inspect runs that are based on real World Bank data rather than only local fixtures.
- Dashboard outputs for the bounded scope reflect live source history with enough context to support trend and anomaly interpretation.
- Partial source failures are visible and understandable rather than hidden.

### 7.2 Business metrics
- The product demonstrates real integration with the challenge's named external data source.
- The live-data story is simple enough to explain clearly in presentation and Q&A.
- The system remains bounded and credible instead of expanding into a broad ingestion effort.

### 7.3 Technical metrics
- The pipeline can fetch all six approved indicators for the 15 approved countries through the live World Bank API path.
- Normalized records are compatible with the existing analysis and storage flow.
- The history window is sufficient to support current trend and anomaly logic.
- Invalid or deleted indicator configuration fails clearly.
- Partial-success runs preserve successful results and report incomplete coverage explicitly.

## 8. Technical considerations

### 8.1 Integration points
- Live fetch boundary in `pipeline/fetcher.py`.
- Analysis expectations in `pipeline/analyser.py`.
- Current fixture path in `pipeline/local_data.py`.
- Pipeline orchestration in `pipeline/main.py`.
- Existing API contract in `api/openapi.yaml` must remain stable.
- Storage and provenance handoff in `pipeline/storage.py`.
- Shared repository and status behavior defined by adjacent PRDs.
- Project-level indicator and country decisions in `docs/context/world-analyst-project.md`.
- Runtime source selection should remain configuration-driven through `PIPELINE_MODE=local|live`.
- `PIPELINE_MODE` controls the data source only. Storage backend selection remains independent through `REPOSITORY_MODE`, as defined by the durable storage and status PRD.

### 8.2 Data storage and privacy
- The World Bank API is public and requires no authentication.
- This PRD should produce normalized source records and provenance suitable for later archival and persistence work.
- Raw response retention and durable archival remain aligned with the storage PRD rather than being redefined here.
- No additional sensitive user data is introduced by this integration.

### 8.3 Scalability and performance
- The bounded scope remains 15 countries and 6 indicators.
- One API request per indicator remains acceptable at this scale.
- The implementation should respect the public API without adding unnecessary batching complexity beyond what the source already supports.
- The fetch path should continue to use bounded retries and request timeouts rather than introducing complex rate-control infrastructure for the current scope.
- This PRD optimizes for correctness, bounded resilience, and clarity rather than ingestion throughput.

### 8.4 Potential challenges
- Different indicators may have different recency or completeness across countries.
- The World Bank API can return HTTP 200 responses that still contain logical API errors in the payload.
- Sparse or null-heavy series can create misleading downstream calculations if they are not normalized carefully.
- It is easy to let partial coverage look like complete coverage unless status and provenance are explicit.
- The analysis layer may need modest refinement if live data exposes edge cases not present in the local fixture set.

## 9. Milestones and sequencing

### 9.1 Project estimate
This is a medium-sized data-foundation PRD. It is narrower than cloud runtime or full hardening work, but it is substantial because it replaces the source of truth under the whole pipeline and must do so without making the system harder to reason about.

### 9.2 Team size and composition
- One implementation lane covering live fetching, normalization, validation, and pipeline integration.
- One review lane checking indicator validity, data-quality rules, partial-success behavior, and downstream contract stability.

### 9.3 Suggested phases
1. Finalize the approved live indicator list, country list, and historical-window policy.
2. Implement or refine the live fetch path and one normalized internal record shape.
3. Add explicit data-quality rules for nulls, sparse coverage, invalid indicators, and API-level errors.
4. Wire live data into the main pipeline path while retaining local fixtures for tests and deterministic development.
5. Validate partial-success behavior, provenance handoff, and downstream compatibility with analysis and storage.

### 9.4 Dependencies
- Durable storage and status should complete before this PRD so provenance handoff, partial-success behavior, and repository validation can be tested against durable persistence.
- Live AI integration may proceed in parallel, but the final live-AI evaluation gate should run against real live-data inputs rather than only deterministic fixtures.

## 10. User stories

### 10.1 Fetch real World Bank data for the bounded scope
- **ID**: US-1
- **Description**: As an evaluator, I want the pipeline to fetch real World Bank data for the approved countries and indicators so that the product reflects the actual challenge source.
- **Acceptance criteria**:
  - [ ] The live fetch path retrieves the approved six indicators for the approved 15 countries.
  - [ ] Local fixtures remain available for tests, but live data becomes the real-run source.
  - [ ] The indicator and country scope remains explicit and easy to inspect in code.
  - [ ] Scope changes to countries or indicators require an ADR rather than informal exploratory testing.

### 10.2 Normalize live data into one internal shape
- **ID**: US-2
- **Description**: As an engineer, I want live source data normalized into one predictable record shape so that downstream analysis does not need source-specific logic.
- **Acceptance criteria**:
  - [ ] Raw World Bank responses are converted into one normalized internal record structure.
  - [ ] The normalized structure includes country identifiers, indicator identifiers, year, and numeric value.
  - [ ] Analysis code can consume the same shape regardless of whether data came from fixtures or the live API.

### 10.3 Keep enough history for analysis to remain defensible
- **ID**: US-3
- **Description**: As a reviewer, I want the system to fetch enough source history so that trend and anomaly logic are based on more than one recent point.
- **Acceptance criteria**:
  - [ ] The live fetch path uses a documented seven-year historical window rather than only the most recent observation.
  - [ ] The initial implementation uses `2017:2023` unless an ADR updates the approved range (ADR-019).
  - [ ] The history policy is applied consistently unless an explicit exception is documented.

### 10.4 Handle imperfect source data clearly
- **ID**: US-4
- **Description**: As an engineer, I want the system to handle nulls, sparse coverage, and invalid indicators predictably so that source quirks do not silently corrupt downstream output.
- **Acceptance criteria**:
  - [ ] Null or unusable rows are filtered or flagged according to explicit data-quality rules.
  - [ ] Invalid or deleted indicator configuration fails clearly rather than silently returning empty success.
  - [ ] API-level logical errors in otherwise successful HTTP responses are detected from the response body, logged with run identifier and indicator code, and surfaced through the pipeline status error summary.
  - [ ] Null values are filtered rather than interpolated or converted to zero.

### 10.5 Preserve useful output when runs are only partially successful
- **ID**: US-5
- **Description**: As a reviewer, I want partial live-data failures to be visible without discarding successful results so that the product stays useful and honest.
- **Acceptance criteria**:
  - [ ] A run can complete partially when some countries or indicators fail.
  - [ ] Successful records from a partial run are preserved and traceable to the run.
  - [ ] If at least one record succeeds but coverage is incomplete, the run ends in terminal `failed` status while preserving successful outputs.
  - [ ] Status or logging makes the incomplete coverage explicit rather than implying a full success.
