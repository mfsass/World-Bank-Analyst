import { Link } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";

const TELEMETRY_CARDS = [
  {
    label: "Runtime baseline",
    value: "LOCAL-FIRST",
    status: "Current",
    tone: "success",
    freshness: "Deterministic local mode stays default; deploy-only switches stay explicit.",
  },
  {
    label: "Narrative chain",
    value: "2-STEP + PANEL",
    status: "Validated",
    tone: "success",
    freshness: "Provider-backed AI runs the country chain and the monitored-set overview pass in live mode; local mode stays deterministic for tests.",
  },
  {
    label: "Core panel",
    value: "17 x 6",
    status: "Validated",
    tone: "success",
    freshness: "Exact-complete 2024 core panel validated against the World Bank API.",
  },
  {
    label: "Storage seam",
    value: "LOCAL // FIRESTORE",
    status: "Current",
    tone: "success",
    freshness: "One repository contract supports local runs and Firestore-backed durable storage.",
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
  ["Execution", "Local-first runtime // Cloud Run job stays the deploy target"],
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
        description="How World Analyst turns World Bank indicators into analyst-ready country briefings and one monitored-set overview. Repo-current behavior and deploy-only runtime switches stay labeled separately."
        eyebrow="SYSTEM FLOW"
        meta="World Bank source · Country + panel synthesis contract · Spec-first delivery"
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
              The trigger page runs the current pipeline flow end to end. It now
              shows how World Bank records become indicator signals, country
              briefings, and one monitored-set overview so the global page stays
              distinct from the country drilldown page.
            </p>
          </div>
          <StatusPill tone="neutral">Current + deploy target</StatusPill>
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
        <div className="card architecture-step-card">
          <p className="text-label">Step 1</p>
          <h2 className="text-headline mt-3">Fetch and normalize</h2>
          <p className="text-body text-secondary mt-4">
            The pipeline requests the approved World Bank indicator panel, drops unusable rows, and reshapes the response into one normalized record per country-indicator-year before any AI stage runs.
          </p>
        </div>
        <div className="card architecture-step-card">
          <p className="text-label">Step 2</p>
          <h2 className="text-headline mt-3">Statistical signal layer</h2>
          <p className="text-body text-secondary mt-4">
            Pandas calculates deltas, trend shifts, and anomaly flags first. That keeps the analysis prompts narrow and the result auditable because the math is already settled before narrative generation starts.
          </p>
        </div>
        <div className="card architecture-step-card">
          <p className="text-label">Step 3</p>
          <h2 className="text-headline mt-3">Country synthesis</h2>
          <p className="text-body text-secondary mt-4">
            The first live synthesis stage writes one note per indicator, then rolls those structured notes into a country briefing with outlook and risk flags the drilldown page can render directly.
          </p>
        </div>
        <div className="card architecture-step-card">
          <p className="text-label">Step 4</p>
          <h2 className="text-headline mt-3">Panel overview + storage</h2>
          <p className="text-body text-secondary mt-4">
            A final pass synthesizes all stored country briefings into one cross-country overview, then persists both the overview and country outputs to the shared repository.
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
