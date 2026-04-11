# World Analyst — Project Instructions

> **What:** AI-native economic intelligence terminal, originally framed in the ML6 Engineering Challenge and now held to production-grade quality standards.
> **Why:** Demonstrate intent-driven, spec-first development with agentic AI — not vibe coding.

---

## Identity

You are working on **World Analyst**, a global economic intelligence dashboard that fetches World Bank data, processes it through a two-step LLM analysis chain, and serves structured insights via a Connexion REST API to a React frontend. This is a demonstration of ML6's AI Native Way of Working (WoW).

---

## Tech Stack (Non-Negotiable)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend Framework | **Python 3.12 + Connexion** | OpenAPI-first, contract-enforced routing. The spec requires Connexion. |
| API Spec | **openapi.yaml** | Single source of truth. Connexion reads this, not the other way around. |
| Data Processing | **Pandas** | Statistical analysis (% changes, anomaly flags) before LLM receives data. |
| AI Layer | **Vertex AI (Gemini) or OpenAI** | Two-step chain: per-indicator analysis → macro synthesis. Abstracted via `ai_client.py`. |
| Storage | **Firestore** (insights) + **GCS** (raw backup) | Document-shaped, read-heavy. Not BigQuery. |
| Frontend | **React 18 + Vite** | SPA served via nginx on Cloud Run. |
| Styling | **Vanilla CSS** with CSS custom properties | Design system uses explicit tokens. No Tailwind, no CSS frameworks. |
| Charts | **Recharts** (line/bar) + **react-simple-maps** (choropleth) | D3-based, React-native. |
| Deployment | **Cloud Run** (3 services) + **Cloud Scheduler** | Scale-to-zero. Region: `europe-west1`. |
| Auth | **API Key** in `X-API-Key` header | Stored in GCP Secret Manager. |

---

## Design System (Mandatory Constraints)

Read `Design Mockups/Design System.md` for full tokens. Hard rules:

- **Canvas:** `#0E0E0E`. Cards: `#1A1A1A`. Nested: `#201F1F`.
- **Primary accent:** `#FF4500` (International Orange) — reserved for AI insights and primary CTAs only.
- **Borders:** 1px solid `#262626`. No shadows. No blur. No glassmorphism.
- **Border radius:** 8px everywhere. Never more, never less.
- **Typography:** Inter (display/body) + Commit Mono (metrics/labels).
- **Vertical rhythm:** 32px between major sections.
- **Secondary text:** `#737373`. Drop immediately — no in-between greys.
- **Labels:** `label-sm` = Commit Mono, 0.6875rem, 700 weight, uppercase, 0.05em letter-spacing.
- **Depth:** Tonal only. Level 0 → Level 3 via background lightness, never shadow.
- **Icons:** Functional only. No decoration. `auto_awesome` in `#FF4500` for AI indicator.

---

## Architecture Principles (ML6 WoW)

1. **Intent-First Development** — Document the "why" and trade-offs before writing code. `WORLD_ANALYST_PROJECT.md` is the intent document.
2. **PaperTrail of Context** — Context lives in the repo (this file, README.md, openapi.yaml), not in ephemeral chats.
3. **Absolute Ownership** — Every line must be explainable and defensible. No blind AI generation. Use docstrings and targeted inline comments so non-obvious logic can be defended from the repo alone.
4. **Business-Driven Testing** — Tests prove business requirements, not coverage metrics. "Does the pipeline detect an anomaly when GDP drops 5%?" > "Does the function return 200?"
5. **Spec-Driven Development (SDD)** — openapi.yaml defines the contract. Handlers implement it. Never the reverse.

---

## Project Skills (In-Repo)

Use these project-specific skills for domain guidance:

| Skill | Path | When |
|-------|------|------|
| Design System | `.github/skills/world-analyst-design-system/SKILL.md` | Any frontend/UI work |
| Connexion API | `.github/skills/connexion-api-development/SKILL.md` | API routes, handlers, openapi.yaml |
| Engineering WoW | `.github/skills/world-analyst-engineering/SKILL.md` | Architecture decisions, testing philosophy, code quality |
| World Bank API | `.github/skills/world-bank-api/SKILL.md` | Pipeline data fetching, indicator codes, response parsing |
| LLM Prompting | `.github/skills/llm-prompting-and-evaluation/SKILL.md` | AI prompts, structured output, evaluation, LLM-as-Judge |
| Humanizer Pro | `.github/skills/humanizer-pro/SKILL.md` | ADRs, README prose, presentation copy, user-facing narrative, and other writing that must sound direct and credible |

## Global Skills (Antigravity)

The following globally-installed skills are relevant. Invoke with `@skill-name`:

**Always applicable:** `@debugger`, `@lint-and-validate`, `@concise-planning`, `@writing-plans`
**Backend:** `@api-patterns`, `@python-pro`, `@pydantic-models-py`, `@database-design`
**Frontend:** `@react-patterns`, `@frontend-design`, `@claude-d3js-skill`
**Infrastructure:** `@docker-expert`, `@gcp-cloud-run`, `@secrets-management`, `@cost-optimization`
**Quality:** `@test-driven-development`, `@code-reviewer`, `@architect-review`, `@systematic-debugging`
**AI/ML:** `@gemini-api-dev`

---

## Code Style

### Python
- Formatter: `ruff format`
- Linter: `ruff check`
- Type hints on all function signatures
- Docstrings: Google style
- Add brief inline comments when business rules, thresholds, orchestration, or contract shaping would not be obvious from names alone
- Imports: stdlib → third-party → local, separated by blank line

### JavaScript/React
- Formatter: Prettier (default config)
- Linter: ESLint
- Functional components only, hooks for state
- Named exports for components
- CSS custom properties for theming, imported via `index.css`
- Add concise file or section comments when derived state, polling, or data flow would otherwise be hard to explain in review

### General
- No `console.log` or `print()` in production code — use proper logging
- No commented-out code
- No TODO without a linked plan reference
- Code and docs should be presentation-ready: the repo should explain itself without chat history
- Commit messages: `type: description` (feat, fix, refactor, docs, test, chore)

---

## File Map

```
api/
├── openapi.yaml          ← API contract. Connexion reads this.
├── app.py                ← Connexion app factory
├── handlers/             ← Route handlers (1:1 with openapi paths)
│   ├── indicators.py
│   ├── countries.py
│   ├── health.py
│   └── pipeline.py
├── requirements.txt
├── Dockerfile
└── tests/

pipeline/
├── main.py               ← Entry point for Cloud Run Job
├── fetcher.py             ← World Bank API client
├── analyser.py            ← Pandas statistical analysis
├── ai_client.py           ← LLM abstraction (Gemini/OpenAI swap)
├── storage.py             ← Firestore + GCS write operations
├── requirements.txt
├── Dockerfile
└── tests/

frontend/
├── src/
│   ├── pages/             ← 4 pages matching routes
│   ├── components/        ← Shared UI components
│   ├── App.jsx
│   └── index.css          ← Design system tokens as CSS variables
├── package.json
├── vite.config.js
└── Dockerfile
```

---

## Workflows

| Workflow | Path | Command |
|----------|------|---------|
| Build | `.agents/workflows/build.md` | Lint + install + build |
| Test | `.agents/workflows/test.md` | pytest + npm test |
| Deploy | `.agents/workflows/deploy.md` | gcloud run deploy |
| Decision | `.agents/workflows/decision.md` | Append ADR to docs/DECISIONS.md |

