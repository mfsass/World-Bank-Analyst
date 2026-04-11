# World Analyst — Project Brief & Build Context

**Document Type:** Engineering Challenge Brief + Architecture Decision Record  
**Challenge:** ML6 AI Native WOW Engineering Challenge  
**Role Applied For:** Product Engineer — Unum Enterprise AI Platform  
**Document Status:** Active — Implementation Baseline  

---

## Table of Contents

1. [Original Challenge Brief](#1-original-challenge-brief)
2. [What We Are Actually Building](#2-what-we-are-actually-building)
3. [Architecture Decisions](#3-architecture-decisions)
4. [Page Structure & UX Design System](#4-page-structure--ux-design-system)
5. [AI Strategy — Agentic Thinking](#5-ai-strategy--agentic-thinking)
6. [Model Selection](#6-model-selection)
7. [Data Strategy — World Bank API](#7-data-strategy--world-bank-api)
8. [Technical Stack](#8-technical-stack)
9. [Security](#9-security)
10. [Deployment](#10-deployment)
11. [Design System Reference](#11-design-system-reference)
12. [Presentation Strategy](#12-presentation-strategy)
13. [Open Questions](#13-open-questions)
14. [What Makes This Different](#14-what-makes-this-different)

---

## 1. Original Challenge Brief

### Source
ML6 AI Native WOW Engineering Challenge — distributed to candidates by Julie Plusquin.

### Interview Format
- `[05 min]` Introductions
- `[30 min]` Presentation of solution
- `[15 min]` Q&A

### The Brief Summary
> *"Your role is to bridge the gap between advanced AI tooling and daily business operations. Build an end-to-end automated system that extracts global economic data, processes it using Generative AI, and delivers actionable insights to a dashboard."*

### Three Core Requirements

**1. Data Acquisition & Integration**
- Source: World Bank Data API (free, no auth required)
- Mechanism: **Push** — not pull-on-demand. A scheduled job actively pushes data into storage. This is a deliberate architectural word in the brief that most candidates will miss.

**2. AI Analysis Step**
- Use an LLM (OpenAI or similar) to interpret retrieved figures
- AI should identify trends, anomalies, and financial risks
- The key evaluation word: **"Agentic thinking"** — how you structure the prompt and workflow to ensure reliable, useful output

**3. Data Persistence & Visualisation**
- Store raw data + AI-generated insights in a GCP component
- Create a dashboard displaying figures and AI interpretations

### Technical Requirements (Verbatim from Brief)
- **Cloud Engineering:** Entire solution hosted on GCP
- **Backend:** Python — must use the **Connexion framework**
- **Frontend:** Web application with financial dashboard
- **AI Native Workflow:** Evidence of agentic thinking in prompt structure
- **Security:** Implement secure access (API keys, Basic Auth, or OAuth)

### Deliverables
- Live URL to deployed dashboard/API
- Git repository with code + `README.md` explaining architectural choices
- Cloud Run scale-to-zero enabled (cost management)

### ML6 Note
> *"We value seamless access. The easier it is for our engineers to trigger and view your solution, the better."*

---

## 2. What We Are Actually Building

### Product Name
**World Analyst** — a global economic intelligence terminal

### The Mental Model
Not a data pipeline with a frontend bolted on. A **product** — an AI-native analyst that happens to be built on a data pipeline.

```
World Bank API 
    ↓ [scheduled push, weekly]
Cloud Run Job (Python + Connexion)
    ↓ [pandas: % changes, anomaly flags]
Pandas Statistical Analysis
    ↓ [structured context per indicator]
AI Intelligence Layer (LLM via API)
    ↓ [structured JSON narratives]
Firestore (processed insights) + GCS (raw JSON backup)
    ↓ [served via Connexion REST API]
React Frontend (World Analyst Dashboard)
```

### The Core Insight
> Python + Pandas does the math. The LLM writes the analyst report.

Pandas detects *that* GDP dropped 4.2%. The LLM explains *why* — what it means, what drives it, what the risk flags are. This is the right division of labour and directly what ML6 is evaluating.

### Four Pages

| Page | Route | Purpose |
|---|---|---|
| Global Overview | `/` | Summary, map, market depth |
| Country Intelligence | `/country/:id` | Per-country deep dive |
| How It Works | `/pipeline` | Architecture explainer |
| Pipeline Trigger | `/trigger` | Live execution UI |

### April 2026 Clarifications

These constraints govern KPI selection, AI prompt design, dashboard UX, and scope decisions across the project:

1. **Finance team audience.** The user is a finance professional, not a general business reader. The product should assume literacy in macro indicators and focus on what the signals mean now in risk terms: sovereign risk, inflationary pressure, fiscal stress, external vulnerability, and recessionary signal. Country intelligence should emphasise direction of travel, magnitude of change, and anomaly versus historical norms rather than explaining basic definitions.
2. **Bounded delivery scope.** Scope guardrails remain fixed at 15 countries, 6 indicators, one Cloud Run job, one Firestore collection, and one deployable URL. Treat those limits as scope controls, not permission for shortcut engineering. Prefer a clean, defendable end-to-end system with production-grade readability, documentation, and validation over speculative scalability.
3. **Dashboard as the terminal surface.** A human reads the output and decides what to do next. That means API responses and Firestore documents should be optimized for display rather than machine-readability. Rich analyst prose is desirable. Structured fields should exist only where the React frontend needs them for rendering badges, deltas, anomaly flags, or risk scores. The responsible AI disclaimer matters because a human is acting on generated narrative.
4. **Decision baseline.** ADR-008 and ADR-014 now formalize the finance-first audience and production-grade delivery standard. This document should be read as the product brief and architecture story, while `docs/DECISIONS.md` remains the source of truth for trade-offs finalized during planning.

---

## 3. Architecture Decisions

### Storage: Firestore + GCS

**Why not BigQuery?**
BigQuery is a data warehouse built for analytical queries over large datasets. We are storing JSON-shaped documents and serving them read-heavy to a dashboard. BigQuery is overkill and adds unnecessary complexity.

**Why Firestore?**
- Data is naturally document-shaped (country → indicators → AI narratives)
- Read-heavy workload with no need for SQL queries
- GCP-native, serverless, zero management overhead
- `doc.get()` is all the querying we need

**Why also GCS?**
- Raw World Bank API responses stored as JSON blobs
- Cheap, durable, GCP-native
- Provides a clear audit trail: raw data in GCS, processed insights in Firestore

**README justification ready:**
> "Firestore chosen for document-shaped read-heavy workload over BigQuery; GCS for raw data archival. Architecture supports migration to BigQuery if analytical queries become a future requirement."

---

### Backend: Python + Connexion

**What is Connexion?**
An OpenAPI-first Python framework. You write an `openapi.yaml` specification first, and Connexion automatically routes HTTP requests to your Python handler functions based on the spec. It enforces the API contract at the framework level.

**Why does ML6 specify it?**
Connexion represents enterprise-grade API design thinking — you define the contract before you write the implementation. This is how production APIs at scale are built.

**How it works in practice:**
```yaml
# openapi.yaml
paths:
  /indicators:
    get:
      operationId: handlers.indicators.get_all
      security:
        - ApiKeyAuth: []
```
```python
# handlers/indicators.py
def get_all():
    docs = firestore_client.collection('insights').stream()
    return [doc.to_dict() for doc in docs], 200
```

Connexion reads the YAML, wires the route, validates the request, checks auth — all before your handler runs.

---

### Deployment: Cloud Run

**Why Cloud Run?**
- Serverless containers — no server management
- Scale-to-zero: costs nothing when idle (brief explicitly mentions this)
- Each service is its own container
- Single `gcloud run deploy` command to ship

**Three Cloud Run services:**
1. `world-analyst-api` — Connexion/Python REST API
2. `world-analyst-frontend` — React app served via nginx
3. `world-analyst-pipeline` — Cloud Run Job triggered by Cloud Scheduler

**Cloud Scheduler:**
Weekly cron triggers the pipeline job. This is the "Push mechanism" the brief requires — data is actively pushed into Firestore on a schedule, not fetched on page load.

---

## 4. Page Structure & UX Design System

### Navigation Structure
Four items only. No clutter.

```
[✦ WORLD ANALYST]  Global Overview | Country Intelligence | How It Works | Pipeline  [🔒 API KEY] [🔔] [⚙] [👤]
```

### Sidebar (simplified)
```
● OPERATIONAL
  LATENCY: 24MS

🌐  Global Overview
🚩  Country Intelligence  
⬡   How It Works
▶   Pipeline

---
Export Report →
Documentation
API Support
```

---

### Page 1 — Global Overview

**Structure:**
```
[AI-GENERATED INSIGHTS badge]
[H1: Global Economic Outlook — April 2026]
[AI summary paragraph]

[⚠ 04 ANOMALIES DETECTED — REVIEW FLAGGED MARKETS BELOW]  [DISMISS]

EXECUTIVE SUMMARY
[Countries: 15] [Indicators: 6] [Volatility: 18.42] [Last Analysis: 2h ago]

GLOBAL RISK OVERVIEW                    REGIONAL BREAKDOWN
[World map with orange pins]            [Table: ID | Country | Metric | Risk]
[SELECT MARKET pill rail]
[Hover tooltip per country]

MARKET DEPTH ANALYSIS
[4 country cards with sparklines + AI insight quotes]
```

**Map Interaction:**
- 15 countries have orange `place` pin markers
- Hover: pin scales 1.2x + preview card appears
  - Country flag + name + primary metric + risk badge + "View Intelligence →"
- Click: navigates to Country Intelligence for that country

**15 Selected Countries:**

| Region | Countries |
|---|---|
| Europe (ML6 Markets) | Belgium (BE), Netherlands (NL), Germany (DE), United Kingdom (GB), France (FR) |
| Americas | USA (US), Brazil (BR), Canada (CA) |
| Asia-Pacific | China (CN), Japan (JP), India (IN), Australia (AU) |
| Africa / MENA | South Africa (ZA), Nigeria (NG), Egypt (EG) |

Rationale: geographic spread, strong narrative contrast (DE stability vs NG volatility vs ZA recovery), covers ML6's key client regions and office locations (Belgium HQ, Netherlands, Germany, UK). All 15 country codes verified against World Bank API — see `.github/skills/world-bank-api/SKILL.md`.

---

### Page 2 — Country Intelligence

**Structure:**
```
DASHBOARD > SOUTH AFRICA

[SWITCH MARKET pill rail: BR | CN | EG | IN | NG | ZA* | ...]

[🇿🇦  SOUTH AFRICA]  EMERGING MARKET — TIER 1     TOTAL POPULATION
                                                    60.41M    [HIGH RISK]

[GDP: 1.2% -0.3%] [CPI: 5.4% -1.2%] [Unemployment: 32.9% +0.2%] [Fiscal: -4.7% -0.1%]

[Real GDP Growth chart — 5Y]        [✦ AI ANALYST REPORT          +4.2% SCORE]
[CPI Inflation chart — 1Y]          [TREND SUMMARY paragraph]
[Unemployment chart — 5Y]           [KEY DRIVERS bullet list]
                                    [⚠ RISK FLAGS two cards]
                                    [OUTLOOK italic quote]
```

**Chart Specifications:**
- White `#F5F5F5` line, 1.5px stroke
- Anomaly marker: `#FF4500` filled circle, 5px radius + `ANOMALY DETECTED` orange pill label
- Y-axis: `%` or `ANNUAL %` in `#404040` mono 10px
- X-axis year markers: 2020, 2021, 2022, 2023, 2024
- Time toggles: `1Y | 3Y | 5Y` — orange active, ghost inactive

---

### Page 3 — How It Works

**Structure:**
```
HOW IT WORKS — AI PIPELINE

[✦ LIVE PIPELINE EXECUTION card with CTA buttons]

SYSTEM TELEMETRY
[Uptime: 99.98%] [Latency: 142ms] [Daily Data Points: 2.4M] [Cache Hit Rate: 86.4%]

PIPELINE ARCHITECTURE
[World Bank API] → [Cloud Run] → [Anomaly Detection] → [AI Intelligence Layer] → [Data Persistence]

INPUT: RAW WORLD BANK JSON          OUTPUT: AI INTELLIGENCE SUMMARY
[code block]                        [structured card output]

PROMPT STRATEGY
[Step 1: Per-Indicator Analysis]    [Step 2: Macro Synthesis]

TWO-STEP AGENTIC CHAIN — DESIGNED FOR RELIABLE, STRUCTURED OUTPUT

AI ENGINE          COMPUTE               DATABASE          ORCHESTRATOR
Intelligence Layer Cloud Run—Serverless  Firestore + GCS   Cloud Scheduler (Python 3.12)
```

**Pipeline Node Specs:**

| Node | Badge | Icon | Colour |
|---|---|---|---|
| World Bank API | `REST API` | `public` | `#737373` |
| Cloud Run | `PYTHON 3.12` | `cloud` | `#FF4500` |
| Anomaly Detection | `PANDAS` | `analytics` | `#737373` |
| AI Intelligence Layer | `AI INTELLIGENCE LAYER` | `auto_awesome` FILLED | White on `#FF4500` bg |
| Data Persistence | `FIRESTORE + GCS` | `storage` | `#737373` |

---

### Page 4 — Pipeline Trigger

**The most important page for the presentation.** An ML6 engineer clicks one button and watches the entire pipeline execute end-to-end in real time.

**Structure:**
```
PIPELINE EXECUTION — LIVE TRIGGER

[PIPELINE STATUS: IDLE/RUNNING/COMPLETE] [Last Run: 8.4s] [Records: 2,847] [AI Calls: 17]

[✦ TRIGGER PIPELINE RUN                          [▶ RUN PIPELINE NOW] ]
[Fetches World Bank data, runs analysis,                                ]
[generates AI narratives, updates Firestore.                            ]

LIVE EXECUTION SEQUENCE                    SYSTEM TERMINAL
[Step 01: WORLD BANK API FETCH   ✓ 847ms] [● ● ●  CONSOLE_STREAM       ]
[Step 02: SCHEMA VALIDATION      ✓ 234ms] [[08:42:01] Initialising...   ]
[Step 03: ANOMALY DETECTION      ↻ RUNNING] [[08:42:03] Connection OK   ]
[Step 04: AI NARRATIVE GENERATION  PENDING] [[08:42:08] Anomaly: EG...  ]
[Step 05: FIRESTORE WRITE          PENDING]

[✓ PIPELINE COMPLETE — View Updated Dashboard →]
```

**Step Card States:**

| State | Left Border | Background | Status Text |
|---|---|---|---|
| IDLE | `1px #262626` | `#1A1A1A` | `—` in `#404040` |
| RUNNING | `4px #FF4500` | `#1F1A17` warm tint | Orange spinner + `RUNNING...` |
| COMPLETE | `4px #22C55E` | `#1A1A1A` | `✓ COMPLETE — {ms}` in `#22C55E` |
| PENDING | `1px #262626` | `#1A1A1A` | `PENDING` muted |

**Terminal Log Format:**
```
[HH:MM:SS] Initialising pipeline run...
[HH:MM:SS] Connecting to World Bank API...
[HH:MM:SS] Fetched ZA: GDP 1.2%, Inflation 5.4%
[HH:MM:SS] Fetched NG: GDP -1.2%, Inflation 24.5%
[HH:MM:SS] Schema validation complete. 0 errors.
[HH:MM:SS] Anomaly flagged: EG inflation +32.1%
[HH:MM:SS] AI narrative generation: 15/15 complete
[HH:MM:SS] Writing to Firestore... done.
[HH:MM:SS] Pipeline complete. Duration: 8.4s
```

---

## 5. AI Strategy — Agentic Thinking

This is the primary differentiator. Most candidates pass data to an LLM and call it done. We show a structured reasoning chain.

### Two-Step Agentic Chain

**Step 1 — Per-Indicator Analysis**

Each indicator is analysed independently. The LLM receives structured context:

```python
prompt_per_indicator = f"""
You are a senior financial analyst reviewing economic data.

COUNTRY: {country_name}
INDICATOR: {indicator_name}
CURRENT VALUE: {current_value}
YEAR-ON-YEAR CHANGE: {yoy_change}%
ANOMALY FLAGGED: {anomaly_detected}
HISTORICAL CONTEXT: {last_5_years_values}

Respond with JSON only:
{{
  "summary": "2-3 sentence interpretation",
  "trend": "improving|declining|stable|volatile",
  "risk_level": "low|medium|high|critical",
  "key_drivers": ["driver1", "driver2"],
  "anomaly_explanation": "explanation if anomaly flagged"
}}
"""
```

**Step 2 — Macro Synthesis**

A second LLM pass synthesises all per-indicator outputs:

```python
prompt_macro = f"""
You are a chief economist reviewing analyst reports for {country_name}.

INDICATOR ANALYSES:
{json.dumps(all_indicator_analyses, indent=2)}

Generate an executive intelligence summary as JSON only:
{{
  "headline": "one sentence macro outlook",
  "trend_summary": "2-3 sentence narrative",
  "key_drivers": ["top 3 drivers"],
  "risk_flags": [{{"category": "name", "description": "detail"}}],
  "outlook": "forward-looking paragraph",
  "overall_risk_level": "low|medium|high|critical",
  "confidence_score": 0.0-1.0
}}
"""
```

### Why Two Steps?

Single-pass prompting on multi-indicator data causes context collapse — the model averages everything and produces generic summaries. Two-pass forces independent reasoning per indicator first, then gives the synthesis step structured, validated inputs. Output quality is measurably better and the architecture is defensible in Q&A.

### Structured Output Handling
- All LLM calls use schema-constrained structured output rather than prompt-only JSON enforcement.
- Response payloads validate against shared Pydantic models before storage.
- Transient provider or validation failures use bounded retries.
- Exhausted retries produce an explicit degraded result rather than a normal-looking fabricated response.

---

## 6. Model Selection

### Current baseline

Live AI now starts from an economy-first baseline: Google GenAI with `gemma-4-31b-it`.

This is not a blind commitment to the cheapest model. It is the default candidate defined by ADR-026 and the Live AI integration PRD. The model keeps the system inside the Google ecosystem, fits the current cost posture, and is easy to explain in review.

### Promotion policy

- The baseline stays in place only if it passes the evaluation gate.
- Evaluation covers structured-output validity, groundedness to the pandas inputs, synthesis quality, refusal behavior, latency, and bounded full-run cost.
- One or both AI steps may move to a stronger Google, OpenAI, or OpenRouter-backed model if the baseline is not good enough.
- The AI client boundary remains provider-agnostic, so model promotion does not require a pipeline redesign.

### Cost reality

The two-step chain produces 90 per-indicator calls plus 15 country-synthesis calls per full run: 105 total. Cost still matters because the project is scheduled and bounded, but it now matters as an optimization target rather than as a reason to delay live AI. ADR-027 addresses that by reusing exact-match AI inputs instead of adding a separate cache layer.

---

## 7. Data Strategy — World Bank API

### Base URL
```
https://api.worldbank.org/v2/
```
No authentication required. Free and open.

### Selected Indicators

> **⚠ CORRECTED (April 2026):** Original indicators `GC.BAL.CASH.GD.ZS` (Fiscal Balance) and `DT.DOD.DECT.GD.ZS` (External Debt) were found to be **deleted/archived** and **invalid** respectively during live API audit. Replaced with verified working indicators.

| Indicator Code | Metric | Unit | Verified |
|---|---|---|---|
| `NY.GDP.MKTP.CD` | GDP (current US$) | USD | ✅ |
| `NY.GDP.MKTP.KD.ZG` | GDP Growth (Annual %) | % | ✅ |
| `FP.CPI.TOTL.ZG` | CPI Inflation (Annual %) | % | ✅ |
| `SL.UEM.TOTL.ZS` | Unemployment Rate (% of labour force) | % | ✅ |
| `BN.CAB.XOKA.GD.ZS` | Current Account Balance (% of GDP) | % | ✅ |
| `GC.DOD.TOTL.GD.ZS` | Central Government Debt (% of GDP) | % | ✅ |

All six indicators verified against live World Bank API production endpoint (April 2026). See `.github/skills/world-bank-api/SKILL.md` for complete API reference.

### Example API Call
```
https://api.worldbank.org/v2/country/za/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2017:2023&per_page=1000
```

### Historical window policy

The live analysis window is fixed to seven years: `2017:2023` (ADR-019). That is enough history for year-over-year change, anomaly checks, and narrative context without turning the data layer into a broader research platform.

### Pandas Analysis Steps
1. Fetch raw JSON → normalise to DataFrame
2. Calculate year-on-year % change
3. Calculate rolling 3-year mean
4. Z-score per indicator to detect anomalies (threshold: `|z| > 2.0`)
5. Flag anomaly boolean + magnitude
6. Structure context dict for LLM prompt

### Storage Schema

**GCS (raw):**
```
gs://world-analyst-raw/
  └── runs/
    └── {run_id}/
      └── raw/
        └── {indicator_code}.json
```

**Firestore (processed):**
```
insights/
  ├── indicator:{country_code}:{indicator_code}
  │   └── { entity_type, run_id, values..., source_provenance..., ai_provenance... }
  ├── country:{country_code}
  │   └── { entity_type, run_id, macro_briefing, risk_flags, outlook, ... }
  └── pipeline_status:current
    └── { entity_type, status, steps, started_at, completed_at, error }
```

The processed store now follows the mixed-document model formalized in ADR-009 and ADR-016. One `insights` collection holds indicator, country, and current-status documents behind an explicit record-type field.

---

## 8. Technical Stack

### Backend
```
Python 3.12
Connexion 3.x          # OpenAPI-first routing
Flask                  # Underlying WSGI (Connexion dependency)
google-cloud-firestore # Firestore client
google-cloud-storage   # GCS client
pandas                 # Statistical analysis
numpy                  # Numerical operations
requests               # World Bank API calls
openai / google-genai         # LLM client — see docs/DECISIONS.md ADR-003
pydantic               # Response validation
```

### Frontend
```
React 18
Recharts               # Line charts, sparklines
D3 / react-simple-maps # World map choropleth with pins
Vanilla CSS            # Design tokens as CSS custom properties — no frameworks
Inter (Google Fonts)   # Primary typeface
Commit Mono (Google Fonts) # Monospace metrics
```

### Infrastructure
```
Google Cloud Run       # API + frontend + pipeline job
Google Cloud Firestore # Processed insights
Google Cloud Storage   # Raw data archival
Google Cloud Scheduler # Weekly cron trigger
```

### Project Structure
```
world-analyst/
├── api/
│   ├── openapi.yaml           # Connexion API spec — source of truth
│   ├── app.py                 # Connexion app factory
│   ├── handlers/
│   │   ├── indicators.py      # GET /indicators
│   │   ├── countries.py       # GET /countries, GET /countries/{id}
│   │   └── health.py          # GET /health
│   └── Dockerfile
├── pipeline/
│   ├── main.py                # Entry point
│   ├── fetcher.py             # World Bank API client
│   ├── analyser.py            # Pandas analysis
│   ├── ai_client.py           # LLM integration (model-agnostic)
│   ├── storage.py             # Firestore + GCS writes
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── GlobalOverview.jsx
│   │   │   ├── CountryIntelligence.jsx
│   │   │   ├── HowItWorks.jsx
│   │   │   └── PipelineTrigger.jsx
│   │   ├── components/
│   │   │   ├── WorldMap.jsx
│   │   │   ├── KPICard.jsx
│   │   │   ├── LineChart.jsx
│   │   │   ├── AIReportPanel.jsx
│   │   │   ├── PipelineStep.jsx
│   │   │   └── TerminalLog.jsx
│   │   └── App.jsx
│   └── Dockerfile
└── README.md
```

---

## 9. Security

### API Key Authentication
The brief requires secure access. The current deployment baseline uses API key header validation via Connexion's built-in security scheme. Final browser-facing hardening is now defined in the Security, Testing, And Hardening PRD: the deployed frontend reaches the API through a same-origin proxy path, and the proxy injects the shared API key server-side so the browser does not hold the production secret.

**openapi.yaml:**
```yaml
securitySchemes:
  ApiKeyAuth:
    type: apiKey
    in: header
    name: X-API-Key

security:
  - ApiKeyAuth: []
```

**Validation handler:**
```python
def check_api_key(api_key, required_scopes=None):
    expected = os.environ.get("API_KEY")
    if api_key != expected:
        return None  # Connexion returns 401 automatically
    return {"sub": "analyst"}
```

**Secret management:**
- API key stored as Cloud Run environment variable
- Sourced from Secret Manager in production
- Never committed to source code or repository
- AI provider credentials are also server-side secrets and stay separate from frontend-to-API authentication.

**Current boundary:**
The API-key pattern shown here remains the backend auth scheme. The browser-facing boundary is tighter: the deployed frontend proxy owns the production key, while the browser uses the same-origin product URL without seeing that secret.

**UI signal:**
The `🔒 API KEY` indicator in the top nav bar visually communicates that the system is authenticated. This small detail shows awareness of the security requirement without disrupting the UX.

---

## 10. Deployment

### Runtime topology

The deployment target is now more specific than the original sketch:

- The frontend runs on Cloud Run and reads from the deployed API.
- The API serves data and dispatches manual pipeline runs.
- The pipeline runs as a Cloud Run Job.
- Manual trigger dispatch uses the Cloud Run Jobs API (ADR-021), not an in-process API thread.
- Trigger idempotency uses a Firestore transaction against the current status record (ADR-022).

### Cloud Run Configuration

```bash
# Build and push API
gcloud builds submit --tag gcr.io/PROJECT_ID/world-analyst-api ./api

# Deploy API service
gcloud run deploy world-analyst-api \
  --image gcr.io/PROJECT_ID/world-analyst-api \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 10

# Deploy Pipeline Job
gcloud run jobs deploy world-analyst-pipeline \
  --image gcr.io/PROJECT_ID/world-analyst-pipeline \
  --region europe-west1

# Schedule weekly trigger (Monday 06:00)
gcloud scheduler jobs create http pipeline-weekly \
  --schedule="0 6 * * MON" \
  --uri="https://REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/world-analyst-pipeline:run" \
  --http-method=POST
```

### Runtime configuration

- `PIPELINE_MODE=local|live` selects the data source path.
- `REPOSITORY_MODE=local|firestore` selects the storage backend.
- `VITE_API_BASE_URL` is injected at frontend build time so the deployed bundle targets the correct API origin (ADR-023).
- The scheduled baseline remains weekly at Monday 06:00 UTC (ADR-024).

### Region Choice
`europe-west1` — Belgium. Aligns with ML6's Ghent headquarters. Signals geographical awareness of their client base. Minor detail, worth mentioning in the README and presentation.

See ADR-028 for the explicit rationale.

### Scale-to-Zero
`--min-instances 0` is the default. Costs nothing when idle. The brief explicitly recommends this. Include in README as a deliberate cost management decision.

---

## 11. Design System Reference

### Colour Tokens

```
Background:     #0E0E0E   Canvas
Card surface:   #1A1A1A   Level 1
Nested card:    #201F1F   Level 2
Card border:    #262626   Structural
Text primary:   #F5F5F5   Headings, metrics
Text secondary: #737373   Body, descriptions
Text muted:     #404040   Labels, micro text

Accent orange:  #FF4500   AI signal, CTAs, active states
Accent green:   #22C55E   Stable, success, pipeline complete
Accent amber:   #F59E0B   Warning states
Accent red:     #EF4444   Critical, negative delta
```

### Typography

| Role | Font | Size | Weight |
|---|---|---|---|
| Display | Inter | 2.75rem | 700 |
| Headline | Inter | 1.5rem | 600 |
| Title | Inter | 1.0rem | 600 |
| Body | Inter | 0.875rem | 400 |
| Metric | Commit Mono | 1.125rem | 500 |
| Micro | Commit Mono | 0.6875rem | 700 uppercase 0.05em tracking |

### Core Rules

**Cards:** `#1A1A1A` bg, `1px solid #262626` border, `8px` radius, `24px` padding. No shadows. No gradients. No exceptions.

**Depth is tonal only** — use background shifts, not shadows or blur.

**Accent border rule (strict):**
Coloured left borders appear in exactly three contexts only:
1. AI Analyst Report panel — `4px #FF4500`
2. Pipeline step in RUNNING state — `4px #FF4500`
3. Pipeline step in COMPLETE state — `4px #22C55E`

Everything else: `1px #262626`. When everything has an accent, nothing does.

**Orange usage limit:** Maximum 3–4 visible instances per screen. Restraint is what gives it weight.

**No blue anywhere.** The design system uses a monochromatic dark base with semantic colour accents. Blue has no semantic role in this system.

### Footer (standardised, all screens)
```
Left:   WORLD ANALYST                    #FF4500, Commit Mono bold, 10px uppercase
Center: PRIVACY PROTOCOL | SECURITY AUDIT | ENGINEERING DOCS   #404040
Right:  AI-GENERATED CONTENT MAY CONTAIN INACCURACIES. VERIFY BEFORE ACTING.   #404040
```

No model names. No vendor names. The AI disclaimer directly reflects ML6's public commitment to responsible and trustworthy AI.

---

## 12. Presentation Strategy

### The 30-Minute Arc

**Minutes 0–2: Open with the live demo — not slides**
Navigate directly to the deployed URL. Click "Run Pipeline." Watch all five steps go green in ~8 seconds. Say: *"That was the entire pipeline — World Bank API to AI narratives to Firestore — end to end, live."*

**Minutes 2–8: Global Overview walkthrough**
Walk through Screen 1. Explain the anomaly alert banner. Hover over a country on the map to show the tooltip. Click through to a country page.

**Minutes 8–14: Country Intelligence deep dive**
Choose South Africa — strongest narrative (energy crisis, mining recovery, election risk, Load Shedding). Walk through the charts. Explain how the anomaly markers come from Pandas Z-scores before the LLM ever sees the data.

**Minutes 14–22: How It Works + Agentic thinking**
This is the technical argument. Walk through the pipeline diagram. Spend time on the PROMPT STRATEGY section. Explain the two-step chain explicitly: *"This is agentic thinking — structuring the AI's reasoning process, not just its output."*

**Minutes 22–28: Architecture decisions**
Walk through README. Justify Firestore over BigQuery. Explain Connexion. Show Cloud Run deployment. Mention `europe-west1`.

**Minutes 28–30: Close**
*"The brief asked for a pipeline that extracts data, processes it with AI, and delivers insights. We built a product that does that — one that any ML6 engineer can trigger, observe, and validate end to end from a single URL."*

### Key Q&A Answers

**"Why Connexion?"**
> Connexion is OpenAPI-first — the YAML spec is the source of truth, not the code. It enforces schema validation, authentication, and routing at the framework level before any handler runs. This is how enterprise APIs are designed when the contract matters as much as the implementation.

**"Why Firestore over BigQuery?"**
> Read-heavy, document-shaped workload with no analytical queries. Firestore maps directly to our data model and eliminates operational overhead. The architecture supports BigQuery migration if analytical requirements emerge — that's in the README.

**"Walk me through your prompt engineering."**
> Two-step chain. Step 1 analyses each indicator independently — country, metric, delta, anomaly flag, five years of historical context. Step 2 synthesises all per-indicator outputs into a macro outlook. Single-pass prompting on multi-indicator data causes context collapse. Two-pass gives the model structured, validated inputs to reason from — that's what makes it agentic.

**"How does security work?"**
> API key in the `X-API-Key` header, validated by Connexion's security scheme before any handler executes. Key stored as a Cloud Run environment variable sourced from Secret Manager. In production, the frontend reaches the API through a same-origin proxy that injects the header server-side, so the browser never carries the shared secret.

**"Why europe-west1?"**
> Belgium — your home market. Latency advantage for Benelux clients, and it signals I understood where ML6 operates.

---

## 13. Open Questions

The following are intentionally left open pending testing or further input:

### Model Promotion Threshold
The live baseline is now fixed to `gemma-4-31b-it`, but one open question remains: is that model good enough for both AI steps, or only for per-indicator analysis? The answer depends on the evaluation gate defined by the Live AI integration PRD.

### Netherlands as a Country
Currently 15 countries include Netherlands (NL). Decision: include it. ML6 has an Amsterdam office. Minor signal worth keeping.

### Browser-Facing Auth Hardening
Resolved by the Security, Testing, And Hardening PRD. The deployed frontend uses a same-origin proxy path to the API, and that proxy injects the shared API key server-side. Local development may still use the simpler direct-header pattern.

### Caching vs Live Pipeline
"Refresh Data" should re-fetch the latest persisted state, not trigger a new pipeline run. Running the pipeline remains a separate explicit action.

### AI Parallelism Threshold
The current two-step chain yields 105 AI calls per full run. Step 1 parallelism may become worthwhile if the baseline runtime is too slow, but that should be decided from measured runs rather than added speculatively.

---

## 14. What Makes This Different

A direct assessment of differentiators versus a typical challenge submission.

### What Most Candidates Will Submit
- A Python script that calls the World Bank API
- A single OpenAI call that summarises the data
- A Streamlit dashboard or basic React table
- A README that lists the tech stack

### What This Submission Demonstrates

**1. The Two-Step Agentic Chain**
No other candidate will have visualised their prompt architecture as a deliberate design decision with explicit justification. This directly answers ML6's "agentic thinking" criterion and shows you understand that AI reliability comes from how you structure the reasoning — not which model you use.

**2. The Pipeline Trigger Page**
An interactive live execution page with animated step states and a terminal log is well beyond the brief. It turns a technical requirement into a product moment. The "Run Pipeline" button gives ML6 engineers instant hands-on access to the full system — exactly what the brief says they value.

**3. Production Thinking Throughout**
System Telemetry KPIs, `europe-west1` region choice, Cloud Run scale-to-zero, Secret Manager for API keys, Connexion's OpenAPI-first contract, Firestore schema design — these are production engineering decisions applied to a demo. Most candidates build demos. This is a system.

**4. The AI Disclaimer**
"AI-generated content may contain inaccuracies. Verify before acting." ML6 has a public statement on responsible and trustworthy AI. This footer line — deliberately placed, consistently applied — shows you read it and reflected it in the product.

**5. Design System Discipline**
A documented design system with colour tokens, typography scale, elevation rules, and strict accent usage guidelines applied to a frontend challenge. This demonstrates the full-stack product engineering profile the Unum role requires — not just backend and AI, but end-to-end product craft.

**6. Architecture Decisions are Justified, not Listed**
The README and presentation don't just list the tech stack — they explain why each decision was made and what the trade-off was. Firestore over BigQuery. Two-step over single-pass. europe-west1 over us-central1. These are the answers to Q&A questions before they're asked.

---

*Document maintained alongside build. Update architectural decisions as they are finalised.*  
*Model selection to be confirmed before pipeline development begins.*  
*Last updated: April 2026*
