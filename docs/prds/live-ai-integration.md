# PRD: Live AI integration

## 1. Product overview

### 1.1 Document title and version

Live AI integration
Version: 1.0
Date: 2026-04-12
Status: Implemented and validated locally

### 1.2 Product summary

World Analyst already has the shape of its AI layer in code, but the current end-to-end pipeline still runs through a deterministic development adapter instead of a real model provider. That keeps local tests stable, but it means the product is not yet delivering the live LLM behavior that the challenge brief and the architecture story both claim. The next step is to activate real model calls for bounded production runs without turning the system into a model lab or an expensive orchestration platform.

This PRD covers the live-AI layer only. It owns the switch from deterministic development AI to real provider-backed inference for the existing two-step chain, the provider and model selection policy, structured-output reliability, evaluation gates, low-cost reuse rules, and the minimum provenance needed to explain which model produced which output. It does not own live World Bank fetching, cloud job dispatch, final browser-facing API-key architecture, or broad operational hardening. The goal is narrow and practical: keep the current AI design, make it real, and keep the system honest about quality and cost.

The initial live baseline must use Google GenAI with `gemma-4-31b-it`. That is an economy-first starting point, not a blind long-term commitment. The chosen model remains subject to evaluation against real pipeline inputs. If the baseline does not meet the required quality, reliability, or structured-output thresholds, the implementation may promote one or both AI steps to a stronger model. The product should pay for more model power only when evaluation evidence shows it is needed.

### 1.3 Implementation outcome

The live-AI layer is now implemented behind the existing pipeline seam. `PIPELINE_MODE=live` uses the provider-backed client in `pipeline/ai_client.py`, while `PIPELINE_MODE=local` stays deterministic through `pipeline/dev_ai_adapter.py`. The approved baseline remains Google GenAI with `gemma-4-31b-it`, backed by bounded retry logic, bounded markdown-fence repair before schema validation, explicit degraded fallback payloads, prompt-version lineage, and private per-record AI provenance.

This phase also closed the two remaining product-honesty gaps that would have made the AI story hard to defend in review. Exact-match reuse now avoids duplicate provider calls only when the prior stored output is healthy and fingerprint-compatible, and degraded live AI no longer looks like a clean success at run level. Successful outputs are still stored, but the terminal run status fails when degraded fallback output was required.

Validation completed on 2026-04-12:

- `cd pipeline && python -m pytest tests -q` passed (`49 passed, 1 skipped`).
- `cd pipeline && python -m ruff check .` passed.
- `cd api && python -m pytest tests -q` passed (`14 passed`).
- `python -m pipeline.evaluation` passed on the full approved 17-country by 6-indicator scope with zero fetch failures, 100% schema-valid outputs in both AI steps, 0 degraded fallbacks, 0 refusals, indicator groundedness `0.936`, synthesis coherence `1.0`, Step 1 p95 latency `5338 ms`, Step 2 p95 latency `7705 ms`, and estimated full-run cost `$0.011646`.

## 2. Goals

### 2.1 Business goals

- Replace deterministic development AI with real provider-backed AI for bounded live runs.
- Demonstrate agentic thinking through the existing two-step chain instead of a generic single-pass prompt.
- Keep AI cost low enough that weekly scheduled runs remain easy to justify and explain.
- Preserve an architecture story that is easy to defend in review: pandas does the math, the LLM writes the narrative.

### 2.2 User goals

- As an evaluator, I want the product to use a real LLM so the AI layer is credible rather than simulated.
- As a finance user, I want the generated narratives to be specific, grounded in the source data, and useful for risk interpretation.
- As an engineer, I want provider choice and model upgrades to stay bounded behind one stable interface so the pipeline is easy to maintain.

### 2.3 Non-goals (explicit out-of-scope)

- Reworking the two-step chain into a broader agent framework, tool-using system, or retrieval stack.
- Replacing the live-data fetch and normalization rules owned by the live data integration PRD.
- Owning Cloud Run job dispatch, scheduler wiring, or runtime topology decisions.
- Finalizing the browser-facing API-key pattern for the deployed frontend and API. That belongs to the security, testing, and hardening PRD.
- Building a standalone prompt CMS, model playground, or experimentation platform.
- Chasing maximum benchmark quality without regard for bounded cost or explainability.

