import { Link } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";

const TELEMETRY_CARDS = [
  {
    label: "Current delivery slice",
    value: "LOCAL + DURABLE",
    status: "Current",
    tone: "success",
    freshness: "API, trigger, and stored briefings are already wired",
  },
  {
    label: "AI chain",
    value: "2-STEP",
    status: "Approved",
    tone: "success",
    freshness: "Per-indicator analysis followed by macro synthesis",
  },
  {
    label: "Source scope",
    value: "15 x 6",
    status: "Target",
    tone: "warning",
    freshness: "Fifteen countries and six approved indicators",
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
  { label: "AI Chain", state: "current" },
  { label: "Firestore + GCS", state: "target" },
  { label: "Connexion API", state: "current" },
  { label: "React Terminal", state: "current" },
];

const TECH_STRIP = [
  ["Execution", "Cloud Run job target // local trigger path today"],
  ["Storage", "Firestore + GCS target // local mode remains supported"],
  ["Frontend", "React 18 + Vite + vanilla CSS tokens"],
  ["Contract", "OpenAPI-first via Connexion"],
];

export function HowItWorks() {
  return (
    <div className="page page--how-it-works container">
      <PageHeader
        actions={
          <div className="shell-command-row">
            <Link className="shell-command-link shell-command-link--accent" to="/trigger">
              Open trigger page
            </Link>
            <Link className="shell-command-link" to="/">
              Return to overview
            </Link>
          </div>
        }
        description="How World Bank Analyst turns World Bank indicators into analyst-ready country briefings. Live components and target architecture are labeled separately."
        eyebrow="SYSTEM FLOW"
        meta="World Bank source · Two-step LLM chain · Spec-first delivery"
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
              The trigger page runs the current pipeline flow end to end. This page explains each stage, what is already live, and what remains a target runtime decision.
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
            Pandas calculates deltas, trend shifts, and anomaly flags first. The first model call then writes a short analyst note for one indicator at a time, which keeps the prompt narrow and the result auditable.
          </p>
        </div>
        <div className="card architecture-step-card">
          <p className="text-label">Step 2</p>
          <h2 className="text-headline mt-3">Macro synthesis</h2>
          <p className="text-body text-secondary mt-4">
            The second model call receives only the structured indicator notes. It synthesizes the country story, sets the outlook, and returns risk flags the frontend can render directly.
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
