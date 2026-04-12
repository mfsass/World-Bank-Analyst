import { Link } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";

const TELEMETRY_CARDS = [
  {
    label: "Current delivery slice",
    value: "LOCAL DEFAULTS",
    status: "Current",
    tone: "success",
    freshness: "Deterministic local mode stays default; cloud services opt in explicitly",
  },
  {
    label: "Narrative chain",
    value: "2-STEP",
    status: "Current",
    tone: "success",
    freshness: "Two-stage synthesis contract; provider wiring remains a later phase",
  },
  {
    label: "Live monitored panel",
    value: "17 x 6",
    status: "Validated",
    tone: "success",
    freshness: "Seventeen approved countries and six indicators validated against the World Bank API",
  },
  {
    label: "API contract",
    value: "OPENAPI",
    status: "Spec-first",
    tone: "success",
    freshness: "Connexion reads the contract before handlers run",
  },
];

const ARCHITECTURE_NODES = [
  { label: "World Bank API", state: "current" },
  { label: "Pipeline Orchestrator", state: "current" },
  { label: "Pandas Analysis", state: "current" },
  { label: "Two-step synthesis", state: "current" },
  { label: "Firestore + GCS", state: "target" },
  { label: "Connexion API", state: "current" },
  { label: "React Dashboard", state: "current" },
];

const TECH_STRIP = [
  ["Execution", "Local by default // Cloud Run job via explicit envs"],
  ["Storage", "REPOSITORY_MODE=local by default // Cloud Run sets Firestore + GCS"],
  ["Frontend", "React 18 + Vite + vanilla CSS tokens"],
  ["Proxy", "nginx serves the SPA and injects X-API-Key on same-origin /api/v1/ calls"],
  ["Contract", "OpenAPI-first via Connexion"],
];

export function HowItWorks() {
  return (
    <div className="page page--how-it-works container">
      <PageHeader
        actions={
          <div className="button-row">
            <Link className="btn-primary" to="/trigger">
              Open trigger page
            </Link>
            <Link className="btn-ghost" to="/">
              Return to overview
            </Link>
          </div>
        }
        description="How World Analyst turns World Bank indicators into analyst-ready country briefings. Local defaults and cloud deployment settings are labeled separately."
        eyebrow="SYSTEM FLOW"
        meta="World Bank source · Two-step synthesis contract · Spec-first delivery"
        title="How It Works"
      />

      <section className="section-gap">
        <div className="card architecture-cta">
          <div>
            <p className="text-label">Live pipeline CTA</p>
            <h2 className="text-headline mt-3">
              Trigger the same World Bank Analyst flow the dashboard reads
            </h2>
            <p className="text-body text-secondary mt-4">
              The trigger page runs the current pipeline flow end to end. This page explains which parts are already live, which settings stay local by default, and which cloud choices are activated explicitly at deploy time.
            </p>
          </div>
          <StatusPill tone="warning">Current + target</StatusPill>
        </div>
      </section>

      <section className="kpi-row section-gap">
        {TELEMETRY_CARDS.map((card) => (
          <KpiCard
            freshness={card.freshness}
            key={card.label}
            label={card.label}
            status={card.status}
            statusTone={card.tone}
            value={card.value}
          />
        ))}
      </section>

      <section className="card section-gap">
        <div className="panel-header">
          <div>
            <p className="text-label">Architecture diagram</p>
            <h2 className="text-headline mt-3">
              Data moves through explicit stages
            </h2>
          </div>
          <StatusPill tone="neutral">Claim-traceable</StatusPill>
        </div>
        <div className="architecture-flow mt-4">
          {ARCHITECTURE_NODES.map((node) => (
            <div className="architecture-flow__node" key={node.label}>
              <div
                className={`architecture-flow__chip architecture-flow__chip--${node.state}`}
              >
                {node.state === "current" ? "Current" : "Target"}
              </div>
              <h3 className="text-title mt-3">{node.label}</h3>
            </div>
          ))}
        </div>
      </section>

      <section className="architecture-io-grid section-gap">
        <div className="card architecture-code-card">
          <div className="panel-header">
            <div>
              <p className="text-label">Input example</p>
              <h2 className="text-headline mt-3">Normalized World Bank record</h2>
            </div>
            <StatusPill tone="success">Current</StatusPill>
          </div>
          <pre className="architecture-code-block mt-4">
            {`{
  "country_code": "BR",
  "indicator_code": "FP.CPI.TOTL.ZG",
  "year": 2023,
  "latest_value": 5.9,
  "percent_change": 1.1,
  "is_anomaly": false
}`}
          </pre>
        </div>

        <AIInsightPanel
          eyebrow="Output example"
          status="Current"
          title="Country briefing payload"
          tone="success"
        >
          <pre className="architecture-code-block">
            {`{
  "code": "BR",
  "macro_synthesis": "Inflation remains elevated...",
  "outlook": "cautious",
  "risk_flags": [
    "Inflation remains above comfort range",
    "Debt pressure limits fiscal room"
  ]
}`}
          </pre>
        </AIInsightPanel>
      </section>

      <section className="architecture-prompt-grid section-gap">
        <div className="card architecture-step-card">
          <p className="text-label">Step 1</p>
          <h2 className="text-headline mt-3">Per-indicator analysis</h2>
          <p className="text-body text-secondary mt-4">
            Pandas calculates deltas, trend shifts, and anomaly flags first. The first synthesis stage then writes a short analyst note for one indicator at a time, which keeps the contract narrow and the result auditable.
          </p>
        </div>
        <div className="card architecture-step-card">
          <p className="text-label">Step 2</p>
          <h2 className="text-headline mt-3">Macro synthesis</h2>
          <p className="text-body text-secondary mt-4">
            The second synthesis stage receives only the structured indicator notes. It builds the country story, sets the outlook, and returns risk flags the frontend can render directly.
          </p>
        </div>
      </section>

      <section className="architecture-spec-strip section-gap">
        {TECH_STRIP.map(([label, value]) => (
          <article className="architecture-spec-strip__item" key={label}>
            <span className="text-label">{label}</span>
            <span className="text-body mt-3">{value}</span>
          </article>
        ))}
      </section>
    </div>
  );
}
