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
| AI Chain     | **Two-step contract**                                               | Per-indicator analysis → macro synthesis. Real provider wiring is deferred; the repo still ships a deterministic development adapter. |
| Deployment   | **Cloud Run**                                                       | Scale-to-zero, europe-west1 region.                                                                 |

### Why Not BigQuery?

BigQuery is a data warehouse for analytical queries over large datasets. World Bank Analyst stores JSON-shaped documents and serves them read-heavy to a dashboard. Firestore's `doc.get()` is all the querying needed. Migration to BigQuery is documented as a future path if analytical queries become a requirement.

## Quick Start

Local development defaults to `PIPELINE_MODE=local`, `REPOSITORY_MODE=local`, and `WORLD_ANALYST_API_KEY=local-dev`. `WORLD_ANALYST_STORAGE_BACKEND` remains supported as a backward-compatible alias.
The browser does not send that key directly. The Vite dev proxy injects it server-side, which matches the deployed same-origin proxy story.

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
| API service | `WORLD_ANALYST_RUNTIME_ENV=production`, `REPOSITORY_MODE=firestore`, `GOOGLE_CLOUD_PROJECT`, `WORLD_ANALYST_API_KEY`, `WORLD_ANALYST_ALLOWED_ORIGINS`, optional `WORLD_ANALYST_FIRESTORE_COLLECTION` |
| Pipeline job | `PIPELINE_MODE=live`, `REPOSITORY_MODE=firestore`, `GOOGLE_CLOUD_PROJECT`, `WORLD_ANALYST_RAW_ARCHIVE_BUCKET`, `GEMINI_API_KEY` for the default Google path, optional `WORLD_ANALYST_FIRESTORE_COLLECTION`, `WORLD_ANALYST_AI_PROVIDER`, `WORLD_ANALYST_GEMINI_MODEL`, `WORLD_ANALYST_OPENAI_MODEL`, `WORLD_ANALYST_AI_MAX_ATTEMPTS` |
| Frontend runtime | The frontend already defaults to `/api/v1`; Cloud Run must set `WORLD_ANALYST_API_UPSTREAM` and `WORLD_ANALYST_PROXY_API_KEY` for the nginx same-origin proxy |

Before the first cloud deployment, create or confirm:

1. A GCP project with billing enabled
2. A Firestore Native database in `europe-west1` or the corresponding EU multi-region
3. A GCS bucket for raw World Bank archives
4. A Secret Manager secret for `WORLD_ANALYST_API_KEY`
5. Cloud Run service accounts for the API service, pipeline job, and Cloud Scheduler trigger
6. IAM bindings that give those identities only the roles they need for Firestore, GCS, Secret Manager, and Cloud Run job invocation

See `.agents/workflows/deploy.md` for copy-pasteable service-account, secret-creation, IAM, deploy, and scheduler commands.

Cloud rollout notes:

- `frontend/nginx/default.conf.template` already proxies `/api/v1/` and injects `X-API-Key` server-side. Do not bake the API key into frontend assets.
- Firestore mode requires the paired GCS bucket because stored records keep raw archive references alongside processed documents.
- Live AI now runs through `pipeline/ai_client.py`. The default live baseline is Google GenAI `gemma-4-31b-it` with `GEMINI_API_KEY` supplied server-side; switch providers deliberately with `WORLD_ANALYST_AI_PROVIDER=openai` plus `OPENAI_API_KEY`.

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
