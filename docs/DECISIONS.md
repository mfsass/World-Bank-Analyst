# Architecture Decision Record

> A living log of key trade-offs made during development.
> Not for documenting what we built — that's in the code. This is for documenting **why** we made specific choices when reasonable alternatives existed.

---

## ADR-001: Firestore over BigQuery

**Context:** The challenge says "store insights." Both Firestore and BigQuery are GCP-native.

**Decision:** Firestore for processed insights, GCS for raw backup.

**Why:** The data shape is a JSON document per country-indicator pair. Access pattern is key-value lookup (`doc.get()`), not analytical queries. BigQuery's strength (columnar scanning across millions of rows) is irrelevant here — we have ~90 documents refreshed weekly.

**Trade-off:** If analytical queries become a requirement (e.g., "compare GDP trends across all countries over 10 years"), we'd need to migrate. Documented as a future path in `docs/context/world-analyst-project.md`, not a current concern.

---

## ADR-002: Two-Step AI Chain (Not Single-Pass)

**Context:** The LLM could receive all indicator data for a country at once and produce a single report.

**Decision:** Split into two steps: per-indicator analysis → macro synthesis.

**Why:**

1. **Token efficiency.** Each Step 1 call processes ~200 tokens of input. A single-pass call with 6 indicators would need ~1200 tokens of context, increasing the chance of the model conflating unrelated indicators.
2. **Parallelism.** Step 1 calls are independent and can run concurrently. Step 2 must wait but only processes ~6 small JSON objects.
3. **Debuggability.** If the LLM hallucinates a trend, we can trace it to a specific indicator call with a specific input. In single-pass, this would be buried.

**Trade-off:** More API calls = more cost and latency. For 15 countries × 6 indicators = 90 Step 1 calls + 15 Step 2 calls = 105 total. At Gemini Flash pricing, this is affordable. If costs matter, batch or reduce country count.

---

## ADR-003: Schema-Constrained Output (Not Prompt-Based JSON)

**Context:** Early prompts used "Return valid JSON only. No markdown formatting." to enforce structure.

**Decision:** Removed all prompt-based JSON enforcement. Use `response_json_schema` (Gemini) and `response_format` with `strict: true` (OpenAI).

**Why:** Prompt-based JSON enforcement is unreliable. It works 90% of the time, then produces `\`\`\`json\n{...}\`\`\`` wrapped output or drops required fields in production. Schema-constrained output is enforced at the token level — invalid JSON is structurally impossible.

**Trade-off:** Requires using Pydantic to define output schemas upfront. This is effort, but it's the right kind of effort — the schema is now the spec, living in code, versioned, and testable.

---

## ADR-004: Connexion over FastAPI

**Context:** FastAPI is the default choice for Python APIs. Connexion is less common.

**Decision:** Connexion.

**Why:** The challenge values spec-driven development. Connexion reads `openapi.yaml` and generates routes. FastAPI generates a spec from code. With Connexion, the spec is the source of truth. With FastAPI, the code is. For a project demonstrating engineering rigor, the spec should come first.

**Trade-off:** Connexion has a smaller community and fewer tutorials. FastAPI has better async support and more middleware options. For this project's scale (4 endpoints), Connexion's trade-offs don't hurt.

---

## ADR-005: Vanilla CSS over Tailwind

**Context:** Tailwind is the standard for rapid UI development.

**Decision:** Vanilla CSS with CSS custom properties.

**Why:** The design system defines explicit tokens (exact hex values, exact spacing, exact typography). Tailwind's utility classes would abstract these away behind `bg-gray-900` instead of `var(--surface-card)`. When the reviewer opens `index.css`, they see the entire design system in one file, exactly as specified. No build tooling, no config, no class name abstraction layer.

**Trade-off:** More CSS to write manually. Slower for rapid prototyping. Worth it for clarity and auditability.

---

## ADR-006: 15 Countries, Not All Countries

**Context:** The World Bank API has data for 200+ countries.

**Status:** Superseded by ADR-041 for the active live monitored-set scope.

**Decision:** Analyse 15 countries spanning 6 regions and multiple income levels.

**Why:** Processing 200 countries × 6 indicators = 1200 API calls + 1200 LLM calls per run. At ~$0.01/call, that's $12 per refresh. 15 countries keeps each run under $2 while covering representative diversity (ZA, NG, KE, EG, US, BR, MX, DE, GB, FR, CN, IN, JP, ID, AU).

**Trade-off:** Users can't look up arbitrary countries. Mitigated by choosing economically diverse representatives and documenting the selection rationale.

---

## ADR-007: Lean Copilot Baseline Over Broader Global Instructions

**Context:** The repo already had strong always-on context in `GEMINI.md`, `AGENTS.md`, and `.github/copilot-instructions.md`, but it lacked reusable AI workflow assets for planning, implementation, review, and file-specific guidance.

**Decision:** Keep the global instruction layer as-is and add a lean Copilot baseline made of scoped `.instructions.md` files, custom agents, prompt files, planning scaffolds, and extension recommendations.

**Why:** This keeps common project rules centralized while loading extra guidance only when relevant files or workflows are in scope. It improves repeatability for plan → implement → review without bloating every chat request with more global prose.

**Trade-off:** The repo now has more AI customization files to maintain. We accept that overhead because each file has a narrow purpose and can be pruned independently if it stops paying for itself.

**Date:** 2026-04-08

---

## ADR-008: Finance-First, Presentation-Scoped Dashboard

**Context:** The challenge leaves room to build for a broad business audience, design for machine-readable downstream consumers, or over-engineer for future scale. The clarified target is narrower: a finance team using the dashboard as a decision surface during a weekend challenge demo.

**Status:** Active except for the monitored-country count, which is superseded by ADR-041 for the active live monitored-set scope.

**Decision:** Optimize the product for finance users, a weekend-sized implementation, and human-readable dashboard output. Lead KPI and narrative design with risk-weighted signals, keep scope fixed around 15 countries and 6 indicators, and prioritize a reliable Pipeline Trigger demo over speculative scale work.

**Why:** Finance users do not need indicator definitions; they need risk framing, trend magnitude, and anomaly context. A weekend challenge rewards scope discipline more than infrastructure ambition. Because a human reads and acts on the output, richer analyst prose is more valuable than exhaustive machine-oriented schemas except where the frontend needs structured fields.

**Trade-off:** The system is less suited to generic audiences, downstream integrations, and near-term scale expansion. We accept that constraint because the evaluation criteria favor a clear, defensible demo and financially literate narrative over breadth.

**Date:** 2026-04-08

---

## ADR-009: Local-First Vertical Slice with Mixed Insights Documents

**Context:** The repo already defines the target product shape, but implementation is still scaffold-heavy. Before wiring Firestore, GCS, Cloud Run Jobs, and live LLM calls, the team needs a credible end-to-end slice that proves the Pipeline Trigger flow and country-level intelligence output. At the same time, the product constraint remains one Firestore collection, while the API contract requires multiple logical entities: indicator insights, country synthesis, and pipeline status.

**Decision:** Build the first milestone as a one-country, local-first vertical slice. Use a deterministic AI fallback for development, keep pipeline status ephemeral in memory for the first milestone, and shape the storage contract around one `insights` collection with mixed document types such as `indicator`, `country`, and `pipeline_status`.

**Why:** This sequence validates the trigger and country-briefing flow without depending on GCP services or live LLM behavior. A local slice is faster to debug and easier to test. Mixed document types keep one collection while still supporting both per-indicator and per-country API responses.

**Trade-off:** The first slice is not production-grade. Status disappears on restart, deterministic AI is not the final narrative layer, and execution still runs in-process. We accept that because it reduces early integration risk and keeps the path to Firestore and real LLMs straightforward.

**Date:** 2026-04-08

---

## ADR-010: In-Process Trigger Execution for the Local Slice

**Context:** The first slice needs to expose `POST /pipeline/trigger` and `GET /pipeline/status` before Cloud Run Job dispatch exists. The user flow depends on seeing a status transition from idle to running to complete and then opening the materialised ZA country briefing.

**Decision:** Execute the first-slice pipeline inside the API process on a background thread, while persisting the latest pipeline status in the shared in-memory repository used by both the API and the pipeline.

**Why:** This keeps the trigger and polling flow end to end without introducing GCP job orchestration yet. It also ensures the same mixed-document contract is exercised immediately by both write and read paths, which is the real product risk for the first slice.

**Trade-off:** This is only appropriate for a single-process local demo. Status disappears on restart, concurrency guarantees are minimal, and the execution model does not match the eventual Cloud Run Job deployment topology. We accept those constraints because they keep the first slice focused on product contract validation rather than infrastructure wiring.

**Date:** 2026-04-08

---

## ADR-011: Complete the Landing Dashboard Before Infrastructure Hardening

**Context:** After the first local slice, the repo has a working trigger, status feed, and `ZA` country briefing backed by the shared in-memory repository. The viable next directions are to integrate the Global Overview page, replace the repository with Firestore, harden Cloud Run Job execution, wire a real LLM provider, or complete the How It Works page.

**Decision:** Make Global Overview integration the next implementation phase, using the existing API boundaries and current local slice data wherever possible.

**Why:** The landing page is still placeholder content, so finishing it increases demo value immediately. It extends current API and frontend boundaries instead of switching storage, job orchestration, or model providers too early.

