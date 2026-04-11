/**
 * Pipeline Trigger — live execution UI.
 *
 * The "product moment" — watch the AI work in real time.
 * This is the most interactive page: the user clicks a button,
 * watches the terminal fill with pipeline output, and sees
 * fresh insights populate the dashboard. It proves the system works.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiRequest } from "../api";

const TARGET_COUNTRY = "ZA";

function buildTerminalLines(status) {
  if (!status) {
    return ["> Connecting to pipeline status..."];
  }

  const lines = [
    `> TARGET COUNTRY: ${TARGET_COUNTRY}`,
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

  return (
    <main className="container">
      <header className="section-gap">
        <p className="text-label">PIPELINE CONTROL</p>
        <h1 className="text-display">Execute Pipeline</h1>
        <p className="text-body text-secondary mt-4">
          Run the local first slice for South Africa and poll the ephemeral
          status feed until the briefing is ready.
        </p>
      </header>

      <section className="section-gap">
        <div className="card">
          <div className="panel-header">
            <div>
              <p className="text-label">TARGET</p>
              <h2 className="text-headline">Pipeline Status</h2>
            </div>
            <span
              className={`status-pill status-pill--${status?.status || "idle"}`}
            >
              {(status?.status || "idle").toUpperCase()}
            </span>
          </div>

          <div className="button-row mt-4">
            <button
              className="btn-primary"
              type="button"
              onClick={handleTrigger}
              disabled={isSubmitting || status?.status === "running"}
            >
              {status?.status === "running"
                ? "PIPELINE RUNNING"
                : "RUN ZA PIPELINE"}
            </button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() =>
                navigate(`/country/${TARGET_COUNTRY.toLowerCase()}`)
              }
              disabled={!pipelineReady}
            >
              OPEN ZA BRIEFING
            </button>
          </div>

          {requestError ? (
            <p className="text-body text-critical mt-4">{requestError}</p>
          ) : null}
        </div>
      </section>

      <section className="section-gap">
        <div className="terminal-panel">
          <p className="text-label">TERMINAL OUTPUT</p>
          <pre className="terminal-panel__output text-metric text-secondary mt-3">
            {terminalOutput}
          </pre>
        </div>
      </section>

      <section className="section-gap">
        <div className="card">
          <p className="text-label">RESPONSIBLE AI</p>
          <p className="text-body text-secondary mt-4">
            AI-generated content may contain inaccuracies. Verify before acting.
          </p>
        </div>
      </section>
    </main>
  );
}
