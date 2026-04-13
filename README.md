# World Bank Analyst

> AI-native global economic intelligence terminal for the ML6 Engineering Challenge.

## What This Is

World Bank Analyst pulls economic data from the World Bank, processes it through a two-step LLM analysis chain, and serves structured insights through a Connexion REST API to a React frontend.

**Python + Pandas handles the math. The LLM writes the analyst report.**

Pandas detects _that_ GDP dropped 4.2%. The LLM explains _why_ — what it means, what drives it, what the risk flags are.

## Why This Repo Tracks More Than Code

This repository is meant to show both the product and the working method behind it. The tracked surface is intentionally broader than a runtime-only app repository.

- Product code lives in `api/`, `pipeline/`, `frontend/`, and `shared/`.
- The paper trail lives in `docs/`, `docs/prds/`, `docs/plans/`, `docs/design-mockups/`, and `docs/context/`.
- Scoped workflow assets live in `.github/`, `.agents/`, `AGENTS.md`, and `GEMINI.md`.

That mix is deliberate. The challenge is partly about whether the repo can explain why decisions were made, how AI was used, and what was kept out of scope.

## Current Product Constraints

World Bank Analyst is designed for a finance team, not a general business audience. The dashboard should assume fluency in macro indicators and focus on risk interpretation: direction of travel, magnitude of change, and whether a move is anomalous relative to history. AI narratives should use finance vocabulary such as sovereign risk, inflationary pressure, fiscal stress, external vulnerability, and recessionary signal.

The delivery scope remains deliberately bounded around a 17-country exact-complete core panel ending at 2024, 6 indicators, one Cloud Run job, and one Firestore collection. That core panel prioritizes comparable live coverage over broad regional representation. Those are scope guardrails, not permission for shortcut engineering: implementations should be production-grade in readability, inline documentation, validation, and decision logging. The API and stored documents are optimized for human-readable dashboard rendering rather than downstream machine integration, so prose-forward insight fields are preferred unless the frontend needs structured values for specific UI elements.

## Architecture

The deployed target is Firestore plus GCS, but repo defaults stay local and deterministic until Cloud Run env vars opt into live data and durable storage explicitly.

```text
World Bank API → Cloud Run Job (Python + Pandas)
    → Two-step synthesis contract
    → Firestore (insights) + GCS (raw backup)
    → Connexion REST API
    → React Frontend (World Bank Analyst Dashboard)
```