## 3. User personas

### 3.1 Key user types

- ML6 evaluator assessing whether the AI layer is real, structured, and defensible.
- Finance reviewer reading generated indicator and country narratives for risk signal quality.
- Engineer maintaining prompts, provider wiring, evaluation, and AI error handling.

### 3.2 Basic persona details

- ML6 evaluator: cares that the AI step is real, bounded, and backed by deliberate prompt and validation design rather than vague claims.
- Finance reviewer: cares that narratives cite the actual signal, magnitude, and risk implication instead of generic macro filler.
- Engineer: needs one stable AI interface with explicit evaluation rules, failure behavior, and low-cost operation.

### 3.3 Role-based access (if applicable)

- No new role model is introduced in this PRD.
- Live AI remains a pipeline-side capability surfaced through the same API and frontend responses.
- Model provider credentials remain server-side runtime concerns, not browser concerns.

## 4. Functional requirements

- **Real provider activation behind the existing AI boundary** (Priority: High)
  - Real runs must use a provider-backed AI client instead of the deterministic development adapter.
  - The pipeline must preserve the current two-step chain: per-indicator analysis first, then country-level synthesis.
  - The rest of the pipeline should continue to depend on one stable AI client interface rather than provider-specific calls.
  - Deterministic development AI must remain available for tests and lightweight local work.

- **Gemma 4 baseline with evaluation-gated promotion** (Priority: High)
  - The initial live baseline must use Google GenAI with `gemma-4-31b-it`.
  - The baseline may be replaced for one or both chain steps only when documented evaluation evidence shows it is not good enough.
  - Model promotion decisions must be explicit and reviewable rather than ad hoc.
  - The implementation must keep the path open to stronger Google, OpenAI, or OpenRouter-backed models if the baseline fails.

- **Structured output contract preservation** (Priority: High)
  - Live AI responses must continue to validate against the existing step-level schema contracts before downstream storage.
  - The chosen live model is acceptable only if the pipeline can reliably convert its responses into the required structured outputs.
  - Validation failures must never silently write malformed AI payloads into durable records.
  - If the baseline model cannot meet structured-output reliability requirements after bounded retry and repair logic, that is grounds for model promotion.

- **Prompt contract stability and versioning** (Priority: High)
  - Step 1 and Step 2 prompts must remain explicit, versioned, and easy to inspect in code.
  - Prompt changes that materially alter behavior must be traceable through a prompt version identifier or equivalent contract field.
  - The implementation must preserve the current division of labor where pandas computes statistics and the LLM writes narrative interpretation.
  - Anomaly detection is Pandas' responsibility, not the LLM's. The pipeline uses a per-indicator z-score rather than a fixed percentage threshold: each year-over-year change is compared against that indicator's own cross-panel mean and standard deviation (pooled across all 17 countries). A move is flagged when `|z| >= 2.0σ`. The raw `z_score` is passed into the LLM context so the AI can calibrate the strength of its language — a 2.1σ move warrants a different sentence than a 4.0σ shock. See ADR-044.
  - Prompt design should remain simple enough to explain clearly in review and Q&A.

- **Evaluation-gated model selection** (Priority: High)
  - The live-AI layer must include a repeatable evaluation pass before any model becomes the default production candidate.
  - Evaluation must cover at least structured-output validity, groundedness to numeric inputs, synthesis coherence, refusal behavior, latency, and estimated full-run cost.
  - The baseline model must be tested against the full approved 17-country by 6-indicator scope unless a documented subset is agreed before the evaluation phase.
  - A stronger model should only be adopted when the baseline fails documented pass criteria.

- **Bounded retry and degraded-fallback behavior** (Priority: High)
  - Live AI calls must use bounded retries for transient provider or validation failures.
  - If retries are exhausted, the system must emit an explicit degraded fallback payload rather than fabricate a normal-looking analysis.
  - Countries with incomplete AI coverage must not be presented as fully successful without qualification.
  - Successful outputs from the same run may still be preserved, but incomplete AI coverage must be visible in logs and terminal run status.

