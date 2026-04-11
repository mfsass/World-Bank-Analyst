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

**Decision:** Use a seven-year history window. The initial implementation uses `2017:2023` for all approved indicators.

**Why:** The current analysis logic compares year-over-year movement and needs more than one recent point. Seven years is enough to show medium-term direction without adding much extra fetch or storage cost, and it matches the existing fixture baseline.

**Trade-off:** Very long-term structural context stays out of scope. We accept that because the current product is built for recent risk signals, not decade-scale economic research.

**Date:** 2026-04-10

---

## ADR-020: Curated Repository Baseline Over Code-Only Import

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
