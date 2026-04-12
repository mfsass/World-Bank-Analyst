import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest } from "../api";

// Default deep-link target after a successful run — first country in the monitored panel.
const TARGET_COUNTRY = "BR";
const DEFAULT_STEPS = [
  { name: "fetch", status: "pending" },
  { name: "analyse", status: "pending" },
  { name: "synthesise", status: "pending" },
  { name: "store", status: "pending" },
];

const STEP_COPY = {
  fetch: {
    pending: "Waiting to request the approved World Bank indicator set.",
    running: "Pulling World Bank source data for the active market slice.",
    complete: "World Bank source data was fetched and normalized for this run.",
    failed: "The run stopped while requesting or normalizing World Bank source data.",
  },
  analyse: {
    pending: "Waiting for the statistical analysis stage.",
    running: "Calculating deltas, trend shifts, and anomaly flags with Pandas.",
    complete: "Pandas finished the statistical pass for this run.",
    failed: "The run stopped while computing the statistical signal layer.",
  },
  synthesise: {
    pending: "Waiting for the AI synthesis stage.",
    running: "Turning structured signals into analyst-ready notes and a country briefing.",
    complete: "The AI layer produced the analyst narratives for this run.",
    failed: "The run stopped while generating the analyst narratives.",
  },
  store: {
    pending: "Waiting to persist the finished briefing.",
    running: "Writing processed insights and runtime status to the configured store.",
    complete: "Processed insights and status were saved for this run.",
    failed: "The run stopped while persisting the finished outputs.",
  },
};

const STAGE_SIMULATIONS = {
  fetch: [
    "Connecting to World Bank Indicators API...",
    "Fetching GDP growth series...",
    "Fetching inflation series...",
    "Fetching unemployment series...",
    "Normalizing source payloads...",
    "Completing source ingest..."
  ],
  analyse: [
    "Building analysis frame...",
    "Calculating deltas and trend shifts...",
    "Scoring anomaly thresholds...",
    "Packaging the signal layer..."
  ],
  synthesise: [
    "Preparing structured prompt context...",
    "Writing indicator notes...",
    "Drafting country synthesis...",
    "Scoring risk language..."
  ],
  store: [
    "Validating response payload...",
    "Writing processed insight record...",
    "Writing raw archive manifest...",
    "Finalizing pipeline status..."
  ]
};

function StepSimulation({ stepName, isRunning }) {
  const [index, setIndex] = useState(0);
  const phrases = STAGE_SIMULATIONS[stepName] || ["Processing..."];

  useEffect(() => {
    if (!isRunning) return undefined;
    
    // Cycle through phrases roughly synchronized to the polling interval
    const intervalId = window.setInterval(() => {
      setIndex((prev) => (prev + 1) % phrases.length);
    }, 750);
    
    return () => clearInterval(intervalId);
  }, [isRunning, phrases.length]);

  if (!isRunning) return null;

  return (
    <span className="execution-step-card__simulation text-secondary text-body fade-in">
      &gt; {phrases[index]}
    </span>
  );
}

StepSimulation.propTypes = {
  isRunning: PropTypes.bool.isRequired,
  stepName: PropTypes.string.isRequired,
};

function getStatusTone(status) {
  if (status === "complete") {
    return "success";
  }

  if (status === "failed") {
    return "critical";
  }

  if (status === "running") {
    return "running";
  }

  return "neutral";
}

function formatDuration(status) {
  if (!status?.started_at || !status?.completed_at) {
    return "Awaiting completion";
  }

  const startedAt = new Date(status.started_at).getTime();
  const completedAt = new Date(status.completed_at).getTime();
  return `${((completedAt - startedAt) / 1000).toFixed(2)}s`;
}

function getExecutionCopy(step) {
  const statusCopy = STEP_COPY[step.name]?.[step.status];

  if (step.duration_ms && statusCopy) {
    return `${statusCopy} Latest duration: ${step.duration_ms}ms.`;
  }

  if (statusCopy) {
    return statusCopy;
  }

  return "Waiting for the next execution request.";
}

function buildTerminalLines(status) {
  if (!status) {
    return ["> Connecting to pipeline status..."];
  }

  const lines = [
    "> TARGET SCOPE: 17-COUNTRY PANEL",
    `> DEFAULT OPEN MARKET: ${TARGET_COUNTRY}`,
    `> STATUS: ${status.status.toUpperCase()}`,
  ];

  if (status.started_at) {
    lines.push(`> STARTED AT: ${formatTimestamp(status.started_at)}`);
  }

  if (status.steps?.length) {
    status.steps.forEach((step) => {
      const duration = step.duration_ms ? ` ${step.duration_ms}ms` : "";
      lines.push(
        `> ${step.name.toUpperCase().padEnd(10, " ")} ${step.status.toUpperCase()}${duration}`,
      );
    });
  }

  if (status.completed_at) {
    lines.push(`> COMPLETED AT: ${formatTimestamp(status.completed_at)}`);
  }

  if (status.error) {
    lines.push(`> ERROR: ${status.error}`);
  }

  if (status.status === "idle") {
    lines.push("> Awaiting pipeline execution...");
  }

  return lines;
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString();
}