- **Low-cost reuse by exact input fingerprint** (Priority: Medium)
  - The live-AI path must avoid repeat model calls when the exact effective input has already been analysed.
  - Reuse eligibility must be based on an exact-match fingerprint derived from normalized input content, step name, prompt version, provider, and model.
  - This PRD does not introduce a semantic cache or a separate cache service.
  - Reuse must favor correctness and auditability over aggressive cache hit behavior.

- **AI provenance for stored outputs** (Priority: High)
  - Stored AI-backed outputs must preserve enough provenance to identify the producing provider, model, step, and prompt version.
  - Provenance must stay light and useful rather than becoming a full prompt-tracing platform.
  - This PRD extends the minimal provider and model provenance introduced by the durable storage and status PRD with prompt-version lineage for AI-backed records. The durable storage and status PRD still owns how those fields are persisted inside stored records.
  - A reviewer should be able to tell which model generated a stored result without reading deployment logs.

- **Cost visibility and boundedness** (Priority: Medium)
  - The system must capture provider-reported usage or an equivalent cost-estimation input for live AI calls where the provider supports it.
  - The default live-AI setup should remain aligned with a weekly bounded-scope pipeline rather than enterprise-scale inference assumptions.
  - Model upgrades that materially raise cost must be justified by evaluation evidence, not preference.
  - Cost controls should remain simple and inspectable.

- **Downstream contract preservation** (Priority: High)
  - Live AI integration must continue to feed the existing storage, API, and frontend contract shape unless an explicit decision changes that boundary.
  - The move from deterministic to live AI should strengthen the product without forcing a frontend redesign.
  - The live AI layer must validate its outputs against the current repository and API expectations before this PRD can be considered complete.
  - If new fields are needed for provenance or degraded-state honesty, they must be introduced deliberately rather than leaking through incidental payload changes.

## 5. User experience

### 5.1 Entry points and first-time user flow

A reviewer triggers the pipeline or opens a page backed by stored insights and sees the same product flow that already exists. The difference is underneath: the narrative text is now generated by a real live model instead of a deterministic development adapter. The user should not need to think about provider wiring to benefit from this change, but the product should be able to explain that live AI is now part of the real pipeline.

### 5.2 Core experience

The product continues to fetch data, compute changes, generate per-indicator narratives, synthesize country-level briefings, store results, and render them in the dashboard. With this PRD in place, those AI steps are real provider-backed calls. Users should see narratives that remain concise, risk-aware, and tied to the supplied figures rather than generic placeholder copy.

### 5.3 Advanced features and edge cases

If the baseline model produces weak or invalid outputs, the system should not quietly accept them just because the call was cheap. If a provider times out or refuses a response, the system should retry in a bounded way and then surface a degraded but explicit result if needed. If the same exact AI input appears across repeated runs, the system should reuse the previous output rather than paying for the same inference again. If one AI step fails while others succeed, the run should preserve useful work without pretending full AI coverage was achieved.

### 5.4 UI and UX highlights

- No new page is required for this PRD.
- Existing indicator and country views should continue to render against the same broad contract shape.
- User-visible AI text should be more truthful and useful than deterministic placeholder narrative.
- Responsible-AI messaging remains visible on human-facing surfaces.

## 6. Narrative

World Analyst already knows where AI belongs. Pandas calculates the signal. The LLM turns that signal into analyst language. This PRD makes that design real without making it bigger than it needs to be. It starts with a low-cost Gemma 4 baseline, forces that baseline to earn its place through evaluation, and keeps the rest of the pipeline insulated behind the same two-step AI boundary. The result should be a real AI layer that is cheap enough to run, clear enough to defend, and honest enough to trust.

## 7. Success metrics

### 7.1 User-centric metrics

- A reviewer can inspect stored outputs produced by a real live model instead of deterministic development text.
- Indicator and country narratives are specific enough to describe direction, magnitude, and risk implication rather than generic macro commentary.
- AI degradation or incomplete coverage is visible rather than silently hidden.

### 7.2 Business metrics