The 17-country monitored panel is not an editorial shortlist. It is the smallest World Bank 2024 exact-complete set with full 2010-2024 coverage across all six indicators, which is why Bahamas and El Salvador stay in scope while larger economies with missing series do not. That rule keeps the live demo comparable across every market in the panel instead of mixing complete and partial histories. See [ADR-041](docs/DECISIONS.md#adr-041-replace-ml6-market-scope-with-a-2024-exact-complete-17-country-core-panel).

### Three Services

| Service                  | Technology            | Role                                                         |
| ------------------------ | --------------------- | ------------------------------------------------------------ |
| `world-analyst-api`      | Python + Connexion    | REST API serving insights from the active repository backend |
| `world-analyst-pipeline` | Python + Pandas       | Data fetch → analysis → storage pipeline                     |
| `world-analyst-frontend` | React 18 + Vite       | Dashboard served via nginx                                   |

### Four Pages

| Page                 | Route          | Purpose                       |
| -------------------- | -------------- | ----------------------------- |
| Global Overview      | `/`            | KPIs, world map, market depth |
| Country Intelligence | `/country/:id` | Per-country deep dive         |
| How It Works         | `/pipeline`    | Architecture explainer        |
| Pipeline Trigger     | `/trigger`     | Live execution UI             |

## Tech Decisions

| Decision     | Choice                                                              | Rationale                                                                                           |
| ------------ | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Storage      | **Local in-memory for development; Firestore + GCS for deployment** | Local runs stay dependency-light, while the deployed target remains document-shaped and read-heavy. |
| Backend      | **Connexion**                                                       | OpenAPI-first, contract-enforced routing. Spec is source of truth.                                  |
| Frontend CSS | **Vanilla CSS**                                                     | Design system uses explicit tokens. No Tailwind, no frameworks.                                     |
| AI Chain     | **Two-step contract**                                               | Per-indicator analysis → macro synthesis. Live runs now use provider-backed AI, while local runs stay deterministic for tests and lightweight development. |
| Deployment   | **Cloud Run**                                                       | Scale-to-zero, europe-west1 region.                                                                 |

### Why Not BigQuery?

BigQuery is a data warehouse for analytical queries over large datasets. World Bank Analyst stores JSON-shaped documents and serves them read-heavy to a dashboard. Firestore's `doc.get()` is all the querying needed. Migration to BigQuery is documented as a future path if analytical queries become a requirement.

## Quick Start

Local development defaults to `PIPELINE_MODE=local`, `REPOSITORY_MODE=local`, and `WORLD_ANALYST_API_KEY=local-dev`. `WORLD_ANALYST_STORAGE_BACKEND` remains supported as a backward-compatible alias.
The browser does not send that key directly. The Vite dev proxy injects `local-dev` server-side by default (or `WORLD_ANALYST_DEV_PROXY_API_KEY` when a non-default local proxy key is needed), which matches the deployed same-origin proxy story.

```bash
# Backend
cd api && pip install -r requirements.txt
export WORLD_ANALYST_API_KEY=local-dev
export PIPELINE_MODE=local
python app.py

# Pipeline
cd pipeline && pip install -r requirements.txt
export PIPELINE_MODE=local
python main.py

# Frontend
cd frontend && npm install
npm run dev
```

For deployed runtimes, keep the code default local and set the cloud services explicitly instead:

| Surface | Required runtime/build configuration |
| --- | --- |
| API service | `WORLD_ANALYST_RUNTIME_ENV=production`, `REPOSITORY_MODE=firestore`, `GOOGLE_CLOUD_PROJECT`, `WORLD_ANALYST_API_KEY`, `WORLD_ANALYST_ALLOWED_ORIGINS`, `WORLD_ANALYST_PIPELINE_DISPATCH_MODE=cloud`, `WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID`, `WORLD_ANALYST_PIPELINE_JOB_REGION`, `WORLD_ANALYST_PIPELINE_JOB_NAME`, optional `WORLD_ANALYST_FIRESTORE_COLLECTION`, `WORLD_ANALYST_PIPELINE_JOB_CONTAINER_NAME` |
| Pipeline job | `PIPELINE_MODE=live`, `REPOSITORY_MODE=firestore`, `GOOGLE_CLOUD_PROJECT`, `WORLD_ANALYST_RAW_ARCHIVE_BUCKET`, `GEMINI_API_KEY` for the default Google path, optional `WORLD_ANALYST_FIRESTORE_COLLECTION`, `WORLD_ANALYST_AI_PROVIDER`, `WORLD_ANALYST_GEMINI_MODEL`, `WORLD_ANALYST_OPENAI_MODEL`, `WORLD_ANALYST_AI_MAX_ATTEMPTS` |
| Frontend runtime | The frontend already defaults to `/api/v1`; Cloud Run must set `WORLD_ANALYST_RUNTIME_ENV=production`, `WORLD_ANALYST_API_UPSTREAM`, and `WORLD_ANALYST_PROXY_API_KEY` for the nginx same-origin proxy, and the frontend service account must be able to read that secret at runtime |

Example cloud configuration values for this repo:

- `WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID=world-bank-analyst`
- `WORLD_ANALYST_PIPELINE_JOB_REGION=europe-west1`
- `WORLD_ANALYST_RAW_ARCHIVE_BUCKET=world-bank-analyst-raw-markus-euw1`
- Secret names: `world-analyst-api-key` for the shared API key and `world-analyst-gemini-api-key` for the AI provider key

Before the first cloud deployment, create or confirm:

1. A GCP project with billing enabled
2. A Firestore Native database in `europe-west1` or the corresponding EU multi-region
3. A GCS bucket for raw World Bank archives
4. A Secret Manager secret for `WORLD_ANALYST_API_KEY`
5. Cloud Run service accounts for the API service, frontend service, pipeline job, and Cloud Scheduler trigger
6. IAM bindings that give those identities the roles they need for Firestore, GCS, Secret Manager, and Cloud Run job execution

See `.agents/workflows/deploy.md` for copy-pasteable service-account, secret-creation, IAM, deploy, and scheduler commands.

Treat that workflow as the developer-facing deployment source of truth. It now documents both the commands and the rollout lessons that actually mattered in practice: repo-root image builds, override-based Cloud Run Job IAM, the scheduler OAuth scope, the frontend proxy runtime split, and the smoke gate that proves the deployment is real.

Cloud rollout notes:

- `frontend/nginx/default.conf.template` already proxies `/api/v1/` and injects `X-API-Key` server-side. Do not bake the API key into frontend assets.
- `POST /api/v1/pipeline/trigger` stays on the deterministic local thread path unless `WORLD_ANALYST_PIPELINE_DISPATCH_MODE=cloud` is set explicitly.
- Cloud dispatch requires explicit job coordinates: `WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID`, `WORLD_ANALYST_PIPELINE_JOB_REGION`, and `WORLD_ANALYST_PIPELINE_JOB_NAME`. The trigger passes `WORLD_ANALYST_PIPELINE_RUN_ID` and `WORLD_ANALYST_PIPELINE_COUNTRY_CODE` into the job execution as runtime overrides.
- The frontend Cloud Run service should use its own service account with Secret Manager access because nginx reads `WORLD_ANALYST_PROXY_API_KEY` at runtime.
- The frontend container keeps local-friendly proxy defaults only for explicit local runtimes. In Cloud Run, set `WORLD_ANALYST_RUNTIME_ENV=production` so startup fails fast if the upstream or proxy key is left on the local fallback.
- The API service account needs `run.jobs.runWithOverrides` for the override-based trigger path; the built-in role used in the live rollout is `roles/run.developer`, not `roles/run.invoker`.
- The Cloud Scheduler job creation command should include `--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform` when targeting the Cloud Run Jobs API.
- Firestore mode requires the paired GCS bucket because stored records keep raw archive references alongside processed documents.
- Live AI now runs through `pipeline/ai_client.py`. The default live baseline is Google GenAI `gemma-4-31b-it` with `GEMINI_API_KEY` supplied server-side; switch providers deliberately with `WORLD_ANALYST_AI_PROVIDER=openai` plus `OPENAI_API_KEY`.

Container entry points for Cloud Run builds now live in `api/Dockerfile`, `pipeline/Dockerfile`, and `frontend/Dockerfile`. The API container now serves the Connexion app through Gunicorn via `api/wsgi.py` instead of the Flask development server.

## Development

```bash
# Lint
ruff check api/ pipeline/
cd frontend && npm run lint

# Test
cd api && pytest tests/ -v
cd pipeline && pytest tests/ -v
cd frontend && npm run test:overview
```

Opt-in live World Bank smoke:

```bash
cd pipeline && WORLD_ANALYST_RUN_LIVE_TESTS=1 pytest tests/test_live_world_bank_integration.py -v
```

Live AI evaluation gate:

```bash
# From the repo root. Exits non-zero when the Gemma 4 baseline misses the
# documented live-AI gate. Uses the built-in rubric by default; add
# --judge-model gemma-4-31b-it when you want a live Google judge overlay too.
python -m pipeline.evaluation
```

## Reviewer Quick Path

| If you want to validate... | Start here |
| --- | --- |
| The challenge fit and why the repo is shaped this way | `docs/context/world-analyst-project.md` |
| The cloud deployment and smoke gate | `.agents/workflows/deploy.md` |
| The AI-native workflow and agentic repo setup | `docs/AI_NATIVE_WORKFLOW.md`, `.github/agents/`, `.github/prompts/`, `.github/instructions/` |
| The shipped feature and architecture phases | `docs/prds/` |
| The trade-offs behind the current shape | `docs/DECISIONS.md` |

The live frontend and API URLs are rollout outputs rather than stable repo constants. Before the presentation handoff, capture the active `FRONTEND_URL` and `API_ORIGIN` from the latest successful Cloud Run rollout and smoke gate so the reviewer gets one current entry point instead of an outdated hardcoded link.

## Git Workflow

This repo should read as an audit trail, not a file dump. Keep commits small and intention-revealing so a reviewer can follow repo hygiene, design decisions, tests, and behavior changes without reconstructing intent from chat history.

When a trade-off would matter in review, log it in `docs/DECISIONS.md`. When a change affects how we stage, split, or curate work into git, use `CONTRIBUTING.md` as the working agreement.

## Design System

See `docs/design-mockups/Design System.md` for the full specification. Key constraints:

- Dark canvas (`#0E0E0E`), no shadows, no blur
- `#FF4500` accent reserved for AI insights and primary CTAs
- Inter (text) + Commit Mono (data/metrics)
- 8px border-radius everywhere
- 32px vertical rhythm between sections

## Documentation

| Document                                | What It Answers                                                  |
| --------------------------------------- | ---------------------------------------------------------------- |
| `docs/DECISIONS.md`                     | **Why** — trade-offs, alternatives considered, rationale         |
| `CONTRIBUTING.md`                       | How we stage, split, and curate commits into a clear audit trail |
| `docs/context/world-analyst-project.md` | Full project brief, data model, pipeline architecture            |
| `.agents/workflows/deploy.md`           | Deployment commands, required GCP resources, and the smoke gate  |
| `docs/AI_NATIVE_WORKFLOW.md`            | How the repo demonstrates an AI-native way of working            |
| `docs/prds/`                            | Shipped phases and scoped product/architecture decisions         |
| `.github/skills/`                       | Domain-specific guidance for each area of the codebase           |
| `docs/design-mockups/Design System.md`  | Complete design token specification                              |

## Engineering Principles

This project follows ML6's AI Native Way of Working:

1. **Intent-First Development** — Decisions documented before code
2. **PaperTrail of Context** — Context lives in the repo, not in chats
3. **Absolute Ownership** — Every line explainable and defensible, with docstrings and targeted comments wherever the code would otherwise hide intent
4. **Business-Driven Testing** — Tests prove business requirements

---

_Built as a demonstration of the ML6 AI Native Way of Working._