**Trade-off:** Firestore realism, Cloud Run Job parity, and live-provider narrative quality are deferred by one phase, so the system stays locally anchored a bit longer. We accept that because a working dashboard matters more at that point than backend hardening.

**Date:** 2026-04-08

---

## ADR-012: Derive Overview Coverage from Country Briefings, Not Indicator Presence

**Context:** The Global Overview page needs to report how many monitored countries have a live briefing. The current API surface exposes country metadata at `GET /countries`, raw indicator insight rows at `GET /indicators`, and full briefing existence only at `GET /countries/{country_code}`. Indicator presence alone can overstate coverage because a country may have indicator records without a materialised macro synthesis, outlook, and risk flags.

**Decision:** For the current local slice, derive coverage by fetching country detail for each monitored country and counting only successful briefing payloads. Treat `404` as "not materialised yet" and use those detail responses as the source of truth for overview coverage and featured-country availability.

**Why:** This keeps the overview aligned with the actual product promise of a finance-ready country briefing without expanding the backend contract during the landing-dashboard phase. It preserves the approved plan's bias toward minimal reuse of the existing API while fixing a user-visible semantic bug in the coverage KPI.

**Trade-off:** The landing page fans out to per-country endpoints instead of using a summary payload. At 15 countries, the extra calls are acceptable. If the monitored set grows or latency becomes material, add a `has_briefing` field to `GET /countries`.

**Date:** 2026-04-08

---

## ADR-013: Gated Dual-Lane Agent Delivery for Substantive Changes

**Context:** The repo already had dedicated planner, implementer, and reviewer agents, but the default workflow was still mostly sequential. The next question was whether to force a two-agent pattern on every implementation task so one lane executes while another independently audits drift and quality.

**Decision:** Use a dual-lane workflow by default for substantive implementation tasks, with the main conversation coordinating one implementation lane and one independent review lane in parallel. Gate the pattern off for trivial, read-only, or purely mechanical work.

**Why:** This repo has clear drift risks that benefit from independent review: OpenAPI versus handler drift, design-system drift, missing ADR updates, and weak validation on a weekend-scale build. External guidance also points to the same shape: keep specialists narrow, keep the manager owning the final synthesis, prefer model diversity for grading or review when available, and add extra agents only when they materially improve isolation or auditability. Running the reviewer in parallel catches likely failure modes earlier without waiting until the end of the task.

**Trade-off:** The workflow adds latency, more prompts, and another source of false positives. If applied indiscriminately it would slow down trivial work and burn context for little gain. We accept the added complexity only for substantive tasks where the extra audit surface is worth the cost.

**Date:** 2026-04-08

---

## ADR-014: Production-Grade Delivery Standard Over Weekend Framing

**Context:** The repo originated in a challenge setting, but active instructions still described it as a weekend build. That framing started to justify thin inline documentation, demo-only shortcuts, and prose that sounded assembled rather than deliberate.

**Status:** Active except for the monitored-country count, which is superseded by ADR-041 for the active live monitored-set scope.

**Decision:** Keep the product scope guardrails fixed at 15 countries, 6 indicators, one Cloud Run job, one Firestore collection, and one live demo URL, but remove weekend framing from active instructions. Treat the repo as production-grade in code quality, inline documentation, validation, and decision logging. Require docstrings plus targeted inline comments for non-obvious business rules, orchestration, and state transitions.

**Why:** The project now needs to stand up in review, presentation, and handover without hidden chat context. Reviewers should be able to understand both the implementation and the trade-offs directly from the repo. Scope discipline still matters, but describing the work as a weekend project biases decisions toward shortcuts when the real requirement is defensible quality.

**Trade-off:** The higher bar adds documentation and review overhead, and it slows delivery slightly compared with a demo-only mindset. We accept that because it reduces ambiguity and improves maintainability.

**Date:** 2026-04-09

---

## ADR-015: Project-Specific Humanized Writing Standard

**Context:** ADRs, README text, presentation copy, and user-facing narrative are now part of the product quality bar. Generic AI phrasing weakens trust, especially when the audience is finance-literate and expects direct language.

**Decision:** Add a project-specific writing skill that favors specific, direct, human-sounding language for ADRs, reports, presentation copy, user-facing narrative, and other important prose. Use placeholders instead of invented specifics, and apply the same standard to explanatory comments when they risk sounding formulaic.

**Why:** Readable writing makes decisions easier to quote and easier to review. It also improves analyst-facing and stakeholder-facing content.

**Trade-off:** The writing standard adds another skill file and another review lens for docs and prose-heavy changes. We accept that maintenance cost because the alternative is bland or inflated wording that undermines otherwise solid engineering work.

**Date:** 2026-04-09

---

## ADR-016: Durable Mixed-Document Repository Behind a Stable API Contract

**Context:** The local slice uses an in-memory repository, which breaks across service boundaries or after restart. The frontend contract is already stable and should not expand just to swap storage.

**Decision:** Introduce a shared repository contract with backend selection, keep the existing in-memory repository for tests and deterministic local runs, and add a Firestore-backed mixed-document adapter for indicator, country, and pipeline-status records. Preserve the current API response shapes and status payload so the frontend can keep polling the same endpoints without contract changes.

**Why:** This moves the system off process-local state while keeping the product surface stable. Firestore matches the current mixed-document model, lets the API and pipeline share durable state across service boundaries, and creates a clean seam for the next phase of execution hardening. Keeping the frontend contract stable limits risk to the storage boundary instead of combining storage and UI churn in one step.

**Trade-off:** Repository hardening adds durable state but does not make execution durable yet, because trigger still runs in-process until Cloud Run Job dispatch exists. Firestore collection scans remain acceptable at current scale.

**Date:** 2026-04-09

---

## ADR-017: Clarification-First Planning and PRD Agents

**Context:** Planner-style workflows were starting from short or ambiguous briefs, which made it too easy to produce plans that guessed at scope, acceptance criteria, or user intent. VS Code custom agents and prompt files can explicitly scope which tools are available, including the native clarification tool.

**Decision:** Give the workspace planner and PRD customizations explicit access to `vscode/askQuestions` alongside read-only research tools, and instruct them to pause for clarification when the brief is materially underspecified.

**Why:** This makes clarification explicit instead of optional. It also keeps planning agents read-oriented: they can inspect the repo, check the web when needed, and ask targeted questions without carrying edit or terminal privileges they do not need.

**Trade-off:** Planning flows now add a small amount of up-front friction when a request is vague, and this only covers workspace custom planner and PRD paths rather than changing any built-in VS Code agents directly. We accept that because the alternative is faster but weaker planning built on preventable assumptions.

**Date:** 2026-04-09

---

## ADR-018: Storage Hardening After the Landing Dashboard Baseline

**Context:** ADR-011 deferred storage hardening until the landing dashboard baseline existed. That baseline now exists well enough to justify moving durability work ahead of further expansion.

**Decision:** Treat durable storage as the next foundational backend phase after the landing dashboard baseline, with cloud runtime wiring still deferred to its own PRD.

**Why:** The product now needs durable state and raw-data persistence to remain defensible in review. Storage hardening is the smallest backend change that materially improves product credibility without yet forcing cloud job orchestration.

**Trade-off:** This shifts work earlier than ADR-011 originally implied. We accept that because the repo now has enough frontend shape to benefit from durable state, while runtime wiring remains separately scoped.

**Date:** 2026-04-10

---

## ADR-019: Seven-Year Historical Window for Live Indicator Analysis

**Context:** Live data integration needs a stable history window that supports current trend and anomaly logic without turning the fetch layer into a larger analytics system.

**Status:** Superseded by ADR-041 for the active live monitored-set scope.

**Decision:** Use a seven-year history window. The initial implementation uses `2017:2023` for all approved indicators.

**Why:** The current analysis logic compares year-over-year movement and needs more than one recent point. Seven years is enough to show medium-term direction without adding much extra fetch or storage cost, and it matches the existing fixture baseline.

**Trade-off:** Very long-term structural context stays out of scope. We accept that because the current product is built for recent risk signals, not decade-scale economic research.

**Date:** 2026-04-10

---

## ADR-020A: Curated Repository Baseline Over Code-Only Import

**Context:** The project had already accumulated product code, PRDs, design mockups, and AI workflow assets before git initialization. The repo now needs to serve as a technical interview artifact, not just a place to store source files.

**Decision:** Initialize the repository around a curated baseline that keeps runtime code, design and planning context, and AI workflow assets in version control, while excluding machine-local state, secrets, caches, and generated output. Split the first history into hygiene, workflow documentation, and baseline import.

**Why:** This project is being evaluated partly on how clearly it explains intent and uses AI with discipline. A code-only import would hide the spec-first, test-driven, ADR-backed working method that the demo is meant to show. See `README.md`, `CONTRIBUTING.md`, and `.gitignore`.

**Trade-off:** The repository is broader than a minimal application repo and includes more non-runtime material to maintain. We accept that because the paper trail is part of the deliverable and improves reviewability.

**Date:** 2026-04-11

---

## ADR-020: Partial-Success Live Runs Preserve Good Data

**Context:** The World Bank API can return sparse or incomplete coverage. The system needed a decision on whether one failure should invalidate a whole run.

**Decision:** Preserve successful outputs from a partially successful live-data run, but keep the overall pipeline status terminal state as `failed` when coverage is incomplete.

