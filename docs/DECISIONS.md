# Architecture Decision Record

> Key trade-offs made during development. Not what we built — why we made specific choices when reasonable alternatives existed.
>
> This file keeps the 20 active fork-in-the-road decisions. Older notes stay in local working history rather than the repo.

---

## ADR-001: Firestore over BigQuery

**Decision:** Firestore for processed insights, GCS for raw backup.

**Why:** The data shape is a JSON document per country-indicator pair. Access pattern is key-value lookup (`doc.get()`), not analytical queries. BigQuery's strength — columnar scanning across millions of rows — is irrelevant here. We have ~100 documents refreshed monthly.

**Trade-off:** If analytical queries become a requirement (cross-country time-series comparison), that's the migration trigger. Documented as a future path in ADR-060.

---

## ADR-002: Two-Step AI Chain (Not Single-Pass)

**Decision:** Per-indicator analysis (Step 1) → macro synthesis (Step 2). Not one combined pass.

**Why:**
1. **Token efficiency.** Each Step 1 call processes ~200 tokens. A single-pass call with 6 indicators needs ~1,200 tokens, raising the chance the model conflates unrelated indicators.
2. **Parallelism.** Step 1 calls are independent and run concurrently. Step 2 waits but only processes ~6 small JSON objects.
3. **Debuggability.** If the LLM misfires on a trend, trace it to one indicator call with one input. Single-pass buries that.

**Trade-off:** More API calls — 17 × 6 = 102 Step 1 calls + 17 Step 2 calls = 119 total per run. At Gemma 4 pricing the full run costs ~$0.012. Negligible.

---

## ADR-003: Schema-Constrained Output (Not Prompt-Based JSON)

**Decision:** Use `response_json_schema` (Gemini) and `response_format` with `strict: true` (OpenAI). No prompt-based JSON instructions.

**Why:** Prompt-based enforcement works 90% of the time, then produces ` ```json\n{...}``` ` wrapped output or drops required fields. Schema-constrained output is enforced at the token level — structurally invalid JSON cannot be generated.

**Trade-off:** Requires Pydantic schemas upfront. The schema lives in code, versioned and testable. Worth the setup cost.

---

## ADR-004: Connexion over FastAPI

**Decision:** Connexion, routing from `api/openapi.yaml` as the authoritative contract.

**Why:** The challenge values spec-driven development. With Connexion, the spec leads — handlers implement what the spec declares. With FastAPI, the code generates the spec. For a project demonstrating engineering rigor, spec-first is the right signal.

**Trade-off:** Smaller community, fewer tutorials, weaker async support than FastAPI. For 6 endpoints at demo scale, none of those gaps matter.

---

## ADR-005: Vanilla CSS over Tailwind

**Decision:** Vanilla CSS with CSS custom properties.

**Why:** The design system uses explicit tokens — exact hex values, exact spacing, exact typography. Tailwind abstracts `var(--surface-card)` behind `bg-gray-900`. A reviewer opening `index.css` sees the full design system in one file, exactly as specified.

**Trade-off:** More CSS to write by hand. Slower for prototyping, clearer for audit.

---

## ADR-008: Finance-First, Presentation-Scoped Dashboard

**Decision:** Optimize for finance users, bounded demo scope, and human-readable output. Lead KPI and narrative design with risk-weighted signals: sovereign risk, inflationary pressure, fiscal stress, external vulnerability, recessionary signal.

**Why:** Finance users don't need indicator definitions — they need risk framing, trend magnitude, and anomaly context. The evaluation rewards scope discipline over infrastructure ambition.

**Trade-off:** Less suited to general audiences or downstream machine integration. Accepted constraint given the evaluation criteria.

---

## ADR-020: Partial-Success Live Runs Preserve Good Data

**Decision:** Preserve successful outputs from a partial run. Terminal pipeline status stays `failed` when coverage is incomplete.

**Why:** Throwing away valid data because one country or indicator fails is worse than showing partial results. `failed` terminal status preserves honesty without expanding the status contract.

**Trade-off:** Dashboard may show partially refreshed data after a failed run. Coverage gap is visible through status and logs.

---

## ADR-021: Cloud Run Jobs API for Manual Pipeline Dispatch

**Decision:** `POST /pipeline/trigger` dispatches a Cloud Run Job execution when `WORLD_ANALYST_PIPELINE_DISPATCH_MODE=cloud`.

**Why:** Direct, reviewable, fits scale-to-zero. The API dispatches one job and gets immediate platform feedback — no separate queueing system needed at this scope.

