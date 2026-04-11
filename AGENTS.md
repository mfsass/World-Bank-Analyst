# World Analyst — Agent Instructions

## Project

AI-native economic intelligence terminal. Python/Connexion backend + React 18 frontend + two-step LLM analysis pipeline.

## Core Constraints

1. API spec lives in `api/openapi.yaml`. Connexion reads it. Never create routes outside the spec.
2. Design system defined in `.github/skills/world-analyst-design-system/SKILL.md`. Key tokens: `#0E0E0E` canvas, `#FF4500` accent, 8px radius, no shadows, Inter + Commit Mono, vanilla CSS custom properties only.
3. Firestore for persistence. Not BigQuery.
4. All Python functions must have type hints and docstrings.
5. Add concise inline comments whenever business rules, orchestration, thresholds, or state transitions are not obvious from the code alone. Comments should explain why, not restate syntax.
6. Tests must validate business outcomes, not implementation details.
7. **Log decisions.** When choosing between viable alternatives, append to `docs/DECISIONS.md` using the ADR template. Run `/decision` or append manually. No trade-off goes undocumented.

## Delivery Workflow

- For substantive implementation work, default to a dual-lane workflow: one implementation lane makes the change while one independent review lane audits for spec drift, design-system drift, missing tests, regressions, and ADR gaps.
- Keep the main conversation as the coordinator. It should synthesize the final answer after reconciling both lanes rather than handing ownership away permanently.
- Prefer a different model for the review lane when the platform supports per-agent model selection. Diversity is useful for catching blind spots, but correctness still comes from validation and evidence.
- Do **not** pay the orchestration tax on trivial tasks. Skip the second lane for read-only questions, tiny mechanical edits, formatting-only changes, or when the user explicitly asks for a single-agent flow.
- For the review lane, start early enough to challenge the approach and run it again against the actual diff before closing non-trivial work.

## Current Delivery Constraints

- Primary user is a finance professional. Assume working knowledge of GDP, CPI, unemployment, fiscal debt, current account balance, and related macro indicators.
- KPI selection and AI narrative should lead with risk-weighted signals: sovereign risk, inflationary pressure, fiscal stress, external vulnerability, recessionary signal.
- Country pages should explain direction of travel, magnitude of change, and whether a move is anomalous relative to history. Avoid basic indicator definitions.
- Scope remains intentionally bounded: a 17-country exact-complete core panel ending at 2024, 6 indicators, one Cloud Run job, one Firestore collection, and one end-to-end live demo URL.
- Treat those scope limits as delivery guardrails, not permission for shortcut engineering. Target production-grade readability, documentation, validation, and reviewability.
- The Pipeline Trigger flow is the presentation centrepiece. Prefer clean end-to-end reliability over speculative scale work such as async fan-out, multi-source enrichment, or heavy caching.
- The dashboard is the final human-facing surface. Optimize API and Firestore shapes for frontend display, with structured fields only where the UI needs them and richer prose everywhere else.
- Keep the responsible AI disclaimer visible in human-facing surfaces: AI-generated content may contain inaccuracies. Verify before acting.

## Commands

```bash
# Backend
cd api && pip install -r requirements.txt
cd api && python -m pytest tests/ -v
cd api && ruff check .

# Pipeline
cd pipeline && pip install -r requirements.txt
cd pipeline && python -m pytest tests/ -v

# Frontend
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run lint
cd frontend && npm run build
```

## File Map

- `api/openapi.yaml` — API contract (source of truth)
- `api/app.py` — Connexion application factory
- `api/handlers/` — Route handlers
- `pipeline/fetcher.py` — World Bank API client
- `pipeline/analyser.py` — Pandas statistical processing
- `pipeline/ai_client.py` — LLM abstraction (Gemini/OpenAI)
- `pipeline/storage.py` — Firestore + GCS operations
- `frontend/src/pages/` — 4 pages (GlobalOverview, CountryIntelligence, HowItWorks, PipelineTrigger)
- `frontend/src/index.css` — Design tokens as CSS custom properties

## Skills

Read `.github/skills/*/SKILL.md` for domain-specific guidance before modifying code in that area.

Frontend work should consult three complementary layers:

- `.github/skills/world-analyst-design-system/SKILL.md` — What things look like (tokens, colors, surfaces, typography)
- `.github/skills/emil-design-eng/SKILL.md` — How things move (animation, easing, springs, interaction polish)
- `.github/skills/design-taste-frontend/SKILL.md` — Design judgment (anti-AI-slop, creative proactivity, layout philosophy)

For a structured design review or polish pass, run `.agents/workflows/frontend-design-review.md` — it orchestrates all three layers in sequence: appearance audit, taste audit, motion audit, then structured fixes by priority.

Use `.github/skills/humanizer-pro/SKILL.md` when writing or editing ADRs, presentation copy, user-facing narrative, or explanatory comments/docs that read as generic AI text.