**Why:** Throwing away valid data because one country or indicator fails would make the product less useful. Keeping the terminal state as `failed` preserves honesty and avoids expanding the current status contract with a new enum before the product needs it.

**Trade-off:** The dashboard may show partially refreshed data after a failed run. We accept that because the alternative is losing all valid outputs, and the incomplete coverage remains visible through status and logs.

**Date:** 2026-04-10

---

## ADR-021: Cloud Run Jobs API for Manual Pipeline Dispatch

**Context:** Once the API stops running the pipeline in-process, `POST /pipeline/trigger` still needs a concrete way to start a run remotely.

**Decision:** Use the Cloud Run Jobs API to execute the pipeline job from the API service.

**Why:** It keeps the runtime model direct and reviewable: the API dispatches one job execution and gets immediate success or failure feedback from the platform. It also fits the product's scale-to-zero posture better than adding another queueing system just for the challenge.

**Trade-off:** The API service account needs permission to execute the job. We accept that because the IAM scope is still narrow and the dispatch path stays easy to explain.

**Date:** 2026-04-10

---

## ADR-022: Firestore Transaction for Trigger Idempotency

**Context:** The trigger endpoint must prevent duplicate runs when multiple requests arrive at nearly the same time.

**Decision:** Use a Firestore transaction to check the current pipeline status and claim the next run before dispatching the Cloud Run Job.

**Why:** The product already depends on Firestore-backed current status. Using the same durable state for idempotency avoids adding a second coordination mechanism and keeps the behavior correct across stateless API instances.

**Trade-off:** Trigger handling gains a small amount of latency and a little more transactional code. We accept that because duplicate job execution would be harder to explain and recover from than the extra complexity.

**Date:** 2026-04-10

---

## ADR-023: Build-Time API Base URL Injection for the Frontend

**Context:** The deployed frontend needs to know which API origin to call without shipping a hardcoded development URL.

**Decision:** Inject `VITE_API_BASE_URL` into the frontend build at build time.

**Why:** This is the simplest Vite-native way to keep the built bundle environment-specific without adding runtime config fetching. It also keeps local development straightforward while making the deployed bundle explicit about which API it targets.

**Trade-off:** Different environments require separate builds. We accept that because the project has one primary deployed environment and does not need a more complex config service.

**Date:** 2026-04-10

---

## ADR-024: Weekly Monday 06:00 UTC Scheduler Cadence

**Context:** The push architecture needed one explicit refresh cadence for scheduled runs.

**Decision:** Run the pipeline weekly at 06:00 UTC every Monday.

**Why:** World Bank indicator coverage does not change frequently enough to justify daily refresh. Weekly cadence is enough to demonstrate the push model, keep cloud costs near zero, and avoid pretending the product has a higher-frequency source than it really does.

**Trade-off:** The dashboard can lag a source update by a few days. We accept that because the source itself is not real-time, and the product's credibility depends more on honest cadence than on artificial frequency.

**Date:** 2026-04-10

---

## ADR-025: Run-Scoped Raw Archive Paths in GCS

**Context:** Durable storage requires raw World Bank payloads to be discoverable later without guessing which archive belongs to which run.

**Decision:** Store raw payloads under a run-scoped path template such as `runs/{run_id}/raw/{indicator_code}.json`.

**Why:** A run-scoped path is easy for reviewers and operators to inspect manually, and it ties the raw archive structure directly to the provenance model used by stored records.

**Trade-off:** One file per indicator creates more small objects than a batched archive. We accept that because the object count stays trivial at the current scope and the structure is clearer to inspect.

**Date:** 2026-04-10

---

## ADR-026: Economy-First Live AI Baseline with Gemma 4

**Context:** Live AI integration needs a real default provider and model, but the project should not lock itself into a higher-cost proprietary option before testing whether a cheaper baseline is already good enough.

**Decision:** Start live AI with Google GenAI using `gemma-4-31b-it` as the default baseline candidate, and only promote one or both AI steps to a stronger model when evaluation evidence shows the baseline is not good enough.

**Why:** This keeps cost discipline inside the design from the start, uses a real provider-backed model, and forces model upgrades to be evidence-based rather than preference-based.

**Trade-off:** The cheapest baseline may prove weaker on structured reliability or macro synthesis quality, so the implementation must carry an explicit evaluation gate and a clean upgrade path.

**Date:** 2026-04-10

---

## ADR-027: Exact-Input AI Reuse Over a Standalone Cache Layer

**Context:** The bounded weekly pipeline should minimize repeat AI cost, but adding a separate semantic cache or cache service would create more architecture than the current scope needs.

**Decision:** Reuse prior AI outputs only when the effective AI input matches exactly by fingerprint across normalized input content, step name, prompt version, provider, and model.

**Why:** Exact-match reuse is cheap, safe, and easy to explain. It lowers repeat cost without introducing a second platform concern.

**Trade-off:** Small input or prompt changes invalidate reuse, and the system gives up more aggressive cache-hit behavior. We accept that because correctness and auditability matter more than maximizing reuse.

**Date:** 2026-04-10

---

## ADR-028: `europe-west1` as the Deployment Region

**Context:** The deployed system needs one default GCP region for Cloud Run services, Cloud Run Jobs, Firestore access patterns, and the demo environment.

**Decision:** Use `europe-west1` as the default deployment region.

**Why:** It aligns with ML6's Belgian home market, keeps the demo story regionally coherent, and is easy to justify in presentation and review.

**Trade-off:** This is a presentation- and operations-friendly default, not a latency-optimized answer for every future user. We accept that because the project has one primary demo environment and does not need multi-region complexity.

**Date:** 2026-04-10

---

## ADR-029: Server-Side Frontend Proxy Over Browser-Held API Key

**Context:** The current local frontend sends `X-API-Key` directly from browser-side JavaScript. That is acceptable for local development but not for the deployed demo, because any production browser-held shared secret is exposed immediately in the bundle or network traffic.

**Decision:** Keep the API's header-based auth scheme, but move production secret handling behind the frontend runtime. The deployed frontend will call the API through a same-origin `/api/v1` proxy path, and that proxy will inject `X-API-Key` server-side.

**Why:** This keeps one live dashboard URL, avoids shipping the API secret to the browser, and stays much simpler than introducing OAuth or a user-account system for a bounded challenge demo. It also preserves the existing API contract and auth scheme instead of changing multiple layers at once. Deployed frontend builds can point `VITE_API_BASE_URL` at `/api/v1`, while the frontend runtime forwards that path to the API service internally.

**Trade-off:** The frontend deployment gains proxy configuration and an extra request hop. The API still uses a shared secret rather than per-user auth. We accept that because it closes the most obvious trust gap without adding infrastructure the product does not need.

**Date:** 2026-04-10

---

## ADR-030: Public Repo Curation Over Raw Interview Prep

**Context:** The repo started to accumulate design assets, planning notes, employer research, and workflow scaffolding in a way that was useful locally but cluttered the public-facing root and exposed prep material that did not strengthen the engineering story.

**Decision:** Curate the repo around product code, public docs, and repo-owned workflow guidance. Move design and architecture context under `docs/`, replace loose root planning files with repo-backed plan documents, and keep employer-specific research in ignored local files instead of tracked markdown.

**Why:** The repo needs to read as a deliberate engineering artifact, not a working folder. Reviewers should be able to find the design system, product brief, ADRs, and plans quickly without wading through candidate-prep material or stale scratch files.

**Trade-off:** Some local research stays outside version control, and a few paths become longer because they now sit under `docs/`. We accept that because the cleaner public surface is easier to review and easier to defend.

**Date:** 2026-04-11

---

## ADR-031: Local Raw Archive Adapter Behind the Same Run-Scoped Contract

**Context:** Durable storage now needs raw-data archival linkage before processed records are persisted. In production that archive belongs in GCS, but the current local slice and tests still need to run without cloud credentials or a fake GCS stack.

**Decision:** Keep one run-scoped raw archive contract and back it with two implementations: local filesystem storage for development and tests, and GCS for deployed environments. Persist only the stable archive reference in stored records, not the raw payload itself.

**Why:** This keeps the storage flow honest to the target architecture without making local validation depend on cloud setup. The same run id and relative archive paths work in both modes, so tests can prove archival linkage and provenance using the same record shape that production will use.

**Trade-off:** Local development does not exercise real GCS permissions or object-store behavior. We accept that because the bounded goal in this phase is the contract between archival and processed persistence, not full cloud runtime parity.

**Date:** 2026-04-11

---

## ADR-032: Persist Provenance Privately While Standardizing on REPOSITORY_MODE

**Context:** Durable storage needs to persist run ids, raw archive references, source provenance, and minimal AI provenance. The approved scope also keeps the current frontend contract stable. At the same time, repo docs already describe `REPOSITORY_MODE`, while the runtime selector still used `WORLD_ANALYST_STORAGE_BACKEND`.

**Decision:** Persist provenance and richer status detail in stored mixed documents, but project API reads back to the existing public response shapes. Standardize runtime configuration on `REPOSITORY_MODE=local|firestore` and keep `WORLD_ANALYST_STORAGE_BACKEND` only as a backward-compatible alias.

**Why:** This keeps the durable record contract truthful and reviewable without turning storage hardening into an API redesign. It also removes a real code-versus-doc drift point at the exact boundary this phase is hardening.