**Trade-off:** API service account needs `roles/run.developer` for override-based dispatch. IAM scope stays within Cloud Run.

---

## ADR-022: Firestore Transaction for Trigger Idempotency

**Decision:** Firestore transaction checks the current pipeline status and claims the next run before dispatching. Returns `409 Conflict` if a run is already active.

**Why:** The product already depends on Firestore-backed status. Reusing it for idempotency avoids a second coordination mechanism and keeps the behavior correct across stateless API instances.

**Trade-off:** Small latency overhead on the trigger path. Correct behavior over speed here.

---

## ADR-024: Monthly Scheduler Cadence

**Decision:** Cloud Scheduler triggers the pipeline job monthly (first Monday of each month, 06:00 UTC).

**Why:** World Bank indicator data is published annually, often with a 1–2 year lag. Weekly or daily polling produces only redundant upserts. Monthly keeps the push story honest. The manual trigger on the Pipeline Trigger page is the primary evaluation mechanism.

**Trade-off:** Dashboard can lag a source update by weeks. The source itself isn't real-time — that lag is honest, not a product failure.

---

## ADR-026: Economy-First Live AI Baseline with Gemma 4

**Decision:** Default to Google GenAI `gemma-4-31b-it`. Promote to a stronger model only when evaluation evidence shows the baseline is insufficient.

**Why:** Keeps cost discipline in the design from the start. $0.012 per full 17-country run leaves 430× headroom before the $5.00 gate threshold. Model upgrades are evidence-based, not preference-based.

**Trade-off:** The cheapest baseline may be weaker on structured reliability or nuanced macro synthesis. The evaluation gate in `pipeline/evaluation.py` catches this before any promotion decision.

---

## ADR-028: `europe-west1` as the Deployment Region

**Decision:** All Cloud Run services, Cloud Run Jobs, and Firestore in `europe-west1`.

**Why:** Aligns with ML6's Belgian home market, keeps the demo story regionally coherent, straightforward to justify in presentation.

**Trade-off:** Not latency-optimized for global users. Acceptable for one primary demo environment.

---

## ADR-029: Server-Side Frontend Proxy Over Browser-Held API Key

**Decision:** The deployed frontend calls the API through a same-origin `/api/v1` proxy. The nginx runtime injects `X-API-Key` server-side. The browser never holds the key.

**Why:** A browser-held shared secret is exposed immediately in the bundle or network traffic. Same-origin proxy closes that gap without introducing OAuth or a user-account model for a bounded demo.

**Trade-off:** Frontend deployment gains proxy configuration and an extra request hop. API still uses a shared secret rather than per-user auth — accepted at this scope.

---

## ADR-041: Replace ML6-Market Scope With a 2024 Exact-Complete 17-Country Core Panel

**Context:** The original 15-country ML6-market set produced repeated debt-coverage failures and stale-series exceptions in live runs. A feasibility scan showed that no country has five consecutive fully complete years across all six indicators ending at 2025. Exactly 17 countries have a fully complete 15-year span ending at 2024.

**Decision:** Active monitored set: **BR, CA, GB, US, BS, CO, SV, GE, HU, MY, NZ, RU, SG, ES, CH, TR, UY**. Data window: 2010–2024. Supersedes ADR-006, ADR-019, and ADR-037.

**Why:** Smallest scope change that makes the live backend honest and comparable. The selection is mechanically derived from the data-completeness rule — not editorially chosen. This preserves the six-indicator macro story and gives the pipeline one defensible balanced panel.

**Trade-off:** No Africa, MENA, or South Asia coverage. Russia is included because the shortlist is data-driven. If future goals require broader regional representation, that belongs in a second-tier watchlist with explicit partial-coverage rules — not by weakening the exact-complete core panel.

---

## ADR-044: Per-Indicator Z-Score Anomaly Detection Over a Fixed Threshold

**Decision:** Replace the fixed 3% change constant with a cross-panel z-score per indicator. Compute mean and std of year-over-year percent change across all 17 countries per indicator, flag `|z| >= 2.0`. Pass `z_score` into LLM context.

**Why:** A uniform 3% threshold applied to GDP growth, CPI, unemployment, debt-to-GDP, current account, and broad money is wrong by construction — each has a completely different natural volatility range. Z-score anchors each indicator against its own cross-panel distribution. 2.0σ maps to the outer ~5% — a conventional, defensible threshold in quantitative finance.

**Trade-off:** Cross-panel pooling requires a reasonably complete panel. A zero-std guard handles degenerate cases. If panel coverage shrinks significantly, std becomes unreliable.

---

## ADR-046: `pipeline/evaluation.py` as the Live-AI Approval Gate

