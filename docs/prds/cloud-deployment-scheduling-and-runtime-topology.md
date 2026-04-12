# PRD: Cloud deployment, scheduling, and runtime topology

## 1. Product overview

### 1.1 Document title and version
Cloud deployment, scheduling, and runtime topology
Version: 0.1
Date: 2026-04-10
Status: Draft for approval

### 1.2 Product summary
World Analyst now has a clearer product shape and a stronger storage story, but its runtime model still reflects the local slice. The API currently starts pipeline execution inside the same process, the frontend still assumes local API behavior, and the deployed topology described in the project brief is not yet the system that actually runs.

This PRD moves World Analyst from a local-first execution model to a real GCP runtime topology that matches the challenge brief. The target shape is a React frontend served from Cloud Run, a Connexion API on Cloud Run, and a separate Cloud Run Job that performs the push pipeline on a schedule through Cloud Scheduler or on demand through the trigger endpoint. Firestore and GCS remain the shared state and storage layer. Secret Manager provides runtime secrets. The outcome is not full production hardening yet; it is a truthful, deployable, review-ready cloud architecture with one live demo URL.

## 2. Goals

### 2.1 Business goals
- Meet the challenge requirement that the solution is hosted on GCP and works as a push-based system rather than a pull-on-demand demo.
- Make the deployed runtime match the architecture story used in the review and presentation.
- Separate the dashboard-serving API from the pipeline execution path so the system behaves like a real product, not one long-running web request.
- Unlock one live demo URL that an ML6 reviewer can open without depending on a local machine.

### 2.2 User goals
- As a reviewer, I want one live URL where I can view the dashboard and trigger or observe the pipeline so the system is easy to test.
- As a finance user, I want the deployed dashboard to show the latest persisted insights without depending on someone manually running the app locally.
- As an engineer, I want the API service, frontend service, and pipeline job to have clear boundaries and shared durable state so the architecture is easy to reason about.

### 2.3 Non-goals (explicit out-of-scope)
- Reworking the frontend to match the finalized mockups in detail. That belongs to the frontend-fidelity PRD.
- Rewriting the How It Works narrative or visual explanation layer. That belongs to the How It Works and architecture explainability PRD.
- Replacing the underlying data-fetch or AI-analysis logic. Those belong to the live-data and live-AI PRDs.
- Building a full CI/CD platform, infrastructure-as-code stack, or multi-environment release process.
- Performing deep security testing, resilience drills, load testing, or broad hardening. That belongs to the security, testing, and hardening PRD.
- Adding multi-region deployment, high-availability failover, or multi-run orchestration beyond the current bounded scope.

## 3. User personas

### 3.1 Key user types
- Finance reviewer opening the live dashboard to inspect insights and trigger a run.
- ML6 evaluator assessing whether the system is really cloud-hosted, push-driven, and defensible in architecture discussion.
- Engineer or operator responsible for deploying the services, wiring secrets, and validating runtime behavior.

### 3.2 Basic persona details
- Finance reviewer: expects a working dashboard and does not care whether the system runs on one process or three, as long as the product behaves consistently.
- ML6 evaluator: cares about whether the actual runtime matches the claimed architecture, especially Cloud Run, push scheduling, storage boundaries, and API contract discipline.
- Engineer or operator: needs a clean deployment story, stable configuration, and enough runtime traceability to diagnose failed runs.

### 3.3 Role-based access (if applicable)
- Public access remains limited to the deployed frontend and API surface behind the existing API-key pattern.
- Internal cloud operators may use GCP tools to inspect jobs, logs, Firestore records, and GCS backups.
- No new frontend role model is introduced in this PRD.

## 4. Functional requirements

- **Cloud runtime separation** (Priority: High)
  - The frontend, API, and pipeline execution path must run as separate cloud resources rather than one local process.
  - The deployed API must no longer perform the full pipeline inside its own process when cloud mode is enabled.
  - The pipeline must execute in a dedicated Cloud Run Job runtime.
  - The repo default may remain `"local"` for deterministic development, but every Cloud Run pipeline deployment must set `PIPELINE_MODE=live` explicitly. Deployed services must not rely on the code default.

- **Scheduled push execution** (Priority: High)
  - Cloud Scheduler must trigger the Cloud Run Job on a defined cadence.
  - Scheduled runs must write processed records and pipeline status without requiring any frontend page load.
  - The architecture must remain push-based in line with the challenge brief.
  - The scheduled cadence is monthly (first Monday of each month, 06:00 UTC). World Bank indicator data is published annually, sometimes with a 1–2 year lag, so daily or weekly polling produces only redundant upserts. Monthly is the minimum frequency that keeps the push story honest without wasting quota.
  - The manual trigger via `POST /pipeline/trigger` is the primary mechanism for demonstration and evaluation. The scheduled job exists to satisfy the architectural requirement; the PipelineTrigger page is the centrepiece the reviewer will use during the evaluation session.
  - Firestore upsert semantics make any cadence idempotent: re-running against unchanged source data overwrites records with identical values and advances no state visible to the user.

