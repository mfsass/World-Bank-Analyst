import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest } from "../api";

const PIPELINE_ACTIVITY_INTERVAL_MS = 900;
const DEFAULT_STEPS = [
  { name: "fetch", status: "pending" },
  { name: "analyse", status: "pending" },
  { name: "synthesise", status: "pending" },
  { name: "store", status: "pending" },
];

const STEP_COPY = {
  dispatch: {
    pending: "Waiting for a Cloud Run Job dispatch request.",
    running: "Dispatching the bounded monitored-set job to Cloud Run.",
    complete: "Cloud Run accepted the job dispatch request.",
    failed: "The run stopped before pipeline execution because Cloud Run dispatch failed.",
  },
  fetch: {
    pending: "Waiting to request the approved World Bank indicator set.",
    running: "Pulling the approved World Bank indicator set for the active monitored panel.",
    complete: "World Bank source data was fetched and normalized for this run.",
    failed: "The run stopped while requesting or normalizing World Bank source data.",
  },
  analyse: {
    pending: "Waiting for the statistical analysis stage.",
    running: "Calculating deltas, stress direction, and anomaly flags with Pandas.",
    complete: "Pandas finished the statistical pass for this run.",
    failed: "The run stopped while computing the statistical signal layer.",
  },
  synthesise: {
    pending: "Waiting for the AI synthesis stage.",
    running:
      "Turning structured signals into analyst-ready notes, country briefings, and one monitored-set overview. This is the longest stage because the model works through the full 17-country panel.",
    complete: "The AI layer produced the country narratives and the monitored-set overview for this run.",
    failed: "The run stopped while generating the analyst narratives.",
  },
  store: {
    pending: "Waiting to persist the finished briefing.",
    running: "Writing processed insights, the monitored-set overview, and runtime status to the configured store.",
    complete: "Processed insights, the monitored-set overview, and status were saved for this run.",
    failed: "The run stopped while persisting the finished outputs.",
  },
};

const STAGE_ACTIVITY_LOG = {
  dispatch: [
    { label: "Validate config", verb: "checking", detail: "Verifying Cloud Run job configuration and runtime credentials." },
    { label: "Reserve slot", verb: "claiming", detail: "Holding the monitored-set run slot so only one execution stays active." },
    { label: "Dispatch job", verb: "launching", detail: "Handing the bounded panel run to Cloud Run Jobs." },
  ],
  fetch: [
    { label: "Open source", verb: "opening", detail: "Connecting to the World Bank Indicators API for the approved panel." },
    { label: "Collect series", verb: "pulling", detail: "Fetching GDP, inflation, labour, fiscal, and external series." },
    { label: "Normalize rows", verb: "shaping", detail: "Normalizing raw indicator payloads into one comparable frame." },
    { label: "Seal ingest", verb: "indexing", detail: "Finalizing the source ingest before the signal pass starts." },
  ],
  analyse: [
    { label: "Frame data", verb: "assembling", detail: "Lining up yearly observations across the monitored indicators." },
    { label: "Score change", verb: "measuring", detail: "Calculating deltas, direction of travel, and stress movement." },
    { label: "Flag anomalies", verb: "screening", detail: "Testing each indicator against anomaly thresholds." },
    { label: "Package signals", verb: "staging", detail: "Preparing the structured signal layer for model input." },
  ],
  synthesise: [
    { label: "Prepare context", verb: "aligning", detail: "Gathering structured indicator evidence for the model." },
    { label: "Write notes", verb: "drafting", detail: "Turning each indicator into analyst-ready signal notes." },
    { label: "Blend signals", verb: "weaving", detail: "Combining risk signals into country-level narratives." },
    { label: "Work queue", verb: "orchestrating", detail: "Moving through the monitored-set country briefing queue." },
    { label: "Compare markets", verb: "reconciling", detail: "Comparing cross-market pressure before the overview pass." },
    { label: "Finish overview", verb: "composing", detail: "Writing the monitored-set overview and risk language." },
    { label: "Check schema", verb: "validating", detail: "Verifying structured output before persistence." },
  ],
  store: [
    { label: "Prepare records", verb: "packaging", detail: "Preparing processed insight, overview, and status payloads." },
    { label: "Write insights", verb: "committing", detail: "Writing country and panel records to the repository." },
    { label: "Archive raw", verb: "archiving", detail: "Recording raw payload provenance for follow-up." },
    { label: "Seal run", verb: "closing", detail: "Finalizing the durable pipeline status contract." },
  ],
};

function getStageActivities(stepName) {
  return (
    STAGE_ACTIVITY_LOG[stepName] || [
      { label: "Processing", verb: "processing", detail: "Working through the current pipeline stage." },
    ]
  );
}

function getActiveStageActivity(stepName, tick) {
  const activities = getStageActivities(stepName);
  return activities[tick % activities.length];
}

function StepSimulation({ stepName, isRunning, tick }) {
  const activities = getStageActivities(stepName);
  const activeActivity = getActiveStageActivity(stepName, tick);

  if (!isRunning) return null;

  return (
    <div className="execution-step-card__activity fade-in">
      <div className="execution-step-card__activity-row">
        <span className="text-label">Live operation</span>
        <span className="execution-step-card__verb">
          {activeActivity.verb}
          <span className="terminal-cursor" />
        </span>
      </div>
      <p className="execution-step-card__simulation text-secondary text-body mt-3">
        &gt; {activeActivity.detail}
      </p>
      <div
        aria-label={`${stepName} sub-steps`}
        className="execution-step-card__track mt-3"
        role="list"
      >
        {activities.map((activity, index) => (
          <span
            className={`execution-step-card__chip${
              activity.label === activeActivity.label
                ? " execution-step-card__chip--active"
                : ""
            }`}
            key={`${stepName}-${activity.label}`}
            role="listitem"
          >
            {String(index + 1).padStart(2, "0")} {activity.label}
          </span>
        ))}
      </div>
    </div>
  );
}

StepSimulation.propTypes = {
  isRunning: PropTypes.bool.isRequired,
  stepName: PropTypes.string.isRequired,
  tick: PropTypes.number.isRequired,
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

function buildTerminalLines(status, activeStageActivity) {
  if (!status) {
    return ["> Connecting to pipeline status..."];
  }

  const lines = [
    "> TARGET SCOPE: 17-COUNTRY PANEL",
    "> COUNTRY PAGE UNLOCKS AFTER COMPLETION",
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

  if (status.status === "running" && activeStageActivity) {
    lines.push(
      `> ACTIVE OPERATION: ${activeStageActivity.verb.toUpperCase()} ${activeStageActivity.label.toUpperCase()}`,
    );
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
  const [simulationTick, setSimulationTick] = useState(0);

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
      setSimulationTick(0);
      return undefined;
    }

    const simulationIntervalId = window.setInterval(() => {
      setSimulationTick((currentTick) => currentTick + 1);
    }, PIPELINE_ACTIVITY_INTERVAL_MS);

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
      window.clearInterval(simulationIntervalId);
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

  const executionSteps = status?.steps?.length ? status.steps : DEFAULT_STEPS;
  const runningStep =
    executionSteps.find((step) => step.status === "running") || null;
  const activeStageActivity = runningStep
    ? getActiveStageActivity(runningStep.name, simulationTick)
    : null;
  const terminalOutput = buildTerminalLines(status, activeStageActivity).join("\n");
  const pipelineReady = status?.status === "complete";
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
              onClick={() => navigate("/country")}
              disabled={!pipelineReady}
            >
              Open country intelligence
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
                  <StepSimulation
                    stepName={step.name}
                    isRunning={isRunning}
                    tick={simulationTick}
                  />
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