**Decision:** The evaluation script is the repo-owned approval gate for the live AI baseline. Exits non-zero if quality misses the documented bar. Runs the full 17-country × 6-indicator scope and estimates run cost.

Gate thresholds: groundedness ≥ 0.8, coherence ≥ 0.8, p95 latency ≤ 8s, cost ≤ $5.00/run.
Baseline results: groundedness 0.936, coherence 1.0, p95 ~7.7s, cost $0.01165.

**Why:** Makes model approval reproducible from the repo. Cost, latency, and quality are explicit at the same boundary where provider selection lives.

**Trade-off:** Gate runs add live inference and judge-scoring overhead. Pricing tables need refreshing when provider rates change. Sign-off is infrequent — the cost is justified.

---

## ADR-057: Temperature=0 for Gemma 4

**Decision:** Keep `temperature=0` for all Gemma 4 calls in `ai_client.py`.

**Why:** Empirical: at `temperature=0`, schema validity was 100% with 0 degraded responses. Higher temperatures caused residual markdown fence wrapping, triggering `repair_markdown_fences()` more frequently. Gemma 4 behaves differently from Gemini 3 — this is per-model evidence, not an assumed default.

**Trade-off:** Less output variance; narratives may be more uniform across runs. `repair_markdown_fences()` remains as a safety net regardless.

---

## ADR-060: Persist Historical Time Series in Firestore (BigQuery Migration Trigger)

**Decision:** Store the full 2010–2024 time series as a nested array in the existing Firestore country documents. No BigQuery migration at this scope.

**Why:** Access pattern is still key-value: load one country document, render its indicator history. That's a `doc.get()` call. Data growth is ~5.4KB of additional payload per country document, ~92KB across all 17 countries — well within Firestore's 1MB document limit.

**Trade-off:** If a future feature requires cross-country time-series comparison (overlay GDP for three markets simultaneously), Firestore requires N fetches and client-side joining. That would be the migration trigger. The current single-country timeline view doesn't cross that line.

---

## ADR-061: Rule-Based Regime Classification Over LLM-Derived Labels

**Decision:** Derive economic regime labels (recovery, expansion, overheating, contraction, stagnation) from Pandas rules on GDP growth, inflation, and unemployment in `pipeline/analyser.py`. No additional LLM call.

**Why:** The label is a structural classification, not a narrative judgment. All three inputs are already computed in the statistical pass. A deterministic mapping to five labels is testable and auditable. The LLM synthesis already contextualizes it in prose — a separate classification call would be redundant and non-deterministic.

**Trade-off:** Less nuanced than LLM judgment on edge cases. The label is directional context, not investment advice. Deterministic rules are easier to defend in review than "the model said so."

---

## ADR-062: Demo Walkthrough as Frontend-Only Simulation

**Decision:** The Pipeline Trigger demo walkthrough animates through `PIPELINE_STAGES` without making any API calls. Clearly labeled as a frontend simulation. The backend never returns fake data.

**Why:** A mock backend mode would contaminate `/pipeline/status` and create ambiguity between real and simulated state. Frontend-only simulation keeps the truth boundary clean: API data is real, browser-animated data is labeled as demo.

**Trade-off:** The walkthrough can't show real Firestore writes or actual LLM latency patterns. Acceptable — its purpose is to explain structure, not simulate performance.

---

## ADR-063: Indicator-Aware Movement Units for Anomaly Detection

**Decision:** Keep legacy `percent_change` for compatibility, but move anomaly scoring and UI semantics to a new canonical pair: `change_value` + `change_basis`. Use relative percent for level series such as GDP in current US$, and percentage-point deltas for rate and ratio indicators such as inflation, unemployment, debt-to-GDP, GDP growth, and current account balance. Also expose `signal_polarity` and `anomaly_basis` so the frontend can describe whether a move is favorable and why it was flagged.

**Why:** ADR-044 fixed the old one-size-fits-all threshold problem, but it still assumed that year-over-year percent change was the right input for every indicator. It is not. A move from 3% inflation to 6% inflation is economically a +3 percentage-point move, not a +100% move. The same issue applies to unemployment, debt-to-GDP, GDP growth, and current account balance. Keeping `percent_change` unchanged avoids a silent contract break for existing consumers and stored records.

**Trade-off:** The contract is wider and the statistical layer carries more metadata. That is a worthwhile cost because the anomaly math now matches the economics of the underlying series, and the country page can show direction-of-travel in a way that is accurate instead of sign-based guesswork. This ADR refines ADR-044 rather than replacing it.