**Trade-off:** Reviewers need Firestore inspection or repository-level tests to see the new provenance fields, because the API does not expose them yet. The repository layer also picks up a small projection and config-compatibility branch. We accept that because preserving the current product surface is more valuable in this phase than expanding the contract.

**Date:** 2026-04-11

---

## ADR-033: Frontend Fidelity Keeps the Current API Boundary

**Context:** The frontend-fidelity PRD needs to make the product look much closer to the finalized mockups, but the current API does not yet expose truthful data for every visual surface those mockups imply. The main alternatives were to expand the API now to satisfy overview maps, regional rollups, chart history, and architecture telemetry, or to keep the current API boundary and treat those richer surfaces as explicitly representative until later PRDs land.

**Decision:** Keep the existing API boundary for the frontend-fidelity phase and implement richer non-live surfaces as clearly labeled representative UI shells rather than forcing backend contract changes for visual convenience.

**Why:** This keeps the phase aligned with the approved implementation order, preserves spec-driven discipline, and avoids mixing a large UI refactor with new contract work that belongs to later live-data, live-AI, or architecture-explainability phases. It also keeps the product honest: overview maps, regional summaries, country charts, and architecture telemetry can exist structurally now without pretending the backend already provides those exact live values.

**Trade-off:** Some surfaces in this pass are less dynamic than the final product shape and need explicit labeling so reviewers can distinguish live state from representative structure. We accept that because the alternative would widen scope, blur PRD boundaries, and risk shipping visual polish backed by invented or weakly supported data.

**Date:** 2026-04-11

---

## ADR-034: Unified Navigation Rail and Strict Utility Pruning

**Context:** The application previously had both a top-nav bar for main links and a side rail mirroring those same links, along with placeholder "Export" and "Documentation" buttons yielding alerts. This violated the single-navigation HIG patterns, created layout bugs (hiding the main content), and presented dead features in production.

**Decision:** Consolidate navigation entirely to the side rail. Remove duplicate top-bar links. Strictly remove any placeholder buttons (Export, Documentation, Settings, Notifications) that do not have explicitly modeled behaviors in the PRD.

**Why:** Duplicate navigation hierarchies confuse users and clutter the interface. "Apple-like" and professional UX demands a single clear structural hierarchy. Furthermore, shipping dead buttons (even with "coming soon" alerts) undermines trust and interface integrity, violating core UX/UI principles.

**Trade-off:** If future requirements introduce dense secondary utilities, they must be explicitly planned in the PRD rather than living as permanent UI stubs.

**Date:** 2026-04-11

---

## ADR-035: Single Top Navigation and Summary-First Country Drill-In

**Context:** ADR-034 pushed the app toward a side-rail-only shell, but the implemented product and latest frontend direction now favor one clear global navigation layer. The overview map also needed a faster way to move from point selection to country context without forcing reviewers to hunt for a separate detail path in `frontend/src/pages/GlobalOverview.jsx` and `frontend/src/pages/CountryIntelligence.jsx`.

**Decision:** Keep one shared top navigation plus footer, drop the desktop side rail from the frontend-fidelity requirement, use click-driven map popovers as the overview drill-in pattern, and surface the country AI briefing above the deeper signal pack.

**Why:** Four primary routes do not justify two structural navigation systems. A single top nav is cleaner on desktop, collapses more predictably on smaller screens, and removes duplicate active-state logic. Map popovers give quick context in place, and the elevated country briefing puts the main analyst takeaway before the lower-level indicator cards.

**Trade-off:** We give up the denser always-visible side rail and stop reserving country-page real estate for a placeholder chart region in this phase. We accept that because the current product benefits more from a clear drill-in flow and stronger narrative hierarchy than from extra chrome or empty visual slots.

**Date:** 2026-04-11

---

## ADR-036: ZA-First Live Extraction Before the Monitored-Set Rollout

**Context:** The live-data PRD targets the approved 15-country monitored set, but the current shared repository metadata and stored country contract still materialize only `ZA`. Expanding fetch scope, repository metadata, overview coverage, and API-facing country parity in one pass would bundle several unrelated risks into the same backend change.

**Status:** Superseded by ADR-041 for the active live monitored-set scope.

**Decision:** Make `PIPELINE_MODE=live` real now for the existing South Africa slice only. Keep the live fetch scope fixed to the approved six indicators and the seven-year `2017:2023` window, preserve deterministic `local` mode for tests and development, and defer the monitored-country catalog rollout to its own follow-on change.

**Why:** The immediate credibility gap is that the pipeline still always loads fixtures even when a live mode is requested. Hardening one real country end to end lets the repo prove the important pieces now: payload-level API error handling, null filtering, stable normalized records, and raw request-response archival with provenance.

**Trade-off:** Live mode becomes honest for one country before it becomes representative of the full monitored set. We accept that temporary asymmetry because it isolates the fetch hardening work from broader catalog and contract changes, and it gives the later rollout a proven live-data seam instead of another combined migration.

**Date:** 2026-04-11

---

## ADR-037: Canonicalize the ML6-Market 15-Country Set

**Context:** ADR-006 still showed an older example list even though the product brief and live fetcher had already converged on a different 15-country monitored set. The backend rollout now needs one country catalog that drives fetch scope, repository metadata, and the API country listing.

**Status:** Superseded by ADR-041 for the active live monitored-set scope.

**Decision:** Treat the ML6-market set already used in the product brief and `pipeline/fetcher.py` as canonical: BE, NL, DE, GB, FR, US, BR, CA, CN, JP, IN, AU, ZA, NG, EG. Use that set as the shared source of truth for monitored-country metadata and live fetch scope.

**Why:** This is the list already reflected in the product brief and live-data seam, so adopting it avoids reopening country-selection scope during backend rollout. It also keeps `GET /countries`, repository metadata, and `PIPELINE_MODE=live` aligned instead of maintaining competing examples.

**Trade-off:** ADR-006's older country example becomes historical context rather than an active source of truth. Future country-set changes now need to update the shared catalog and ADR log together instead of being implied by one illustrative example.

**Date:** 2026-04-11

---

## ADR-038: Keep One Canonical World Bank API Reference

**Context:** The repo had two substantial World Bank API references: the agent-facing skill in `.github/skills/world-bank-api/SKILL.md` and a private-context copy in `private-context/WORLDBANK_API_SKILL.md`. That duplication created a predictable drift risk just as the team was re-validating the official API semantics against the World Bank documentation and live production responses.

**Decision:** Treat `.github/skills/world-bank-api/SKILL.md` as the canonical World Bank API reference for the repo. Keep `private-context/WORLDBANK_API_SKILL.md` only as a short repo-specific usage note that points back to the canonical skill.

**Why:** The skill file is the artifact already wired into the repo's agent instructions, implementation guidance, and pipeline fetcher comments. Making it the single authoritative reference removes ambiguity, keeps official API semantics in one maintained place, and lets the private-context file focus on how World Analyst should use the API rather than trying to restate the entire surface area.

**Trade-off:** The private-context note is no longer a standalone API reference. We accept that because the alternative is maintaining two competing documents and slowly reintroducing the same uncertainty we just resolved.

**Date:** 2026-04-11

---

## ADR-039: Pin Live World Bank Fetches to WDI and Fail Loudly on Scope Drift

**Context:** A deeper audit of the official World Bank API docs and live production responses showed three things that the existing fetcher was handling too loosely. First, the monitored indicators belong to World Development Indicators (`source=2`), and the simple country-indicator endpoint accepts that source pin directly. Second, the public endpoint can be materially slower than the earlier hard-coded 15-second timeout assumption. Third, the current monitored scope fits inside one `per_page=1000` response, but the fetcher was only safe by accident because it never checked whether a future scope expansion had started returning multiple pages.

**Decision:** Refine the live World Bank runtime contract in three ways. Pin monitored indicator requests explicitly to `source=2`, make the request timeout configurable through `WORLD_ANALYST_WORLD_BANK_TIMEOUT_SECONDS` with a higher default, and fail the fetch step explicitly when an indicator response spans more than one page instead of silently truncating page 1.

**Why:** The source pin removes ambiguity if an indicator code exists in multiple catalogs. The timeout knob reflects real public-endpoint behavior without turning the fetch path into a bigger rate-control system. The multi-page guard keeps the pipeline honest: if the bounded scope ever stops fitting in one response page, the run should fail clearly rather than archive incomplete source data and pretend the fetch succeeded.

**Trade-off:** Live requests can now wait longer before failing, and future scope expansion that triggers pagination will stop the run until pagination is implemented deliberately. We accept both costs because source determinism and honest failure behavior are more important than preserving a brittle happy path.

**Date:** 2026-04-11

---

## ADR-040: Treat Live Annual Series Older Than One Year as Stale Coverage

**Context:** The final PRD close-out pass exposed one remaining data-quality gap. The monitored-set live run already failed explicitly when countries had no usable debt series, but it still accepted very old annual tails as if they were current coverage. In the real monitored-set smoke, five debt series were current through 2023, Australia lagged to 2022, and India only had a usable value as far back as 2018. Leaving that untouched meant the pipeline could surface materially stale fiscal language while claiming current live coverage.

