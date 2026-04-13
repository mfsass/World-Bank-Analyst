# Plan: Technical Hardening

**Track:** CTO — Close two production gaps before the demo  
**Status:** Implemented  
**Blocked by:** Nothing  
**Effort estimate:** Country Intelligence Phase 1 is 2–3 days frontend. Rate limiting is 1–2 hours backend.  

---

## Goal

Two technical gaps would be hard to defend under direct questioning at the evaluation:

1. **No rate limiting on `POST /pipeline/trigger`** — any API key holder can POST this endpoint repeatedly, each triggering a Cloud Run Job with 119 Gemini calls. There is no cooldown window, no client-side debounce that the server enforces, and no protection against malicious or accidental spam.

2. **Country Intelligence page is the core product promise but reads as a data snapshot** — the README says the product explains direction of travel, magnitude, and anomaly context. The current Country Intelligence page has no historical timeline, no regime label, and no risk-flag prominence. A finance reviewer who opens a country page after reading the README will notice the gap immediately.

---

## Scope

### Fix 1: Rate limit `POST /pipeline/trigger`

**What:** Add a minimum refire window of 24 hours. Before dispatching any pipeline job (local or cloud mode), read the `completed_at` timestamp of the last pipeline status record from the repository. If the last completed run finished within the past 24 hours, return `429 Too Many Requests` with a `Retry-After` header indicating seconds until the window expires.

This is one Firestore read. No new service, no middleware, no infrastructure.

**Carve-out:** The idempotency check (ADR-022) already handles simultaneous requests (`409 Conflict`). The rate limit handles intentional retries from the same or different clients. They are separate concerns.

**Response shape:**
```json
{
  "error": "Pipeline run too recent. Last run completed at <ISO timestamp>.",
  "retry_after_seconds": 86400
}
```

**Affected files:**
- `api/handlers/pipeline.py` — add the cooldown check before dispatch
- `api/openapi.yaml` — add `429` response schema to `POST /pipeline/trigger`
- `api/tests/` — add a test: "trigger within 24h of completed run returns 429"

---

### Fix 2: Country Intelligence Phase 1 (frontend-only)

**What:** The Country Intelligence page already fetches per-country indicator data including `time_series` arrays. This phase surfaces that data visually and adds the elements that make the page deliver on the product's stated promise.

**Phase 1 is frontend-only.** No backend changes, no `openapi.yaml` changes. All required data is already in the API response from `GET /countries/{code}`.

**Deliverables:**

**2a — Historical indicator timeline (Recharts)**  
Replace the current single-year indicator snapshot with a Recharts `LineChart` per indicator showing the full 2010–2024 series. Use the `time_series` array already returned in `IndicatorInsight`. One chart per indicator, or a tabbed chart view if space is a constraint. Mark anomaly years with a dot or color shift using the `is_anomaly` field.

**2b — Regime label badge**  
Surface the `regime_label` field from the country briefing (`GET /countries/{code}`) as a visible badge on the country page header. Regime values: recovery, expansion, overheating, contraction, stagnation. Use a color mapping that aligns with the design system (no raw hex — use CSS custom properties or data-attribute targeting).

**2c — Risk flag prominence**  
Move the `risk_flags` array from the bottom of the page to immediately below the macro synthesis paragraph. Each flag should render as a compact chip or inline list item. This is repositioning existing content, not new data.

**2d — Country directory link**  
Ensure `CountryIntelligenceLanding.jsx` is accessible from the top navigation and from the "Browse all markets" CTA on the Global Overview default state (from the demo polish plan).

**Affected files:**
- `frontend/src/pages/CountryIntelligence.jsx` — timeline charts, regime badge, risk flag repositioning
- `frontend/src/index.css` — regime label color tokens, chart container styles
- `frontend/src/pages/CountryIntelligenceLanding.jsx` — confirm navigation link is wired

---

## Out of scope

- Backend endpoint changes
- Country Intelligence Phase 2 (time-series enrichment in the pipeline) — requires backend work, separate blocked dependency
- Country Intelligence Phase 3 (enriched popover, regime prompt extension) — blocked by Phase 2
- Additional indicator sources beyond what the current API returns

---

## Acceptance criteria

**Rate limiting:**
- [ ] `POST /pipeline/trigger` returns `429` with `Retry-After` header if last completed run was within 24 hours
- [ ] `429` response is documented in `api/openapi.yaml`
- [ ] Test passes: trigger within window → 429; trigger outside window → 202
- [ ] `ruff check api/` passes

**Country Intelligence Phase 1:**
- [ ] Each indicator renders a historical line chart (2010–2024 data points) using Recharts
- [ ] Anomaly years are visually distinguished on the chart
- [ ] `regime_label` badge is visible above the fold on a country page
- [ ] `risk_flags` appear immediately after the macro synthesis paragraph
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

---

## Execution prompt

Paste this into a new conversation with the **world-analyst-dual-lane** agent:

---

> **Task:** Two independent technical hardening items.
>
> **Context:** Read `docs/plans/technical-hardening.md` before starting. For any frontend work, read `.github/skills/world-analyst-design-system/SKILL.md` first and use design system tokens only. For any Python work, read `.github/instructions/api-python.instructions.md` first.
>
> ---
>
> **Item 1 — Rate limit POST /pipeline/trigger (backend, ~2 hours):**  
> In `api/handlers/pipeline.py`, before dispatching any pipeline run (local or cloud), read the `completed_at` timestamp of the last pipeline status record from the repository. If the last completed run finished within the past 86,400 seconds (24 hours), return `429 Too Many Requests` with a `Retry-After` header (seconds remaining) and a JSON body: `{"error": "Pipeline run too recent. Last run completed at <timestamp>.", "retry_after_seconds": <N>}`. Add the `429` response schema to `POST /pipeline/trigger` in `api/openapi.yaml`. Add a test in `api/tests/` that proves: POST within the cooldown window returns 429, POST outside the window proceeds normally. The 24-hour threshold should be configurable via an env var `WORLD_ANALYST_PIPELINE_COOLDOWN_SECONDS` with a default of 86400.
>
> **Item 2 — Country Intelligence Phase 1 (frontend-only, ~2–3 days):**  
> In `frontend/src/pages/CountryIntelligence.jsx`:  
> (a) Replace the single-year indicator snapshot with a Recharts `LineChart` per indicator showing the `time_series` array already returned in each `IndicatorInsight`. Anomaly years (where `is_anomaly` is true) should be visually distinguished — a different dot color or a reference line.  
> (b) Surface the `regime_label` field from the country briefing as a badge visible in the page header, immediately after the country name. Map regime values to neutral color tokens: expansion/recovery = muted green via `var(--status-positive)` or equivalent, overheating = `var(--color-accent)`, contraction/stagnation = `var(--status-negative)`.  
> (c) Move the `risk_flags` list to immediately below the macro synthesis paragraph. Render each flag as a compact chip.  
>
> **Constraints:**  
> - No new backend endpoints, no `openapi.yaml` changes except the 429 addition  
> - No new npm packages without explicit justification  
> - Design system tokens only — no raw hex values  
> - `ruff check api/` and `npm run lint` and `npm run build` must all pass  
> - Log an ADR entry to `docs/DECISIONS.md` only if a genuine fork-in-the-road choice was made (e.g., chart library approach)
