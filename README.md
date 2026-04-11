# World Analyst

> AI-native global economic intelligence terminal for the ML6 Engineering Challenge.

## What This Is

World Analyst fetches economic data from the World Bank, processes it through a two-step LLM analysis chain, and serves structured insights via a Connexion REST API to a React frontend.

**Python + Pandas handles the math. The LLM writes the analyst report.**

Pandas detects _that_ GDP dropped 4.2%. The LLM explains _why_ — what it means, what drives it, what the risk flags are.

## Why This Repo Tracks More Than Code

This repository is meant to show both the product and the working method behind it. The tracked surface is intentionally broader than a runtime-only app repository.

- Product code lives in `api/`, `pipeline/`, `frontend/`, and `shared/`.
- The paper trail lives in `docs/`, `docs/prds/`, `docs/plans/`, `Design Mockups/`, and `Project Context/`.
- The AI workflow assets live in `.github/`, `.agents/`, `AGENTS.md`, and `GEMINI.md`.

That mix is deliberate. The challenge is partly about whether the repo can explain why decisions were made, how AI was used, and what was kept out of scope.

## Current Product Constraints

World Analyst is designed for a finance team, not a general business audience. The dashboard should assume fluency in macro indicators and focus on risk interpretation: direction of travel, magnitude of change, and whether a move is anomalous relative to history. AI narratives should use finance vocabulary such as sovereign risk, inflationary pressure, fiscal stress, external vulnerability, and recessionary signal.

The delivery scope remains deliberately bounded around 15 countries, 6 indicators, one Cloud Run job, and one Firestore collection. Those are scope guardrails, not permission for shortcut engineering: implementations should be production-grade in readability, inline documentation, validation, and decision logging. The API and stored documents are optimized for human-readable dashboard rendering rather than downstream machine integration, so prose-forward insight fields are preferred unless the frontend needs structured values for specific UI elements.

## Architecture

The deployed target is Firestore plus GCS, but local development currently defaults to the in-memory repository so the vertical slice can run without cloud dependencies.

```text
World Bank API → Cloud Run Job (Python + Pandas)
    → AI Chain (Gemini/OpenAI: indicator analysis → macro synthesis)
    → Firestore (insights) + GCS (raw backup)
    → Connexion REST API
    → React Frontend (World Analyst Dashboard)
```

### Three Services

| Service                  | Technology            | Role                                                         |
| ------------------------ | --------------------- | ------------------------------------------------------------ |
| `world-analyst-api`      | Python + Connexion    | REST API serving insights from the active repository backend |
| `world-analyst-pipeline` | Python + Pandas + LLM | Data fetch → analysis → storage pipeline                     |
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
| AI Chain     | **Two-step**                                                        | Per-indicator analysis → macro synthesis. Prevents context collapse.                                |
| Deployment   | **Cloud Run**                                                       | Scale-to-zero, europe-west1 region.                                                                 |

### Why Not BigQuery?

BigQuery is a data warehouse for analytical queries over large datasets. World Analyst stores JSON-shaped documents and serves them read-heavy to a dashboard. Firestore's `doc.get()` is all the querying needed. Migration to BigQuery is documented as a future path if analytical queries become a requirement.

## Quick Start

Local development defaults to `WORLD_ANALYST_STORAGE_BACKEND=local` and `WORLD_ANALYST_API_KEY=local-dev`.

```bash
# Backend
cd api && pip install -r requirements.txt
export WORLD_ANALYST_API_KEY=local-dev
python app.py

# Pipeline
cd pipeline && pip install -r requirements.txt
python main.py

# Frontend
cd frontend && npm install
npm run dev
```

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

## Git Workflow

This repo should read as an audit trail, not a file dump. Keep commits small and intention-revealing so a reviewer can follow repo hygiene, design decisions, tests, and behavior changes without reconstructing intent from chat history.

When a trade-off would matter in review, log it in `docs/DECISIONS.md`. When a change affects how we stage, split, or curate work into git, use `CONTRIBUTING.md` as the working agreement.

## Design System

See `Design Mockups/Design System.md` for the full specification. Key constraints:

- Dark canvas (`#0E0E0E`), no shadows, no blur
- `#FF4500` accent reserved for AI insights and primary CTAs
- Inter (text) + Commit Mono (data/metrics)
- 8px border-radius everywhere
- 32px vertical rhythm between sections

## Documentation

| Document                                   | What It Answers                                                  |
| ------------------------------------------ | ---------------------------------------------------------------- |
| `docs/DECISIONS.md`                        | **Why** — trade-offs, alternatives considered, rationale         |
| `CONTRIBUTING.md`                          | How we stage, split, and curate commits into a clear audit trail |
| `Project Context/WORLD_ANALYST_PROJECT.md` | Full project brief, data model, pipeline architecture            |
| `.github/skills/`                          | Domain-specific guidance for each area of the codebase           |
| `Design Mockups/Design System.md`          | Complete design token specification                              |

## Engineering Principles

This project follows ML6's AI Native Way of Working:

1. **Intent-First Development** — Decisions documented before code
2. **PaperTrail of Context** — Context lives in the repo, not in chats
3. **Absolute Ownership** — Every line explainable and defensible, with docstrings and targeted comments wherever the code would otherwise hide intent
4. **Business-Driven Testing** — Tests prove business requirements

---

_Built as a demonstration of the ML6 AI Native Way of Working._
