# World Analyst — Copilot Project Instructions

## Project

**World Analyst** is an AI-native economic intelligence terminal. It began in the ML6 Engineering Challenge context and is now held to production-grade quality standards. It fetches World Bank data, processes it through a two-step LLM chain (per-indicator analysis → macro synthesis), and serves structured insights via a Connexion REST API to a React 18 frontend.

## Tech Stack

- **Backend:** Python 3.12 + Connexion (OpenAPI-first framework). API spec lives in `api/openapi.yaml`.
- **Data Processing:** Pandas for statistical analysis (% changes, anomaly detection).
- **AI:** Vertex AI (Gemini) or OpenAI via abstracted `pipeline/ai_client.py`.
- **Storage:** Firestore (processed insights) + GCS (raw backups). NOT BigQuery.
- **Frontend:** React 18 + Vite. Vanilla CSS with CSS custom properties. No Tailwind.
- **Charts:** Recharts (line/bar) + react-simple-maps (choropleth).
- **Deployment:** Cloud Run (3 services) in `europe-west1`. Scale-to-zero.
- **Auth:** API Key in `X-API-Key` header, stored in GCP Secret Manager.

## Design System — Hard Rules

The canonical design system is defined in `.github/skills/world-analyst-design-system/SKILL.md`. Read it before any frontend or UI work. Quick reference: dark canvas `#0E0E0E`, cards `#1A1A1A`, accent `#FF4500` (AI only), 8px radius, no shadows, Inter + Commit Mono, vanilla CSS custom properties.

## Architecture Patterns

- **Spec-Driven Development:** `openapi.yaml` defines routes. Connexion wires them. Handlers implement them. Never write a route that isn't in the spec first.
- **Two-Step AI Chain:** Step 1 = per-indicator analysis (structured JSON). Step 2 = macro synthesis (executive summary + risk flags). Pandas handles the math; LLM writes the narrative.
- **Push Mechanism:** Data is pushed to Firestore on a schedule (Cloud Scheduler + Cloud Run Job), never fetched on page load.

## Agent Workflow

- For non-trivial code-changing work, prefer a manager-style workflow: keep ownership in the main conversation and run an implementation lane plus an independent review lane in parallel when tool support allows.
- The implementation lane should optimize for minimal validated changes. The review lane should stay focused on drift and quality: spec drift, design-system drift, missing tests, regressions, and missing ADR updates.
- Prefer a different model for the review lane when custom agents can pin one. Treat model diversity as a fault-detection aid, not a substitute for validation.
- Skip the parallel review lane for trivial or read-only requests where the extra latency and context overhead would outweigh the benefit.
- Aim for production-ready clarity in the code itself. Use docstrings plus targeted inline comments whenever business rules, orchestration, or state transitions would otherwise be hard to explain during review or presentation.

## Code Style

- Python: `ruff format`, `ruff check`, Google-style docstrings, type hints on all functions, and brief inline comments where thresholds, orchestration, or contract shaping are not obvious from names alone.
- JavaScript: Prettier, ESLint, functional components, named exports, CSS custom properties, and concise file or section comments when derived state or data flow would otherwise be hard to follow.
- No `console.log` or `print()` in production — use proper logging.
- No commented-out code. No TODO without a plan reference.
- Code should be presentation-ready: a reviewer should understand intent from names, docstrings, and targeted comments without needing chat history.

## Project-Specific Skills

Read these for domain guidance before writing code in their area:
- `.github/skills/world-analyst-design-system/SKILL.md` — Frontend/UI work
- `.github/skills/connexion-api-development/SKILL.md` — API development
- `.github/skills/world-analyst-engineering/SKILL.md` — Architecture, testing, quality
- `.github/skills/world-bank-api/SKILL.md` — Pipeline data fetching, indicator codes, API response format
- `.github/skills/llm-prompting-and-evaluation/SKILL.md` — AI prompts, structured output, LLM-as-Judge evaluation
- `.github/skills/humanizer-pro/SKILL.md` — ADRs, README prose, presentation copy, user-facing narratives, and other writing that must sound direct and credible

## File Structure

- `api/` — Connexion backend (openapi.yaml, app.py, handlers/)
- `pipeline/` — Data pipeline (fetcher, analyser, ai_client, storage)
- `frontend/` — React 18 + Vite (pages, components, index.css)
- `Design Mockups/` — Design tokens and visual references
- `Project Context/` — Architecture decisions and ML6 context

## Testing Philosophy

Tests prove business requirements, not coverage metrics. Example: "Does the pipeline flag GDP drops > 3% as anomalies?" > "Does the function return 200 OK?"

## Decision Logging

When choosing between viable alternatives, **always** append an entry to `docs/DECISIONS.md`. Use the ADR template defined in `.agents/workflows/decision.md`. Every trade-off that a reviewer might question must be documented.

