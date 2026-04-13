import { useState } from "react";
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
  { label: "Country + overview synthesis", state: "current" },
  { label: "Firestore + GCS", state: "current" },
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
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const activeStage =
    PIPELINE_STAGE_MODEL[activeStageIndex] || PIPELINE_STAGE_MODEL[0];
  const isFirstStage = activeStageIndex === 0;
  const isLastStage = activeStageIndex === PIPELINE_STAGE_MODEL.length - 1;

  function moveStage(direction) {
    setActiveStageIndex((currentIndex) =>
      Math.min(
        PIPELINE_STAGE_MODEL.length - 1,
        Math.max(0, currentIndex + direction),
      ),
    );
  }

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
  "data_year": 2024,
  "latest_value": 4.6,
  "change_value": -4.7,
  "change_basis": "percentage_point",
  "signal_polarity": "lower_is_better",
  "is_anomaly": false,
  "anomaly_basis": null
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
  "regime_label": "stagnation",
  "outlook": "cautious",
  "source_date_range": "2010:2024",
  "risk_flags": [
    "Inflation remains above comfort range",
    "Debt pressure limits fiscal room"
  ]
}`}
          </pre>
        </AIInsightPanel>
      </section>

      <section className="architecture-prompt-grid section-gap">
        <article className="card architecture-step-card architecture-step-card--active">
          <div className="panel-header">
            <div>
              <p className="text-label">
                Stage {String(activeStageIndex + 1).padStart(2, "0")}
              </p>
              <h2 className="text-headline mt-3">{activeStage.title}</h2>
            </div>
            <StatusPill tone="neutral">{activeStage.name}</StatusPill>
          </div>
          <p className="text-body text-secondary mt-4">{activeStage.story}</p>
          <div className="architecture-step-card__detail mt-4">
            <span className="text-label">Output</span>
            <p className="text-body text-secondary mt-3">{activeStage.outcome}</p>
          </div>
          <div className="architecture-step-card__detail mt-4">
            <span className="text-label">Stage activity</span>
            <div className="architecture-step-card__activity-list mt-3">
              {activeStage.activities.map((activity) => (
                <div
                  className="architecture-step-card__activity"
                  key={activity.label}
                >
                  <p className="text-label">{activity.label}</p>
                  <p className="architecture-step-card__activity-verb mt-2">
                    {activity.verb}
                  </p>
                  <p className="text-body text-secondary mt-3">
                    {activity.detail}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="card architecture-step-sequence">
          <div className="panel-header">
            <div>
              <p className="text-label">Interactive sequence</p>
              <h2 className="text-headline mt-3">Current step lit, next steps dimmed</h2>
            </div>
            <StatusPill tone="neutral">
              {String(activeStageIndex + 1).padStart(2, "0")} /{" "}
              {String(PIPELINE_STAGE_MODEL.length).padStart(2, "0")}
            </StatusPill>
          </div>

          <div className="architecture-step-sequence__list mt-4">
            {PIPELINE_STAGE_MODEL.map((stage, index) => {
              const isActive = index === activeStageIndex;
              const stateLabel = isActive
                ? "Current"
                : index < activeStageIndex
                  ? "Reviewed"
                  : "Up next";

              return (
                <button
                  aria-current={isActive ? "step" : undefined}
                  className={`architecture-step-sequence__item ${
                    isActive
                      ? "architecture-step-sequence__item--active"
                      : "architecture-step-sequence__item--inactive"
                  }`}
                  key={stage.name}
                  onClick={() => setActiveStageIndex(index)}
                  type="button"
                >
                  <div className="architecture-step-sequence__meta">
                    <div>
                      <p className="architecture-step-sequence__index">
                        Stage {String(index + 1).padStart(2, "0")}
                      </p>
                      <h3 className="text-title mt-2">{stage.title}</h3>
                    </div>
                    <span className="architecture-step-sequence__status">
                      {stateLabel}
                    </span>
                  </div>
                  <p className="text-body text-secondary mt-3">
                    {stage.latencyNote}
                  </p>
                </button>
              );
            })}
          </div>

          <div className="architecture-step-sequence__controls mt-4">
            <button
              className="btn-ghost"
              disabled={isFirstStage}
              onClick={() => moveStage(-1)}
              type="button"
            >
              Previous
            </button>
            <button
              className="btn-primary"
              disabled={isLastStage}
              onClick={() => moveStage(1)}
              type="button"
            >
              Next
            </button>
          </div>
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