- **Manual trigger dispatch** (Priority: High)
  - `POST /pipeline/trigger` must dispatch a cloud pipeline run through the Cloud Run Jobs API instead of starting a background thread in the API process when cloud mode is enabled.
  - The trigger endpoint must preserve its current contract shape for the frontend.
  - If a run is already active, the trigger path must return a clear conflict or current-running response rather than silently starting a second run.

- **Idempotent trigger execution** (Priority: High)
  - The API must prevent duplicate manual runs when simultaneous trigger requests arrive.
  - Trigger idempotency must be enforced through a Firestore transaction that checks and updates the current status before dispatch.
  - If the transaction detects an active run, the API must return `409 Conflict` with the current run identifier and start time.

- **Shared durable state across services** (Priority: High)
  - The API service and pipeline job must read from and write to the same Firestore and GCS-backed storage layer.
  - `GET /pipeline/status` must return the durable current status written by the pipeline job.
  - Run identifiers must be consistent across status records, processed records, and cloud logs.

- **Live deployed frontend surface** (Priority: High)
  - A reviewer must be able to open one live dashboard URL.
  - The deployed frontend must communicate with the deployed API using a production-safe base URL pattern.
  - The frontend should default `VITE_API_BASE_URL` to `/api/v1` so browser requests target the same-origin frontend proxy rather than the API origin directly. Override it only if a future deployment topology changes that assumption.
  - The deployed experience must preserve the current route structure even if the visual fidelity is improved later.

- **Runtime configuration and secrets management** (Priority: High)
  - Runtime configuration must be provided through environment variables or equivalent service configuration, not hardcoded values.
  - Secrets such as API keys and model credentials must come from Secret Manager or an equivalent secure runtime path.
  - AI provider credentials are deferred to the live-AI phase. This rollout prepares only the Cloud Run, Firestore, GCS, and shared API-key wiring needed for a truthful cloud deployment story.
  - Service identities must be scoped to the resources they actually use.
  - API, job, and scheduler service accounts must have only the minimum roles needed for their specific duties.

- **Scale-to-zero deployment posture** (Priority: High)
  - Cloud Run services must be deployed with `--min-instances 0` to enable scale-to-zero. The challenge brief names this as an explicit deliverable.
  - The runtime design must avoid always-on infrastructure that is unnecessary for the bounded workload.
  - Acceptance: both the API service and frontend service are deployed with `--min-instances 0` confirmed in the deployment commands.

- **Minimum viable deployment repeatability** (Priority: Medium)
  - The repo must document how to deploy or update the frontend, API service, and pipeline job.
  - The deployment flow may remain manual for this phase as long as it is reviewable and repeatable.
  - The repo must document copy-pasteable deployment commands, the expected runtime resources, regions, and environment variables.

- **Minimum viable cloud observability** (Priority: Medium)
  - Cloud logs must make it possible to trace one pipeline run across trigger dispatch, job execution, storage writes, and terminal status.
  - Logs must include at least a run identifier, service or job context, and terminal outcome.
  - This PRD does not require alerting dashboards, metrics pipelines, or distributed tracing infrastructure.

## 5. User experience

### 5.1 Entry points and first-time user flow
A reviewer opens one live URL and lands on the deployed World Analyst dashboard. The dashboard can read the latest persisted insights from the deployed API. If the reviewer opens the Pipeline Trigger surface, they can start a run or inspect the latest known run state without needing local setup.

### 5.2 Core experience
The user-facing flow should feel familiar: open the dashboard, inspect the latest insights, optionally trigger a run, and watch status progress. The difference is that the runtime is now real. The API is a reader and dispatcher, not the pipeline host. The pipeline work runs in a separate cloud job. Scheduled refreshes happen without the frontend being open.

### 5.3 Advanced features and edge cases
If the frontend is live but the API is misconfigured or unavailable, the failure should be visible rather than silent. If a scheduled or manual run fails, the API should still expose a failed terminal status from durable storage. If the trigger endpoint is called while another run is active, the system should refuse or report that active run clearly. If the API restarts while a job is running, status continuity must come from durable storage rather than process memory.