**Decision:** Define a freshness rule for annual live indicators. For a requested range ending in year `Y`, a country-indicator series remains usable only if its latest non-null observation is at least `Y - 1`. Anything older is treated as stale coverage, removed from the normalized live result, and reported explicitly in the fetch failure summary.

**Why:** This keeps the pipeline honest without over-penalizing annual public-source lag that is still close enough to inform the current narrative. A one-year allowance preserves near-current annual data while excluding clearly stale tails that would distort the live risk story.

**Trade-off:** The live fetch path now treats some source rows as unavailable even though the World Bank still returns them. We accept that because the alternative is presenting materially stale fiscal or external data as if it were part of the current live coverage story.

**Date:** 2026-04-11

---

## ADR-041: Replace the ML6-Market Scope With a 2024 Exact-Complete 17-Country Core Panel

**Context:** The live feasibility scan against the full World Bank country catalog changed the country-selection trade-off materially. The old ML6-market 15-country set told a good geographic story, but it produced repeated debt-coverage failures and stale-series exceptions in the real monitored run. The broader scan showed that no country has even five consecutive fully complete years across the six approved indicators ending at 2025, while exactly 17 countries have a fully complete 15-year span ending at 2024. The challenge brief requires a credible World Bank integration and defensible economic insights, but it does not mandate a fixed country list, a fixed year window, or a fixed monitored-country count.

**Decision:** Replace the superseded ML6-market 15-country monitored set and the seven-year `2017:2023` live window with a data-complete core panel anchored to `2010:2024`. The active live monitored set is: BR, CA, GB, US, BS, CO, SV, GE, HU, MY, NZ, RU, SG, ES, CH, TR, UY. This supersedes ADR-019 and ADR-037 for the active live monitored-set scope. Repository metadata, API country listing, and live runtime fetching should use this panel. Deterministic `local` mode stays on the existing ZA fixture slice for tests and lightweight development.

**Why:** This is the smallest scope change that makes the live backend honest and comparable without lowering the data-quality bar or inventing substitute indicators. It preserves the approved six-indicator macro story, gives the pipeline one defensible balanced panel for longitudinal analysis, and stays well inside the challenge's bounded-product expectations.

**Trade-off:** We give up the earlier geographic-representation and ML6-market narrative. The new core panel has no Africa, MENA, or South Asia coverage, and Russia stays in scope because the shortlist is mechanically derived from the completeness rule rather than chosen editorially. If future product goals require broader regional representation, that should become an explicit second-tier watchlist with documented partial-coverage rules instead of silently weakening the exact-complete core panel.

**Date:** 2026-04-11

---

## ADR-042: Keep Repo Defaults Local and Make Cloud Runtime Selection Explicit

**Context:** The next rollout phase needs truthful Cloud Run, Firestore, GCS, and frontend-proxy deployment guidance, but the repo still serves two audiences at once: deterministic local development and a future cloud deployment. Letting code defaults drift toward cloud-only behavior would make local validation more fragile and would hide critical deployment intent inside implicit fallbacks instead of explicit service configuration.

**Decision:** Keep the repo defaults on deterministic local mode where practical, including `PIPELINE_MODE=local` and `REPOSITORY_MODE=local`, and require Cloud Run services to opt into production behavior through explicit environment variables such as `PIPELINE_MODE=live` and `REPOSITORY_MODE=firestore`.

**Why:** This keeps local commands, tests, and review demos dependency-light while making the cloud rollout more honest. A reviewer can now see exactly which settings turn on live World Bank fetches, Firestore persistence, GCS raw archives, and the frontend proxy path instead of inferring them from code defaults.

**Trade-off:** Cloud deployment commands become a little longer because they must carry the runtime contract explicitly. We accept that because the alternative is a more fragile local experience and a less auditable deployment story.

**Date:** 2026-04-12

## ADR-043: Replace the Global Overview Raster Map With a Bundled Vector Geography

**Context:** The Global Overview map had already moved away from percentage-based marker placement, but it still depended on a cropped raster basemap, custom projection math, and country-specific nudges to make the pins look approximately right. That made the UI more stable than the old CSS overlay, but it still was not geographically trustworthy enough for an analyst-facing surface.

**Decision:** Replace the raster-backed map with a `react-simple-maps` vector geography rendered from a bundled `world-atlas` topology asset. Country pins now use real latitude and longitude projected by the same map engine that draws the world geometry, and the selected-market tooltip stays attached to that projected point inside the SVG layer.

**Why:** This removes the manual pin nudges from the geographic placement path, keeps marker positions consistent across screen sizes, and keeps the map self-contained in the production bundle instead of depending on an external runtime fetch. It also stays within the existing frontend stack rather than introducing a second mapping library.

**Trade-off:** The bundle grows because the world topology asset ships with the frontend, and the selected tooltip still uses edge-aware clamping so it stays readable near the map boundary. We accept that because geographic accuracy is more important here than preserving the smaller raster asset or a perfectly centered tooltip in every case.

**Date:** 2026-04-12

## ADR-044: Per-Indicator Z-Score Anomaly Detection Over a Fixed Percentage Threshold

**Context:** The original analyser flagged any year-over-year percent change above a fixed 3% constant as anomalous. That constant was applied uniformly across all six indicators: GDP growth, CPI, unemployment, debt-to-GDP, current account balance, and broad money. The problem is that each indicator has a completely different natural volatility range. GDP growth crossing 3% is routine for emerging markets. CPI crossing 3% in a developed economy may signal overheating. A 3-point shift in debt-to-GDP is almost invisible in most cycles. A uniform threshold produces both under-flagging (misses real shocks in low-volatility indicators) and over-flagging (treats routine growth as a risk event).

**Decision:** Replace the fixed constant with a cross-panel z-score per indicator. Compute the mean and standard deviation of the year-over-year percent change across all 17 countries for each indicator, then flag any observation where `|z| >= 2.0`. Pass the raw `z_score` value into the LLM context so the AI can reason about magnitude — a 2.1σ move is notable, a 4.0σ shock warrants a strong statement.

**Why:**

1. **Indicator-relative baseline.** GDP growth of +8% is routine for an emerging market; it is not anomalous relative to the GDP growth distribution. The same absolute move in unemployment would be catastrophic. Z-score puts each indicator against its own historical panel distribution.
2. **Cross-panel pooling.** Per-country std would require roughly 30+ years of data per country to be stable. The 17-country cross-panel pool gives ~119 observations per indicator — enough for a meaningful baseline while also anchoring each country against its global peers, which is the correct frame for sovereign risk analysis.
3. **Conventional significance threshold.** 2.0σ corresponds to roughly the outer 5% of a normal distribution. This is a standard and defensible choice in quantitative finance, and it gives the project a clear, explainable methodology during review.
4. **Brief alignment.** The challenge brief requires "identifying trends, anomalies, or specific financial risks." Pandas does the statistical detection; the LLM receives `z_score` and `is_anomaly` and writes the narrative. This keeps the responsibilities clean.

**Trade-off:** Cross-panel pooling works when the 17-country panel is complete. If panel coverage shrinks to fewer than 4–5 countries per indicator, the std becomes unreliable. A zero-std guard is implemented: when std is 0 or undefined, every point in that indicator group is treated as non-anomalous rather than crashing or producing infinite z-scores. This is conservative and appropriate for the current state of the pipeline.

**Date:** 2026-04-12

---

## ADR-045: Exact-Match AI Reuse Reuses Only Healthy Outputs and Fails Runs Honestly on Degradation

**Context:** The live-AI PRD still needed exact-match reuse and clearer run-level honesty when the provider fell back to degraded structured output. The repo already persisted per-record AI lineage fingerprints and private provenance, but it did not yet avoid duplicate calls or reflect degraded AI coverage in terminal run status.

**Decision:** Reuse prior AI outputs only from persisted non-degraded records whose exact input fingerprint matches, and keep that reuse inside the current mixed-document repository instead of adding a cache tier. When a live run stores degraded AI fallback output, preserve the successful records but end the run as failed through the existing status, error, and failure-summary mechanics.

**Why:** Exact-match reuse from current records is the smallest auditable path to lower repeat AI cost. Skipping degraded source records avoids turning transient provider failures into sticky cached fallbacks. Marking the run failed after storing degraded output keeps the product honest: reviewers can still inspect the useful output, but the terminal status no longer suggests full healthy AI coverage.

**Trade-off:** The first run after rollout still has to materialize reuse-ready records, and degraded outputs are re-attempted on later runs rather than reused. The public API also continues to express this state through the existing failed run status instead of a richer status taxonomy. We accept that because it keeps the contract stable while making the run outcome materially more truthful.

**Date:** 2026-04-12

---

## ADR-046: Treat `pipeline/evaluation.py` as the Live-AI Approval Gate

**Context:** The live-AI PRD required a repeatable evaluation gate, but a reporting script without concrete thresholds, a non-zero exit path, or a runnable judge configuration would still leave model approval open to ad hoc interpretation.

**Decision:** Use `pipeline/evaluation.py` as the repo-owned approval gate for the live baseline. The gate must run the full approved 17-country by 6-indicator scope, fail non-zero when evidence misses the documented bar, score groundedness and coherence through the repo's built-in rubric by default with an optional live judge model overlay, and estimate full-run cost with a versioned pricing table for the active baseline.

**Why:** This makes model approval something a reviewer can reproduce from the repo instead of a chat-only judgment call. It also keeps the cost, latency, and quality trade-offs explicit at the same boundary where provider selection already lives.