- The product demonstrates real provider-backed AI behavior consistent with the challenge brief.
- The AI story remains easy to present: two-step chain, bounded prompts, validated outputs, and evidence-based model selection.
- Weekly scheduled use remains financially credible because the default AI configuration is economy-first.

### 7.3 Technical metrics

- The default live model passes the documented evaluation gate before becoming the production default.
- Structured AI outputs validate against the required schemas across the evaluation corpus and a full bounded dry run.
- The system records provider and model provenance for stored AI outputs.
- Repeated exact-match inputs can reuse prior AI outputs instead of forcing duplicate inference.
- Provider usage or estimated run-cost data is available for a full bounded run.

## 8. Technical considerations

### 8.1 Integration points

- AI provider abstraction in `pipeline/ai_client.py`.
- Deterministic development adapter in `pipeline/dev_ai_adapter.py`.
- Pipeline orchestration in `pipeline/main.py`.
- Statistical context preparation in `pipeline/analyser.py`.
- Storage handoff in `pipeline/storage.py` and shared repository adapters.
- ADR-002 and ADR-003 for the two-step chain rationale and structured-output discipline.
- ADR-026 and ADR-027 for the baseline model and exact-input reuse policy.
- Adjacent architecture and challenge-fit guidance in `docs/context/world-analyst-project.md` and `docs/DECISIONS.md`.

### 8.2 Data storage and privacy

- Model provider credentials must remain in server-side runtime configuration and secret management, not in frontend bundles.
- This PRD covers provider-side credential use for the pipeline. Final browser-facing API-key architecture remains outside scope.
- Stored provenance should name provider, model, step, and prompt version without storing sensitive secrets.
- AI output reuse keys should be deterministic and inspectable, but they must not expose provider credentials.

### 8.3 Scalability and performance

- The bounded scope remains 17 countries and 6 indicators on a weekly run cadence.
- The two-step chain still produces a manageable number of calls at this scale, so clarity matters more than advanced batching infrastructure.
- Exact-match reuse should lower recurring cost without adding a new cache tier.
- If one model proves too weak for the synthesis step, a step-specific upgrade is acceptable as long as it is documented and evaluated.
- This PRD optimizes for trustworthy output, bounded cost, and reviewability rather than raw inference throughput.

### 8.4 Potential challenges

- An economy-tier baseline may be good enough for indicator narratives but weaker on country synthesis quality.
- Some models are cheaper but less reliable at schema-following or structured reasoning.
- Prompt changes can silently alter output quality if prompt versions are not tracked.
- Reuse logic can become misleading if the fingerprint does not include every behavior-shaping input.
- It is easy to blur provider-secret handling with product auth concerns unless the boundary stays explicit.

## 9. Milestones and sequencing

### 9.1 Project estimate

This is a medium-sized AI-enablement PRD. It is narrower than cloud runtime or full hardening work, but it is substantial because it turns a mocked core product capability into a real one and must do so without inflating complexity or cost.

### 9.2 Team size and composition

- One implementation lane covering provider wiring, evaluation, bounded retry logic, reuse rules, and provenance.
- One review lane checking prompt discipline, schema reliability, groundedness, cost behavior, and boundary alignment with the hardening PRD.

### 9.3 Suggested phases

1. Confirm the live-AI boundary, baseline model choice, and evaluation rubric before implementation starts.
2. Wire Google GenAI `gemma-4-31b-it` behind the existing AI client interface for real runs while keeping deterministic local mode, schema validation, bounded retry behavior, degraded fallback payloads, and minimum provenance fields.
3. Implement evaluation and cost-reporting for the approved 17-country by 6-indicator scope, or a documented temporary subset if live data is not yet fully available.
4. Add exact-match reuse by AI input fingerprint and validate downstream contract compatibility.
5. Re-run the evaluation gate on the full live-data scope and promote to a stronger model for one or both steps only if the baseline fails.

### 9.4 Dependencies

- Live-data integration should be substantially complete before the final live-AI approval gate so model evaluation reflects real source shapes, null handling, and partial-coverage conditions rather than only deterministic fixtures.
- Durable storage and status should be in place before this PRD completes so provider, model, and prompt-version provenance can be validated against the stored-record contract.