### 5.4 UI and UX highlights
- No new frontend page is required for this PRD.
- The deployed app must keep the existing route structure and core trigger flow.
- The responsible AI disclaimer remains visible on human-facing surfaces.
- Final visual parity with the design mockups is not owned by this PRD, but the deployed system must support truthful runtime states that those pages can later present.

## 6. Narrative

World Analyst should not claim a cloud architecture that only exists in diagrams. This PRD makes the runtime topology real: a live frontend, a deployed API, a scheduled pipeline job, and a storage layer shared across them. It is the step that turns the product from a strong local prototype into a real challenge submission that can be opened, triggered, and questioned by someone outside the development machine.

## 7. Success metrics

### 7.1 User-centric metrics
- A reviewer can open one live URL and reach the deployed dashboard without local setup.
- A reviewer can trigger a pipeline run from the deployed product surface and observe its status through the API.
- A user can return later and still see the most recent persisted status and outputs after a scheduled or manual run.

### 7.2 Business metrics
- The deployed system matches the challenge brief more closely: hosted on GCP, push-based, durable, and easy to demonstrate.
- The cloud architecture can be explained cleanly in presentation and Q&A without hand-waving around local-only behavior.
- The product is reviewable through one live entry point rather than a collection of local commands.

### 7.3 Technical metrics
- The deployed API runs on Cloud Run and preserves the existing OpenAPI contract.
- Pipeline execution in cloud mode runs through a Cloud Run Job rather than an in-process API thread.
- Cloud Scheduler can launch the pipeline job on a cadence without frontend involvement.
- Secrets are not hardcoded in deployed code or frontend bundles.
- Firestore-backed status remains readable across service restarts.
- Frontend build and deployed API integration work from the live environment.

## 8. Technical considerations

### 8.1 Integration points
- API service entry and middleware in `api/app.py`.
- Trigger and status flow in `api/handlers/pipeline.py`.
- Authentication behavior in `api/handlers/auth.py`.
- API contract in `api/openapi.yaml`.
- Pipeline orchestration in `pipeline/main.py`.
- Storage writes in `pipeline/storage.py` and shared repository adapters.
- Frontend API integration in `frontend/src/api.js`.
- The deployed frontend service is expected to remain nginx-served on Cloud Run. In the deployed build, `VITE_API_BASE_URL` should be `/api/v1`, and that same runtime becomes the proxy mechanism hardened later by the Security, Testing, and Hardening PRD against `${WORLD_ANALYST_API_UPSTREAM}`. That upstream runtime value should include the API service origin plus `/api/v1/` so proxied browser routes map cleanly onto the Connexion base path.
- Deployment documentation and resource explanation in `README.md` and `docs/DECISIONS.md`.
- The durable storage and status PRD must complete its shared repository and durable status contract before this PRD can be implemented safely.
- `pipeline/main.py` remains the job entry point so live data and runtime work share the same execution seam.

### 8.2 Data storage and privacy
- Firestore remains the processed record store shared by the API and the pipeline job.
- GCS remains the raw archival layer.
- Secret Manager should provide runtime secrets such as API keys and model credentials.
- No secret should be embedded in the built frontend assets.
- Public access should be limited to the intended dashboard and API surfaces rather than cloud operator tools.
- API service account should have Firestore access and permission to execute the Cloud Run Job.
- Pipeline job service account should have Firestore, GCS, and Secret Manager access.
- Cloud Scheduler should only have permission to invoke the pipeline job.

### 8.3 Scalability and performance
- The bounded workload remains 17 countries and 6 indicators on a scheduled cadence.
- One Cloud Run Job per scheduled or manual run is acceptable at this scale.
- API autoscaling can remain lightweight because the product is read-heavy and demo-oriented.
- Expected pipeline runtime is measured in minutes, not hours. The initial job configuration should assume a 10-minute timeout, 512MB memory, and 1 vCPU unless implementation evidence requires a change.
  - The scheduled cadence is monthly (first Monday of each month, 06:00 UTC). World Bank data is annual; weekly runs would produce redundant upserts. Monthly balances architectural credibility against API quota.
  - The manual trigger endpoint is the primary demonstration mechanism. Cloud Scheduler provides the push-model evidence the challenge brief requires.
- No VPC or private-networking layer is required for the current challenge scope.
- This PRD optimizes for truthful runtime separation and deployability, not for high-throughput orchestration.

### 8.4 Potential challenges
- Moving from local background-thread execution to cloud dispatch changes control flow and failure modes.
- The API and job must coordinate through durable state rather than shared memory.
- Service-to-service permissions need to be right without becoming overly broad.
- Frontend-to-API integration needs a production-safe base URL story that still works locally.
- Scheduler-triggered runs and manual runs must not create confusing status races.
- Rollback should stay simple: redeploy the previous known-good image revision rather than introducing a release orchestration system.