**Trade-off:** Gate runs are slower and more expensive than a normal validation pass because they add live inference and judge-scoring overhead. Pricing tables will also need occasional refreshes when provider rates change. We accept that because sign-off is infrequent and reviewability matters more than minimizing one-off evaluation overhead.

**Date:** 2026-04-12

---

## ADR-047: Keep the Shell Interaction Language Structural and Monochrome

**Context:** The frontend shell had drifted into two competing interaction languages. Header actions, overview actions, and utility links all reused the underlined command-link treatment, while the shell CSS still carried duplicate nav and header-action definitions. That blurred hierarchy and made the topbar telemetry louder than it needed to be for simple runtime metadata.

**Decision:** Keep the shell structural and mostly monochrome. Primary header actions use the orange button treatment. Secondary header actions use ghost buttons. Primary navigation stays white-on-structure, with active state expressed through tone and borders instead of orange. Underlined command links stay in the system only as tertiary utility actions. Topbar runtime telemetry stays quiet and subdued.

**Why:** This gives the app one readable interaction hierarchy. Orange keeps its semantic weight for AI surfaces and true primary actions. Navigation reads as shell structure rather than promotion. Utility links read like utilities instead of competing CTAs.

**Trade-off:** Some overview-level actions now look calmer than before, and the shell relies more heavily on button hierarchy than on command-link styling. We accept that because the old mix made the product feel less intentional and made it harder to tell what the primary action actually was.

**Date:** 2026-04-12

---

## ADR-048: Score Built-In Step 1 Groundedness on Data Anchoring, Not Repo-Implied Risk Judgments

**Context:** The live-AI evaluation gate initially failed the indicator groundedness threshold even though the underlying outputs were schema-valid, numerically specific, and directionally sensible. The miss came from the built-in rubric over-penalizing auxiliary fields such as `risk_level` when those labels did not line up with the repo's own implied interpretation, especially on CPI, debt, and current-dollar GDP cases.

**Decision:** Keep the built-in indicator judge focused on what the PRD actually requires for approval: grounding to the supplied data. The default rubric now scores Step 1 outputs on numeric references, direction-of-travel alignment, data-year references, indicator-specific language, and honest missing-data language. It no longer treats agreement with repo-implied risk semantics as a required groundedness condition. The optional live judge overlay remains available for richer qualitative review when quota allows.

**Why:** This makes the gate measure the thing it claims to measure. A grounded output should pass because it cites the right figures and describes the move correctly, not because it happens to match a hidden risk heuristic. It also keeps the default gate deterministic, reproducible from the repo, and usable even when a live judge model is quota-constrained.

**Trade-off:** The built-in gate is now narrower. It is strong at catching weak numeric anchoring and weak directionality, but it will not catch every subtle issue in risk framing or macro judgment. We accept that because PRD sign-off needs a stable approval gate for grounding and contract safety first, while richer judgment can stay in the optional live-judge path and human review.

**Date:** 2026-04-12

---

## ADR-049: Keep Functional Looping Indicators Outside the 200ms Interaction Cap

**Context:** The frontend-fidelity PRD caps hover, focus, active, and state transitions at 200ms to stop the UI from drifting into decorative motion. That rule works for discrete interactions, but it clashes with a small set of continuous indicators the terminal uses to show loading, selected focus, or active execution: the blinking terminal cursor, running-stage border pulse, selected map-marker ping, and skeleton shimmer.

**Decision:** Keep the 200ms cap for discrete interaction transitions and allow longer looping animations only when they carry state. The allowed exception is narrow: the animation must explain a live condition, stay visually restrained, use transform, opacity, or background-position rather than layout properties, and respect `prefers-reduced-motion`.

**Why:** Forcing these loops under 200ms would make them frantic and less readable. The longer cadence lets the terminal signal "running", "selected", or "loading" without turning the interface into decoration. It also keeps the rule easy to defend: short transitions for interaction polish, slower loops only when the UI is communicating state.

**Trade-off:** This adds a small exception to an otherwise clean timing rule, so future motion work needs discipline. We accept that because the alternative is worse UX and a misleadingly strict interpretation of the PRD that would punish the few places where gentle motion is actually doing useful work.

**Date:** 2026-04-12

---

## ADR-050: Runtime-Gated Trigger Dispatch with Firestore-Backed Run Claiming

**Context:** The API trigger still started the pipeline on an in-process thread. That kept the local slice working, but it blocked the cloud topology because the deployed API could not truthfully claim it dispatched a separate Cloud Run Job. The trigger also needed an idempotent claim path that works across stateless API instances without changing the public status contract.

**Decision:** Keep local trigger execution on the existing background-thread path by default, add an explicit `WORLD_ANALYST_PIPELINE_DISPATCH_MODE` gate, and make cloud dispatch opt-in. In cloud mode, the API claims the next run through the shared repository before dispatching a Cloud Run Job. When the Firestore repository is active, that claim uses a Firestore transaction on the current pipeline-status document.

**Why:** This keeps local development deterministic and easy to run, while making the cloud path explicit instead of inferred from environment drift. Reusing the durable status record as the idempotency gate avoids a second coordination system and keeps the frontend polling contract unchanged.

**Trade-off:** The trigger flow now carries extra runtime configuration and a little more orchestration code. We accept that because it is still smaller and easier to defend than duplicate job runs or an API process that pretends to be a job dispatcher without actually behaving like one.

**Date:** 2026-04-12

---

## ADR-051: Build Cloud Run Images from Repo Root Through a Shared Cloud Build Config

**Context:** The new API and pipeline containers both depend on sibling directories outside their own folders: the API image needs `pipeline/` and `shared/`, and the pipeline image needs `shared/`. That makes the simple `gcloud builds submit ./api --tag ...` shape dishonest, because those Dockerfiles cannot build correctly from a subdirectory-only context.

**Decision:** Add a repo-root `cloudbuild.images.yaml` that builds all three deployable images from the repository root. The deploy workflow now uses that shared Cloud Build config instead of assuming a local Docker daemon or a subdirectory-only build context.

**Why:** This keeps the build surface aligned with the real code layout and makes deployment work from more environments, including machines where Docker is installed but the daemon is unavailable. It also removes ambiguity for reviewers: the repo now contains one explicit image-build path that matches the Dockerfiles it ships.

**Trade-off:** A shared build config is one more deployment asset to maintain, and all three images now build from the same root context instead of three isolated subdirectories. We accept that because correctness and repeatability matter more here than keeping the build instructions superficially shorter.

**Date:** 2026-04-12

---

## ADR-052: Use the Built-In Run Developer Role for Override-Based API Dispatch

**Context:** The deployed API dispatches manual pipeline runs through the Cloud Run Jobs API and passes run-scoped environment overrides such as `WORLD_ANALYST_PIPELINE_RUN_ID` and `WORLD_ANALYST_PIPELINE_COUNTRY_CODE`. The initial least-privilege assumption was `roles/run.invoker`, but the live rollout showed that override-based executions require `run.jobs.runWithOverrides`, which `roles/run.invoker` does not include.

**Decision:** Grant the API service account `roles/run.developer` for the Cloud Run Job dispatch path instead of relying on `roles/run.invoker` alone.

**Why:** This is the smallest built-in role that made the deployed manual trigger work truthfully with runtime overrides and without a custom IAM role. It keeps the deployment instructions reproducible from the repo and avoids a runbook that only works for non-override execution.

**Trade-off:** `roles/run.developer` is broader than the exact single permission the API needs. We accept that for the challenge rollout because it stays within Cloud Run scope, avoids the maintenance overhead of a custom role, and keeps the live deployment path easy to reproduce and explain.

**Date:** 2026-04-12

---

## ADR-053: Keep Frontend Proxy Fallbacks Local-Only and Fail Fast in Production

**Context:** The frontend container needs two runtime values to uphold the browser-facing auth boundary: `WORLD_ANALYST_API_UPSTREAM` and `WORLD_ANALYST_PROXY_API_KEY`. The repo had local-friendly defaults in `frontend/Dockerfile`, which made container experiments easy but also meant a Cloud Run deployment could start with development placeholders unless the operator remembered to override them correctly.

**Decision:** Keep the local-friendly frontend proxy defaults for explicit local runtimes, but require `WORLD_ANALYST_RUNTIME_ENV=production` on Cloud Run and fail container startup when either proxy variable is missing or still set to the local fallback.

**Why:** This preserves lightweight local container experiments without letting the deployed runtime rely on implicit development values. It also makes the browser-facing auth boundary auditable from the repo: production must set the upstream and secret explicitly, and misconfiguration fails before the dashboard serves traffic.

**Trade-off:** The frontend deployment command is slightly more explicit because it now sets `WORLD_ANALYST_RUNTIME_ENV=production`, and the image carries one small validation script. We accept that because the alternative is a brittle rollout that is only safe when every operator remembers to override local defaults perfectly.

**Date:** 2026-04-12

---

## ADR-054: Store One Panel Overview Record but Keep Panel Metrics Deterministic

**Context:** The Global Overview page was still reading like a lead-market screen because the frontend hero and signal pack were anchored to `overview.briefings[0]`, even though the page already fetched the full monitored set of country briefings. The product gap had two separate causes: the page lacked a true cross-country narrative record, and the UI model was incorrectly treating one country as the panel story.

