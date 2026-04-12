import { Link } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import {
  PIPELINE_STAGE_MODEL,
  PIPELINE_TRIGGER_MODES,
} from "../pipelineStageModel";

const TELEMETRY_CARDS = [
  {
    label: "Runtime baseline",
    value: "LOCAL-FIRST",
    status: "Current",
    tone: "success",
    freshness:
      "Deterministic local mode stays default; deploy-only switches stay explicit.",
  },
  {
    label: "Narrative chain",
    value: "2-STEP + PANEL",
    status: "Validated",
    tone: "success",
    freshness:
      "Provider-backed AI runs the country chain and the monitored-set overview pass in live mode; local mode stays deterministic for tests.",
  },
  {
    label: "Core panel",
    value: "17 x 6",
    status: "Validated",
    tone: "success",
    freshness:
      "Exact-complete 2024 core panel validated against the World Bank API.",
  },
  {
    label: "Storage seam",
    value: "LOCAL // FIRESTORE",
    status: "Current",
    tone: "success",
    freshness:
      "One repository contract supports local runs and Firestore-backed durable storage.",
  },
];

const ARCHITECTURE_NODES = [
  { label: "World Bank API", state: "current" },
  { label: "Pipeline Orchestrator", state: "current" },
  { label: "Fetch + Normalize", state: "current" },
  { label: "Pandas Analysis", state: "current" },
  { label: "Country + Panel synthesis", state: "current" },
  { label: "Firestore + GCS", state: "target" },
  { label: "Connexion API", state: "current" },
  { label: "React Dashboard", state: "current" },
];

const TECH_STRIP = [
  ["Execution", "Real run stays API-backed; demo walkthrough stays frontend-only"],
  ["Storage", "Local repository by default // durable backends switch on through explicit envs"],
  ["Frontend", "React 18 + Vite + vanilla CSS tokens"],
  ["Proxy", "nginx template defines the same-origin /api/v1/ proxy for cloud deployment"],
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
        description="How World Analyst turns World Bank indicators into analyst-ready country briefings and one monitored-set overview, while keeping real runs truthful and demo walkthroughs clearly simulated."
        eyebrow="SYSTEM FLOW"
        meta="World Bank source · Shared stage model · Spec-first delivery"
        title="How It Works"
      />

      <section className="section-gap">
        <div className="card architecture-cta">
          <div>
            <p className="text-label">Trigger modes</p>
            <h2 className="text-headline mt-3">
              One stage story, two trigger modes
            </h2>
            <p className="text-body text-secondary mt-4">
              Pipeline Trigger now separates truthful real runs from the fast demo
              walkthrough. Both modes use the same shared stage model, but only
              real run touches backend status or stored outputs.
            </p>
          </div>
          <StatusPill tone="neutral">Shared product story</StatusPill>
        </div>
      </section>

      <section className="architecture-mode-grid section-gap">
        {PIPELINE_TRIGGER_MODES.map((mode) => (
          <article className="card architecture-mode-card" key={mode.key}>
            <div className="panel-header">
              <div>
                <p className="text-label">{mode.eyebrow}</p>
                <h2 className="text-headline mt-3">{mode.label}</h2>
              </div>
              <StatusPill tone={mode.tone}>
                {mode.key === "real" ? "LIVE" : "SIMULATED"}
              </StatusPill>
            </div>
            <p className="text-body text-secondary mt-4">{mode.description}</p>
            <div className="architecture-mode-card__detail mt-4">
              <span className="text-label">{mode.boundaryLabel}</span>
              <p className="text-body text-secondary mt-3">
                {mode.boundaryDetail}
              </p>
            </div>
          </article>
        ))}
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
                {node.state === "current" ? "Current" : "Deploy target"}
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
        {PIPELINE_STAGE_MODEL.map((stage, index) => (
          <div className="card architecture-step-card" key={stage.name}>
            <div className="panel-header">
              <div>
                <p className="text-label">
                  Stage {String(index + 1).padStart(2, "0")}
                </p>
                <h2 className="text-headline mt-3">{stage.title}</h2>
              </div>
              <StatusPill tone="neutral">{stage.name}</StatusPill>
            </div>
            <p className="text-body text-secondary mt-4">{stage.story}</p>
            <div className="architecture-step-card__detail mt-4">
              <span className="text-label">Output</span>
              <p className="text-body text-secondary mt-3">{stage.outcome}</p>
            </div>
          </div>
        ))}
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