## 9. Milestones and sequencing

### 9.1 Project estimate
This is a medium-to-large integration PRD. It touches deployment, runtime control flow, cloud permissions, configuration, and operator documentation, but it should still remain narrower than the final hardening phase because it does not own full resilience or release engineering.

### 9.2 Team size and composition
- One implementation lane covering cloud resources, trigger dispatch, runtime config, and deployment wiring.
- One review lane checking contract stability, secret handling, service boundaries, deployment clarity, and ADR alignment.

### 9.3 Suggested phases
1. Finalize the target runtime topology, service boundaries, and configuration matrix.
2. Deploy the API service against durable storage with cloud-safe configuration and authentication.
3. Deploy the pipeline as a Cloud Run Job and redeploy the API service with the updated trigger handler that replaces in-process execution with cloud dispatch.
4. Deploy the frontend against the live API and verify one live dashboard entry point.
5. Add Cloud Scheduler and validate scheduled push execution, run-level logs, and operator steps.
6. Document the deployment and runtime model clearly for reviewers and maintainers.

## 10. User stories

### 10.1 Provide one live dashboard entry point
- **ID**: US-1
- **Description**: As an ML6 reviewer, I want one live dashboard URL so that I can open the product and evaluate it without local setup.
- **Acceptance criteria**:
  - [ ] A public live URL serves the deployed frontend.
  - [ ] The deployed frontend can successfully call the deployed API in its target environment.
  - [ ] The route structure used by the current product remains reachable from the deployed frontend.

### 10.2 Run the pipeline as a real scheduled push job
- **ID**: US-2
- **Description**: As an evaluator, I want the pipeline to run on a cloud schedule so that the architecture matches the brief's push requirement.
- **Acceptance criteria**:
  - [ ] Cloud Scheduler can trigger the Cloud Run Job on a defined schedule.
  - [ ] The scheduled run writes durable status and processed outputs without a frontend request.
  - [ ] Scheduled execution can be explained and demonstrated through the deployed cloud resources.

### 10.3 Dispatch manual runs without in-process API execution
- **ID**: US-3
- **Description**: As a user on the Pipeline Trigger page, I want a manual trigger to start a real cloud pipeline run so that the product demonstrates the actual runtime model rather than a local shortcut.
- **Acceptance criteria**:
  - [ ] In cloud mode, `POST /pipeline/trigger` dispatches a Cloud Run Job execution through the Cloud Run Jobs API rather than starting a background thread in the API service.
  - [ ] Before dispatching, the API uses a Firestore transaction to enforce one active run at a time.
  - [ ] If a run is already active, the trigger path returns `409 Conflict` with the current run identifier and start time.
  - [ ] `GET /pipeline/status` continues to serve the latest durable status contract expected by the frontend.

### 10.4 Keep configuration and secrets out of source code
- **ID**: US-4
- **Description**: As an engineer, I want deployment-time configuration and secret handling so that the live system is secure enough for review and does not depend on hardcoded credentials.
- **Acceptance criteria**:
  - [ ] Runtime configuration is supplied through environment variables or equivalent service configuration.
  - [ ] The deployed frontend uses the same-origin `/api/v1` path by default, with Cloud Run supplying only the nginx upstream and shared proxy key at runtime.
  - [ ] Sensitive values used by cloud services come from Secret Manager or an equivalent secure runtime path.
  - [ ] No sensitive secret is required inside the built frontend bundle.
  - [ ] API, job, and scheduler service accounts have only the minimum roles required for their work.

### 10.5 Trace one run across cloud services
- **ID**: US-5
- **Description**: As an engineer or reviewer, I want one cloud run to be traceable across trigger, job execution, and storage so that failures can be explained.
- **Acceptance criteria**:
  - [ ] Manual and scheduled runs produce logs that include a stable run identifier.
  - [ ] Cloud logs make it possible to connect API trigger activity, job execution, and terminal storage outcome.
  - [ ] Failed runs surface a durable failed status instead of disappearing with a service restart.

### 10.6 Keep deployment repeatable and reviewable
- **ID**: US-6
- **Description**: As an engineer, I want a documented deployment path so that the live system can be reproduced and reviewed without tribal knowledge.
- **Acceptance criteria**:
  - [ ] The repo documents copy-pasteable commands for building and deploying the frontend, API service, pipeline job, and scheduler.
  - [ ] The deployment documentation names the required environment variables, regions, and IAM prerequisites.
  - [ ] The documented flow remains manual but repeatable, without requiring a CI/CD platform.