**Decision:** Add one stored `global_overview` record plus a spec-first `/overview` endpoint for the cross-country narrative, while deriving panel metrics and signal cards deterministically from the existing country and indicator payloads.

**Why:** The monitored-set summary genuinely needs a separate narrative pass because it synthesises across all country briefings. The hero metrics, anomaly counts, and panel signal cards do not need another model call; they are stronger and more auditable when they are computed directly from the structured data the page already has.

**Trade-off:** The pipeline and repository contract gain one more stored document type and one extra synthesis pass. We accept that because it sharply separates the truly global narrative from country drilldown content without inflating model usage for panel facts the frontend can already calculate itself.

**Date:** 2026-04-12

---

## ADR-055: Prefer Frontend-Only Progressive Overview Hydration Over a New Loader Stack or Batch Endpoint

**Context:** The final overview polish still had two viable implementation paths: expand the backend with a batch briefing endpoint and/or add a new skeleton dependency, or keep the current API surface and make the landing page truly panel-first in the existing frontend. The closeout goal was better first paint and no hidden Brazil-first posture without reopening backend scope at the finish line.

**Decision:** Keep the current API surface and existing CSS skeleton system. Implement panel-first overview hydration in `frontend/src/pages/GlobalOverview.jsx`, defer country briefings until focus or queue visibility, and route generic country entry through `frontend/src/pages/CountryIntelligenceLanding.jsx` instead of a hard-coded market.

**Why:** This solves the user-visible problems with the data and primitives the repo already has: `/overview`, `/countries`, `/indicators`, `/pipeline/status`, and the design-system CSS in `frontend/src/index.css`. It removes the lead-market feel, improves first paint, and avoids adding a late dependency or a spec change that would need more backend review.

**Trade-off:** The frontend now carries more orchestration state, and per-country briefings can still incur individual latency after the landing view renders because we did not add a batch endpoint. We accept that because the critical review issue was the blocked landing experience, and the client-side change fixed it with lower delivery risk.

**Date:** 2026-04-12

## ADR-056: Step 3 AI prompt v2 — geographic ordering and cross-continental synthesis

**Date:** 2026-04-16
**Status:** Accepted
**Context:** Step 3 was sorting country briefings alphabetically (BR first), causing the LLM to anchor narratives on Brazil. The system prompt lacked hard rules about geographic coverage and data year citation.
**Decision:** Sort Step 3 briefings by geographic region (Europe first) and add explicit continental coverage requirements and data year context to the prompt. Bump version to step3.v2.0.0 to invalidate cache.
**Consequences:** The next pipeline run will re-generate the global overview synthesis. Lineage/reuse records using step3.v1.0.0 will not match and will be regenerated.

## ADR-057: Temperature=0 for Gemma 4 — empirical variance reduction

**Date:** 2026-04-17
**Status:** Accepted
**Context:** Default temperature for Gemma 4 (`gemma-4-31b-it`) was tested at 0 and at 1.0. At temperature=0, schema validity across all structured output calls was 100% with 0% degraded responses. At higher temperatures, occasional markdown fence wrapping around JSON caused schema validation failures requiring the `repair_markdown_fences()` fallback more frequently. The Gemini skill guidance recommends 1.0 for Gemini 3, but Gemma 4 behaves differently as a separately fine-tuned model family.
**Decision:** Keep temperature=0 for all Gemma 4 calls in `ai_client.py`. The `repair_markdown_fences()` workaround remains as a safety net. Document the empirical basis here so any future reviewer understands this is intentional, not accidental.
**Consequences:** Slightly less output variance. Narratives may be more uniform across runs. Monitor for truncation if context window pressure increases.

## ADR-059: Evaluation rubric — word-boundary matching for single-country anchoring

**Date:** 2026-04-12
**Status:** Accepted
**Context:** The `no_single_country_anchoring` dimension in the builtin evaluation rubric used simple substring search to detect whether the global overview summary opened with a country name or ISO-2 code. Short codes like `"br"` caused false positives: common English words such as "broadly", "brought", and "broader" matched the substring and scored the dimension 0.0, causing the gate to fail even when the model correctly produced a multi-regional opening.
**Decision:** Replace substring search with `re.search(r'\btoken\b', text)` word-boundary matching for all anchor tokens in the rubric. Longer names (e.g. "brazil", "united states") are unaffected; short codes (e.g. `"br"`, `"us"`, `"cn"`) now only match as standalone tokens.
**Consequences:** False positives on common English prefixes are eliminated. The rubric remains deterministic and requires no LLM call. Gate now correctly distinguishes a country-anchored opening from a globally-framed one. Confirmed clean pass: `no_single_country_anchoring: 1.0` on eval run `24539edc`.

---

## ADR-058: Remove pipeline KPI cards from Global Overview page

**Date:** 2026-04-17
**Status:** Accepted
**Context:** The Global Overview page displayed four operational KPI cards: Pipeline Status, Countries Materialised, Indicators Analysed, and Country Queue. These expose pipeline-internal metrics (data processing counts, queue state) to a financial end-user whose primary concern is market signals, not infrastructure health.
**Decision:** Remove the four pipeline KPI cards from the Global Overview. Pipeline status is available on the dedicated Pipeline Trigger page. If a pipeline error occurs, an inline notification surfaces it without occupying prime real estate on the overview. The freed space improves signal density for the actual market content.
**Consequences:** Financial users see a cleaner overview focused on market intelligence. Pipeline operators still have full visibility via the Trigger page. The responsible-AI disclaimer and `auto_awesome` accent icon are retained — they are user-facing content, not operational jargon.

---

## ADR-060: Persist Full Historical Time Series in Firestore Documents (Not BigQuery)

**Date:** 2026-04-17
**Status:** Accepted
**Context:** The Country Intelligence Enhancement PRD (`docs/prds/country-intelligence-enhancement.md`) requires exposing 10–15 years of historical indicator data per country for a timeline view. ADR-001 noted: "If analytical queries become a requirement (e.g., compare GDP trends across all countries over 10 years), we'd need to migrate [to BigQuery]." The question is whether this enhancement triggers that migration.

**Decision:** Persist the full time series (2010–2024) as a nested array inside the existing Firestore country documents. Do not migrate to BigQuery.

**Why:** The access pattern remains key-value: load one country document, render its full indicator history. This is a `doc.get()` call, not a cross-country analytical query. The data growth is modest: 6 indicators × ~15 years × ~60 bytes per data point ≈ 5.4KB additional per country document. Total across 17 countries: ~92KB. Firestore's 1MB document limit is not a concern. The frontend renders one country at a time — there is no cross-country time-series comparison view in scope.

**Trade-off:** If a future feature requires cross-country time-series comparison (e.g., "overlay GDP growth for Brazil, Turkey, and Hungary on one chart"), Firestore would require fetching N separate documents and joining client-side. That would be the trigger for a BigQuery or secondary-index migration. The current single-country timeline view does not cross that line.

**Ref:** `docs/prds/country-intelligence-enhancement.md` §8.2

---

## ADR-061: Rule-Based Regime Classification Over LLM-Derived Labels

**Date:** 2025-01-27
**Status:** Accepted

**Context:** The V2 Consolidated PRD adds a lightweight economic regime label (recovery, expansion, overheating, contraction, stagnation) to each country briefing. Two approaches were viable: (a) derive the label from Pandas rules on GDP growth, inflation, and unemployment direction, or (b) add an LLM classification call.

**Decision:** Rule-based classification in `pipeline/analyser.py`. No additional LLM call.

**Why:** The label is a structural classification, not a narrative judgment. GDP growth direction, inflation level, and unemployment trend are already computed in the statistical analysis pass. A Pandas function that maps these to five labels is deterministic, testable, and auditable. The LLM synthesis already receives and contextualizes this information in prose — adding a separate classification call would be redundant and non-deterministic.

**Trade-off:** Rule-based classification is less nuanced than LLM judgment. Edge cases (e.g., is 0.5% GDP growth "stagnation" or "recovery"?) may be debatable. We accept this because the label is directional context, not investment advice, and because deterministic rules are easier to defend in review than "the model said so."

**Ref:** `docs/prds/v2-consolidated-product-upgrade.md` Phase 1.3

---

## ADR-062: Demo Walkthrough as Frontend-Only Simulation, Not Backend Mock Mode

**Date:** 2025-01-27
**Status:** Accepted

**Context:** The V2 Consolidated PRD splits Pipeline Trigger into a real run mode and a demo walkthrough mode. The demo could be implemented as (a) a frontend-only animation stepping through the shared pipeline stage model, or (b) a backend mock mode that returns fake pipeline status responses.

**Decision:** Frontend-only. The demo walkthrough animates through `PIPELINE_STAGES` without making any API calls. It is clearly labeled as a frontend simulation.

**Why:** The backend should never return fake data. A mock mode would contaminate the `/pipeline/status` endpoint and create ambiguity about whether the dashboard is showing real or simulated state. A frontend-only walkthrough keeps the truth boundary clean: if data comes from the API, it's real. If it's animated in the browser, it's labeled as a demo.

**Trade-off:** The demo walkthrough cannot show real Firestore writes or actual LLM latency patterns. We accept this because the purpose of the walkthrough is to explain the pipeline's structure and transformation flow, not to simulate its performance characteristics.