export function PipelineTrigger() {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [requestError, setRequestError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isActive = true;

    async function loadStatus() {
      try {
        const nextStatus = await apiRequest("/pipeline/status");
        if (isActive) {
          setStatus(nextStatus);
          setRequestError("");
        }
      } catch (error) {
        if (isActive) {
          setRequestError(error.message);
        }
      }
    }

    loadStatus();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (status?.status !== "running") {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const nextStatus = await apiRequest("/pipeline/status");
        setStatus(nextStatus);
        setRequestError("");
        if (nextStatus.status !== "running") {
          window.clearInterval(intervalId);
        }
      } catch (error) {
        setRequestError(error.message);
        window.clearInterval(intervalId);
      }
    }, 750);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [status?.status]);

  async function handleTrigger() {
    setIsSubmitting(true);
    try {
      const nextStatus = await apiRequest("/pipeline/trigger", {
        method: "POST",
      });
      setStatus(nextStatus);
      setRequestError("");
    } catch (error) {
      if (error.status === 409 && error.payload) {
        setStatus(error.payload);
      }
      setRequestError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const terminalOutput = buildTerminalLines(status).join("\n");
  const pipelineReady = status?.status === "complete";
  const executionSteps = status?.steps?.length ? status.steps : DEFAULT_STEPS;
  const completedSteps = executionSteps.filter(
    (step) => step.status === "complete",
  ).length;

  return (
    <div className="page page--trigger container">
      <PageHeader
        actions={
          <div className="button-row">
            <button
              className="btn-primary"
              type="button"
              onClick={handleTrigger}
              disabled={isSubmitting || status?.status === "running"}
            >
              {status?.status === "running"
                ? "Pipeline running"
                : "Run pipeline"}
            </button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() =>
                navigate(`/country/${TARGET_COUNTRY.toLowerCase()}`)
              }
              disabled={!pipelineReady}
            >
              Open lead market
            </button>
          </div>
        }
        description="Run the current World Bank Analyst pipeline and watch each stage complete in real time."
        eyebrow="PIPELINE CONTROL"
        meta="World Bank fetch · AI synthesis · live status polling"
        title="Pipeline Trigger"
      />

      <section className="kpi-row section-gap">
        <KpiCard
          freshness={
            status?.started_at
              ? `STARTED ${formatTimestamp(status.started_at)}`
              : "AWAITING TRIGGER"
          }
          label="Pipeline Status"
          status={(status?.status || "idle").toUpperCase()}
          statusTone={getStatusTone(status?.status)}
          value={(status?.status || "idle").toUpperCase()}
        />
        <KpiCard
          freshness={
            status?.completed_at
              ? `COMPLETED ${formatTimestamp(status.completed_at)}`
              : "NO COMPLETED RUN YET"
          }
          label="Last Run Duration"
          status={status?.completed_at ? "Available" : "Pending"}
          statusTone={status?.completed_at ? "success" : "neutral"}
          value={formatDuration(status)}
        />
        <KpiCard
          freshness={`${executionSteps.length} TRACKED STAGES`}
          label="Stages Completed"
          status={`${completedSteps}/${executionSteps.length}`}
          statusTone={completedSteps > 0 ? "success" : "neutral"}
          value={completedSteps}
        />
        <KpiCard
          freshness="17-COUNTRY PANEL ACTIVE"
          label="Current Scope"
          status="Live panel"
          statusTone="success"
          value="17 MARKETS"
        />
      </section>

      <section className="section-gap">
        <div className="card trigger-hero">
          <div className="panel-header">
            <div>
              <p className="text-label">TARGET</p>
              <h2 className="text-headline mt-3">
                Run the active World Bank Analyst pipeline
              </h2>
              <p className="text-body text-secondary mt-4">
                This flow fetches World Bank data, analyses the signal, writes the AI briefing, and stores the result for the dashboard.
              </p>
            </div>
            <StatusPill tone={getStatusTone(status?.status)}>
              {(status?.status || "idle").toUpperCase()}
            </StatusPill>
          </div>

          <div className="button-row mt-4">
            <Link className="shell-inline-link" to="/">
              Return to overview
            </Link>
            <Link className="shell-inline-link" to="/pipeline">
              Open architecture page
            </Link>
          </div>

          {requestError ? (
            <p className="text-body text-critical mt-4">{requestError}</p>
          ) : null}
        </div>
      </section>

      <section className="trigger-grid section-gap">
        <div className="card">
          <div className="panel-header">
            <div>
              <p className="text-label">Execution sequence</p>
              <h2 className="text-headline mt-3">Tracked pipeline stages</h2>
            </div>
            <StatusPill tone={getStatusTone(status?.status)}>
              {completedSteps}/{executionSteps.length}
            </StatusPill>
          </div>
          <div className="execution-step-list mt-4">
            {executionSteps.map((step) => {
              const isRunning = step.status === "running";
              return (
                <article
                  className={`execution-step-card execution-step-card--${getStatusTone(step.status)} ${isRunning ? 'is-animating-border' : ''}`}
                  key={step.name}
                >
                  <div className="panel-header">
                    <div>
                      <p className="text-label">Stage</p>
                      <h3 className="text-title mt-3">{step.name}</h3>
                    </div>
                    <StatusPill tone={getStatusTone(step.status)}>
                      {isRunning ? (
                        <span className="status-pill__running-label">
                          RUNNING <span className="terminal-cursor" />
                        </span>
                      ) : (
                        step.status.toUpperCase()
                      )}
                    </StatusPill>
                  </div>
                  <p className="text-body text-secondary mt-4">
                    {getExecutionCopy(step)}
                  </p>
                  <StepSimulation stepName={step.name} isRunning={isRunning} />
                </article>
              );
            })}
          </div>
        </div>

        <div className="terminal-panel">
          <p className="text-label">Live status feed</p>
          <pre className="terminal-panel__output text-metric text-secondary mt-3">
            {terminalOutput}
            {status?.status === "running" && <span className="terminal-cursor" />}
          </pre>
        </div>
      </section>
    </div>
  );
}