## 10. User stories

### 10.1 Replace deterministic development AI with live model calls

- **ID**: US-1
- **Description**: As an evaluator, I want the pipeline to use a real LLM for live runs so that the AI layer is credible rather than simulated.
- **Acceptance criteria**:
  - [x] Real runs use a provider-backed AI client instead of the deterministic development adapter.
  - [x] Deterministic development AI remains available for tests and lightweight local work.
  - [x] The pipeline preserves the current two-step chain shape for indicator analysis and country synthesis.
  - [x] Downstream pipeline code continues to depend on one stable AI interface.

### 10.2 Start with Gemma 4 and upgrade only if evaluation justifies it

- **ID**: US-2
- **Description**: As an engineer, I want the live AI layer to start from a low-cost baseline and upgrade only when evidence justifies it so that cost discipline is built into the design.
- **Acceptance criteria**:
  - [x] The initial live baseline uses Google GenAI with `gemma-4-31b-it`.
  - [x] Any model change from that baseline is documented and tied to evaluation evidence.
  - [x] The implementation keeps the path open to stronger Google, OpenAI, or OpenRouter-backed models if needed.
  - [x] Model promotion does not require rewriting upstream pipeline orchestration.

### 10.3 Keep structured outputs valid and reviewable

- **ID**: US-3
- **Description**: As an engineer, I want live AI outputs to validate against stable schemas so that downstream storage and API contracts remain safe.
- **Acceptance criteria**:
  - [x] Step 1 and Step 2 live outputs validate against the required structured contracts before storage.
  - [x] Validation failures never silently write malformed AI payloads.
  - [x] The system uses bounded retry logic for transient provider or validation errors.
  - [x] Exhausted retries produce an explicit degraded fallback payload rather than fabricated normal output.

### 10.4 Evaluate the baseline before it becomes the default

- **ID**: US-4
- **Description**: As a reviewer, I want model selection to be backed by evidence so that the chosen AI configuration is defensible.
- **Acceptance criteria**:
  - [x] Evaluation covers structured-output validity, groundedness to numeric inputs, synthesis coherence, refusal behavior, latency, and estimated full-run cost.
  - [x] The evaluation corpus uses the full approved 17-country by 6-indicator scope unless a documented temporary subset is agreed before the evaluation phase.
  - [x] The default live model is only approved after passing the documented evaluation gate.
  - [x] A stronger model is only adopted when the baseline fails documented pass criteria.
  - [x] The documented pass criteria are concrete: full 17-country scope with zero fetch failures, 100% schema-valid outputs in both AI steps, 0 degraded fallbacks, 0 refusals, average indicator groundedness >= 0.80, average synthesis coherence >= 0.80, p95 latency <= 8s for Step 1 and <= 15s for Step 2, and estimated full-run cost <= $5.00.
  - [x] The evaluation harness behaves as a gate, not telemetry only: it returns a failing result and exits non-zero when those requirements are not met.

### 10.5 Reuse exact-match AI results to keep cost low

- **ID**: US-5
- **Description**: As an engineer, I want repeated identical AI inputs to reuse prior results so that the product avoids paying twice for the same inference.
- **Acceptance criteria**:
  - [x] Reuse eligibility is determined by an exact-match fingerprint of normalized input content, step name, prompt version, provider, and model.
  - [x] Exact-match reuse avoids a duplicate provider call when the fingerprint matches a prior result.
  - [x] The implementation does not introduce a separate semantic cache or cache service for this phase.
  - [x] Reuse behavior remains inspectable and explainable in code and stored provenance.

### 10.6 Preserve minimum provenance and honest degraded states

- **ID**: US-6
- **Description**: As a reviewer, I want stored AI outputs to show which model produced them and whether coverage was degraded so that the product stays explainable.
- **Acceptance criteria**:
  - [x] Stored AI-backed outputs preserve provider, model, step, and prompt-version provenance.
  - [x] Provider credentials are never exposed in stored records or frontend bundles.
  - [x] Runs with incomplete AI coverage preserve successful outputs but do not appear as fully successful without qualification.
  - [x] Logs and terminal run status make AI degradation explicit.