**Ref:** `docs/prds/v2-consolidated-product-upgrade.md` Phase 5.1

---

## ADR-063: Inline Time-Series in Existing API Responses Over Separate History Endpoint

**Date:** 2025-01-27
**Status:** Accepted

**Context:** The V2 PRD requires exposing per-year historical data for indicator charts. Two API approaches: (a) add `time_series` arrays inline to the existing `IndicatorInsight` schema returned by `/countries/{code}`, or (b) add a separate `/countries/{code}/indicators/{code}/history` endpoint.

**Decision:** Inline first. The `time_series` array is added to `IndicatorInsight` in `openapi.yaml` and served as part of the existing country detail response.

**Why:** 17 countries × 6 indicators × ~15 years = ~1,530 data points per country. At ~100 bytes per point, that's ~150KB per country detail response. This is well within acceptable payload size for a demo-scoped product. A separate endpoint would add API surface area, require additional frontend fetch orchestration, and create a second loading state on the country page — all for a payload optimization that isn't needed at this scale.

**Trade-off:** If the country panel grows significantly (e.g., 50+ countries, 20+ indicators), the inline approach would need revisiting. The trigger for a separate endpoint is measured latency exceeding 500ms for the country detail response. Current scope (17 countries) does not approach this.

**Ref:** `docs/prds/v2-consolidated-product-upgrade.md` Technical Implications

---

## ADR-064: Return Sparse Ascending Time-Series Arrays Instead of Padded Year Windows

**Date:** 2026-04-12
**Status:** Accepted

**Context:** Phase 1 adds inline historical indicator series to the existing API responses. Two shaping options were viable: (a) always return a fixed `2010–2024` array with explicit `null` gaps for missing years, or (b) return only observed yearly points and keep the array ordered from oldest to newest.

**Decision:** Return sparse ascending arrays. Each `time_series` list contains only observed yearly points, sorted oldest-to-newest. Missing years are omitted rather than padded with placeholder rows.

**Why:** World Bank annual coverage is not perfectly uniform across indicators and countries, and the local deterministic slice still has a shorter source window than the live path. Sparse arrays keep the API honest: the response shows what the pipeline actually observed and analysed, while `source_date_range` communicates the overall window. Ascending order also matches charting defaults and makes timeline rendering straightforward in the frontend.

**Trade-off:** Frontend timeline components must treat gaps as missing observations rather than assuming a fully dense yearly index. We accept that because padding with synthetic `null` rows would blur the line between absent data and observed data, while also increasing payload size for no analytical gain.

---

## ADR-065: One Shared Frontend Pipeline Stage Model Over Page-Local Trigger and Walkthrough Copy

**Date:** 2026-04-12
**Status:** Accepted

**Context:** Phase 2 splits Pipeline Trigger into a truthful real run mode and a frontend-only demo walkthrough, while How It Works also needs to explain the same pipeline. Two implementation shapes were viable: (a) keep separate hardcoded stage copy in each page and manually keep them aligned, or (b) introduce one shared frontend stage model and let each page adapt it to live or simulated progress.

**Decision:** Use one shared frontend stage model in `frontend/src/pipelineStageModel.js`, with separate adapters for real backend status and demo walkthrough playback.

**Why:** The product story is one thing even though the runtime adapters differ. A shared model keeps stage names, business explanations, latency notes, and demo activity copy in one place, so How It Works and Pipeline Trigger cannot drift into telling different stories about the same system. It also keeps the truth boundary clean: the real adapter still renders backend-reported status, while the demo adapter replays the same stages in browser-only state.

**Trade-off:** The shared model adds a small abstraction layer to the frontend, and the real adapter still needs one live-only operational stage for `dispatch` when Cloud Run job launch is visible. We accept that because the extra structure is cheaper than maintaining duplicate copy across pages, and because treating `dispatch` as live-only preserves backend truth without polluting the shared product-stage story.

---

## ADR-066: Session-Scoped Country Detail Preload Over a New Batch Endpoint or Persistent Browser Cache

**Context:** ADR-055 improved Overview first paint by keeping the current API surface and deferring country-detail work until a user showed intent. That fixed the blocked landing experience, but country drill-in can still feel colder than it should: once a user has identified a market from the map or the `/country` directory, opening `/country/:id` still waits on a fresh detail request. At the same time, ADR-063 keeps historical series inline in the existing country detail response, so adding a batch endpoint would expand backend scope just to hide a route-level pause.

**Decision:** Keep the current API boundary and introduce a shared session-scoped frontend cache for country detail. Warm that cache in the background after the initial view becomes interactive, prioritize hovered, selected, and visible countries first, and reuse the warmed payload across Overview, the `/country` directory, and `/country/:id` navigation.

**Why:** The monitored set is fixed at 17 countries, so the frontend can treat country detail as a bounded working set instead of a cold lookup. This improves perceived route speed without adding a new endpoint, a new backend cache tier, or cross-session browser persistence that could serve stale market context. It also keeps the behavior easy to explain in review: data still comes from the same truthful country-detail endpoint, but the client fetches likely-next markets before the user clicks.

**Trade-off:** The frontend takes on more orchestration state and each session may issue some background requests for countries the user never opens. We accept that because the working set is small, the UX gain is immediate, and the revisit trigger is clear: if the monitored set or per-country payload grows enough to make background warming visibly expensive, then a batch detail endpoint becomes the next step.

**Date:** 2026-04-12

---

## ADR-067: Replay Walkthrough as a Wizard Modal Over Inline Page Playback

**Date:** 2026-04-12
**Status:** Accepted

**Context:** The demo walkthrough already existed as a frontend-only replay on the Trigger page, but it played inline inside the same execution grid used for truthful live status. Two viable UI shapes remained: keep the demo inline and let the page simulate progress inside the shared stage list, or move the demo into a dedicated overlay that can explain one stage at a time without competing with the live run surface.

**Decision:** Move the replay walkthrough into a modal wizard on the Trigger page. Keep the real run feed inline, but present the demo as a browser-only overlay with auto-play, manual Next and Back controls, clickable stage cards, and a synced presentation feed.

**Why:** The walkthrough is presentation behavior, not operational truth. Putting it in a dedicated modal makes that boundary obvious: the page still shows the real trigger controls and static shared stage model, while the overlay can slow down, animate, and explain each step clearly without implying backend progress. Reusing the existing shared stage model and CSS-native motion keeps the story aligned with the rest of the product and avoids adding a new dialog or animation dependency just for one demo surface.

**Trade-off:** The frontend now owns a bit more modal state, keyboard handling, and focus management. We accept that because the result is easier to present, easier to read, and more honest than mixing simulated playback directly into the live execution panel.

---

## ADR-068: Keep Statistical Anomalies Separate From Adverse Moves in the Overview Signal Pack

**Context:** The Global Overview signal pack combines two different kinds of signals from [frontend/src/pages/globalOverviewModel.js](frontend/src/pages/globalOverviewModel.js): `anomalyCount` comes from the pipeline's statistical outlier flag, while `adverseCount` describes how many markets moved in the economically wrong direction for that indicator. The card copy said "No anomalies" directly above a sentence about markets moving in the wrong direction, which made the UI read as contradictory.

**Decision:** Keep anomaly as the statistical term and keep adverse moves as a separate directional-risk term. Update the signal-pack label to explicit copy such as "0 statistical anomalies" instead of broadening anomaly to mean any negative move.

**Why:** The pipeline already gives anomaly a precise meaning through `is_anomaly`, and the dashboard also needs to surface directional stress even when a move is not statistically extreme. Making the statistical label explicit preserves that distinction without changing the data model or hiding economically adverse moves from the panel.

**Trade-off:** The card now carries slightly more technical wording. We accept that because it is more accurate than calling ordinary adverse moves anomalies, and it removes a piece of user-facing copy that undermined trust.

**Date:** 2026-04-12

---

## ADR-069: Risk-First Overview Hero Over Selection-Dependent First-Screen Detail

**Date:** 2026-04-12
**Status:** Accepted

**Context:** The Global Overview first screen had solid source material but weak arrival behavior. The hero mixed macro synthesis, risk flags, and selection-dependent detail in one surface. The most visible failure was the third summary tile: it could collapse into an empty "select a market" state even though the page is supposed to answer the global question before any interaction. At the same time, the map-side drilldown rail did very little when no country was selected.

**Decision:** Keep the existing API boundary and the existing explicit map-focus interaction, but change the first-screen hierarchy to be risk-first. The hero now surfaces a persistent stress signal derived from the existing indicator layer, not from a selected market. The no-focus drilldown rail now opens with a pressure watchlist derived from the same ranking logic, so the page stays useful before any user action. We do not auto-select a default country on load.

**Why:** A finance-facing landing surface should answer three things immediately: what the macro posture is, where the stress is, and what to open next. Selection-dependent empty states fail that test. Reusing the current indicator and coverage data keeps the redesign truthful and deterministic without waiting for warmed country briefings or expanding the backend contract. Keeping explicit selection separate from default watchlist content also preserves the current map interaction model instead of smuggling in a fake preselected market.

**Trade-off:** The first screen now carries more derived ranking logic in the frontend, and the hero gives slightly less space to open-ended narrative. We accept that because the page now scans more like a premium macro dashboard: the narrative still exists, but the arrival surface no longer hides its most actionable signal behind a click.
