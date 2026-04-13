import PropTypes from "prop-types";
import { createPortal } from "react-dom";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../api";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import {
  PIPELINE_STAGE_MODEL,
  PIPELINE_TRIGGER_MODES,
  buildDefaultPipelineSteps,
  decoratePipelineSteps,
  getActivePipelineStageActivity,
  getPipelineStageActivities,
  getPipelineStageStatusCopy,
} from "../pipelineStageModel";

const PIPELINE_ACTIVITY_INTERVAL_MS = 900;
const PIPELINE_REPLAY_ACTIVITY_INTERVAL_MS = 900;
const PIPELINE_REPLAY_STAGE_ADVANCE_MS = 2600;

const PENDING_VERBS = [
  "Accomplishing", "Actioning", "Actualizing", "Architecting", "Baking", "Beaming",
  "Beboppin'", "Befuddling", "Billowing", "Blanching", "Bloviating", "Boogieing",
  "Boondoggling", "Booping", "Bootstrapping", "Brewing", "Bunning", "Burrowing",
  "Calculating", "Canoodling", "Caramelizing", "Cascading", "Catapulting",
  "Cerebrating", "Channeling", "Channelling", "Choreographing", "Churning",
  "Clauding", "Coalescing", "Cogitating", "Combobulating", "Composing", "Computing",
  "Concocting", "Considering", "Contemplating", "Cooking", "Crafting", "Creating",
  "Crunching", "Crystallizing", "Cultivating", "Deciphering", "Deliberating",
  "Determining", "Dilly-dallying", "Discombobulating", "Doing", "Doodling",
  "Drizzling", "Ebbing", "Effecting", "Elucidating", "Embellishing", "Enchanting",
  "Envisioning", "Evaporating", "Fermenting", "Fiddle-faddling", "Finagling",
  "Flambéing", "Flibbertigibbeting", "Flowing", "Flummoxing", "Fluttering",
  "Forging", "Forming", "Frolicking", "Frosting", "Gallivanting", "Galloping",
  "Garnishing", "Generating", "Gesticulating", "Germinating", "Gitifying",
  "Grooving", "Gusting", "Harmonizing", "Hashing", "Hatching", "Herding",
  "Honking", "Hullaballooing", "Hyperspacing", "Ideating", "Imagining",
  "Improvising", "Incubating", "Inferring", "Infusing", "Ionizing", "Jitterbugging",
  "Julienning", "Kneading", "Leavening", "Levitating", "Lollygagging", "Manifesting",
  "Marinating", "Meandering", "Metamorphosing", "Misting", "Moonwalking", "Moseying",
  "Mulling", "Mustering", "Musing", "Nebulizing", "Nesting", "Newspapering",
  "Noodling", "Nucleating", "Orbiting", "Orchestrating", "Osmosing", "Perambulating",
  "Percolating", "Perusing", "Philosophising", "Photosynthesizing", "Pollinating",
  "Pondering", "Pontificating", "Pouncing", "Precipitating", "Prestidigitating",
  "Processing", "Proofing", "Propagating", "Puttering", "Puzzling", "Quantumizing",
  "Razzle-dazzling", "Razzmatazzing", "Recombobulating", "Reticulating", "Roosting",
  "Ruminating", "Sautéing", "Scampering", "Schlepping", "Scurrying", "Seasoning",
  "Shenaniganing", "Shimmying", "Simmering", "Skedaddling", "Sketching", "Slithering",
  "Smooshing", "Sock-hopping", "Spelunking", "Spinning", "Sprouting", "Stewing",
  "Sublimating", "Swirling", "Swooping", "Symbioting", "Synthesizing", "Tempering",
  "Thinking", "Thundering", "Tinkering", "Tomfoolering", "Topsy-turvying",
  "Transfiguring", "Transmuting", "Twisting", "Undulating", "Unfurling",
  "Unravelling", "Vibing", "Waddling", "Wandering", "Warping", "Whatchamacalliting",
  "Whirlpooling", "Whirring", "Whisking", "Wibbling", "Working"
];

function getPendingVerb(index, tick) {
  const hash = index * 37 + tick;
  return PENDING_VERBS[hash % PENDING_VERBS.length].toUpperCase();
}

function prefersReducedMotion() {
  return (
    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false
  );
}

function FormattedStory({ text }) {
  if (!text) return null;
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <span className="text-accent" style={{ fontWeight: 600 }} key={index}>
              {part.slice(2, -2)}
            </span>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

FormattedStory.propTypes = {
  text: PropTypes.string,
};

function buildDemoStatus() {
  return {
    status: "idle",
    steps: PIPELINE_STAGE_MODEL.map((stage) => ({
      name: stage.name,
      status: "pending",
    })),
  };
}

function getFocusableNodes(container) {
  if (!container) return [];

  return Array.from(
    container.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
}

function StepSimulation({ activityLabel, isRunning, stepName, tick }) {
  const activities = getPipelineStageActivities(stepName);
  const activeActivity = getActivePipelineStageActivity(stepName, tick);

  if (!isRunning) return null;

  return (
    <div className="execution-step-card__activity fade-in">
      <div className="execution-step-card__activity-row">
        <span className="text-label">{activityLabel}</span>
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
  activityLabel: PropTypes.string.isRequired,
  isRunning: PropTypes.bool.isRequired,
  stepName: PropTypes.string.isRequired,
  tick: PropTypes.number.isRequired,
};

function getStatusTone(status) {
  if (status === "complete") return "success";
  if (status === "failed") return "critical";
  if (status === "running") return "running";
  return "neutral";
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString();
}

function buildStatusFreshness(mode, status) {
  if (status?.completed_at) {
    return `COMPLETED ${formatTimestamp(status.completed_at)}`;
  }

  if (status?.started_at) {
    return `STARTED ${formatTimestamp(status.started_at)}`;
  }

  return mode === "real"
    ? "AWAITING REAL RUN"
    : "REPLAYABLE FRONTEND WALKTHROUGH";
}

function getExecutionCopy(step) {
  const statusCopy = getPipelineStageStatusCopy(step.name, step.status);

  if (step.duration_ms && statusCopy) {
    return `${statusCopy} Latest duration: ${step.duration_ms}ms.`;
  }

  return statusCopy;
}

function buildTerminalLines(mode, status, executionSteps, activeStageActivity, activityTick) {
  const nodes = [];

  const addLine = (text) => nodes.push(<span key={nodes.length}>{text}{"\n"}</span>);

  addLine(`> MODE: ${mode === "real" ? "REAL RUN" : "DEMO WALKTHROUGH (SIMULATED)"}`);
  addLine(mode === "real" ? "> SOURCE: /PIPELINE/TRIGGER + /PIPELINE/STATUS" : "> SOURCE: FRONTEND-ONLY REPLAY (NO API CALLS)");
  addLine(`> STAGE MODEL: ${executionSteps.map((step) => step.name.toUpperCase()).join(" -> ")}`);
  addLine("> TARGET SCOPE: 17-COUNTRY PANEL");
  addLine(`> STATUS: ${(status?.status || "idle").toUpperCase()}`);

  if (status?.started_at) {
    addLine(`> STARTED AT: ${formatTimestamp(status.started_at)}`);
  }

  executionSteps.forEach((step, index) => {
    const duration = step.duration_ms ? ` ${step.duration_ms}ms` : "";
    if (step.status === "running") {
      const verb = getPendingVerb(index, 0);
      const dots = ".".repeat((activityTick % 3) + 1);
      nodes.push(
        <span key={`step-${step.name}`}>
          {`> ${step.name.toUpperCase().padEnd(10, " ")} ${verb}${dots}\n`}
        </span>
      );
    } else {
      addLine(`> ${step.name.toUpperCase().padEnd(10, " ")} ${step.status.toUpperCase()}${duration}`);
    }
  });

  if (status?.status === "running" && activeStageActivity) {
    addLine(`> ACTIVE OPERATION: ${activeStageActivity.verb.toUpperCase()} ${activeStageActivity.label.toUpperCase()}`);
  }

  if (mode === "demo") {
    addLine("> COUNTRY PAGE STAYS LOCKED UNTIL A REAL RUN COMPLETES");
  }

  if (status?.completed_at) {
    addLine(`> COMPLETED AT: ${formatTimestamp(status.completed_at)}`);
  }

  if (status?.error) {
    addLine(`> ERROR: ${status.error}`);
  }

  if (!status || status.status === "idle") {
    addLine(
      mode === "real"
        ? "> Awaiting real pipeline execution..."
        : "> Demo walkthrough will replay in the browser only.",
    );
  }

  return nodes;
}

function buildReplaySteps(activeStageIndex, isReplayComplete) {
  return PIPELINE_STAGE_MODEL.map((stage, index) => {
    let status = "pending";

    if (isReplayComplete || index < activeStageIndex) {
      status = "complete";
    } else if (index === activeStageIndex) {
      status = "running";
    }

    return {
      ...stage,
      status,
    };
  });
}

function buildReplayTerminalOutput(activeStep, replaySteps, isReplayComplete, activityTick) {
  const nodes = [];

  const addLine = (text) => nodes.push(<span key={nodes.length}>{text}{"\n"}</span>);

  addLine("> MODE: DEMO WALKTHROUGH (SIMULATED)");
  addLine("> SOURCE: FRONTEND-ONLY REPLAY (NO API CALLS)");
  addLine(`> STAGE MODEL: ${replaySteps.map((step) => step.name.toUpperCase()).join(" -> ")}`);
  addLine("> TARGET SCOPE: 17-COUNTRY PANEL");
  addLine(`> STATUS: ${(isReplayComplete ? "complete" : "running").toUpperCase()}`);

  replaySteps.forEach((step, index) => {
    if (step.status === "running") {
      const verb = getPendingVerb(index, 0);
      const dots = ".".repeat((activityTick % 3) + 1);
      nodes.push(
        <span key={`step-${step.name}`}>
          {`> ${step.name.toUpperCase().padEnd(10, " ")} ${verb}${dots}\n`}
        </span>
      );
    } else {
      addLine(`> ${step.name.toUpperCase().padEnd(10, " ")} ${step.status.toUpperCase()}`);
    }
  });

  if (activeStep) {
    addLine(`> ACTIVE STAGE: ${activeStep.title.toUpperCase()}`);
    addLine(`> OUTCOME: ${activeStep.outcome}`);
  }

  addLine("> COUNTRY PAGE STAYS LOCKED UNTIL A REAL RUN COMPLETES");

  return nodes;
}

function PipelineReplayModal({ isOpen, onClose, replayVersion }) {
  const dialogRef = useRef(null);
  const previousActiveElementRef = useRef(null);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [activityTick, setActivityTick] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);
  const [isReplayComplete, setIsReplayComplete] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    setActiveStageIndex(0);
    setActivityTick(0);
    setIsAutoPlaying(!prefersReducedMotion());
    setIsReplayComplete(false);
  }, [isOpen, replayVersion]);

  useEffect(() => {
    if (!isOpen) return undefined;

    previousActiveElementRef.current = document.activeElement;
    document.body.classList.add("dialog-open");

    const frameId = window.requestAnimationFrame(() => {
      getFocusableNodes(dialogRef.current)[0]?.focus();
    });

    return () => {
      document.body.classList.remove("dialog-open");
      window.cancelAnimationFrame(frameId);
      previousActiveElementRef.current?.focus?.();
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      const focusableNodes = getFocusableNodes(dialogRef.current);
      if (!focusableNodes.length) return;

      const firstNode = focusableNodes[0];
      const lastNode = focusableNodes[focusableNodes.length - 1];

      if (event.shiftKey && document.activeElement === firstNode) {
        event.preventDefault();
        lastNode.focus();
      } else if (!event.shiftKey && document.activeElement === lastNode) {
        event.preventDefault();
        firstNode.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || prefersReducedMotion()) return undefined;

    const intervalId = window.setInterval(() => {
      setActivityTick((currentTick) => currentTick + 1);
    }, PIPELINE_REPLAY_ACTIVITY_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !isAutoPlaying || isReplayComplete) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setActiveStageIndex((currentIndex) => {
        if (currentIndex >= PIPELINE_STAGE_MODEL.length - 1) {
          setIsReplayComplete(true);
          setIsAutoPlaying(false);
          return currentIndex;
        }

        return currentIndex + 1;
      });
    }, PIPELINE_REPLAY_STAGE_ADVANCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [activeStageIndex, isAutoPlaying, isOpen, isReplayComplete]);

  if (!isOpen) return null;

  const replaySteps = buildReplaySteps(activeStageIndex, isReplayComplete);
  const activeStep = replaySteps[activeStageIndex] ?? replaySteps[0];
  const progressValue = isReplayComplete
    ? 100
    : ((activeStageIndex + 1) / replaySteps.length) * 100;
  const modeLabel = isReplayComplete
    ? "COMPLETE"
    : isAutoPlaying
      ? "AUTO-PLAY"
      : "MANUAL";

  function handleReplayReset() {
    setActiveStageIndex(0);
    setActivityTick(0);
    setIsAutoPlaying(!prefersReducedMotion());
    setIsReplayComplete(false);
  }

  function handleStepSelect(stepIndex) {
    setActiveStageIndex(stepIndex);
    setIsAutoPlaying(false);
    setIsReplayComplete(false);
  }

  function handleBack() {
    setIsAutoPlaying(false);
    setIsReplayComplete(false);
    setActiveStageIndex((currentIndex) => Math.max(currentIndex - 1, 0));
  }

  function handleNext() {
    setIsAutoPlaying(false);
    setIsReplayComplete(false);
    setActiveStageIndex((currentIndex) =>
      Math.min(currentIndex + 1, replaySteps.length - 1),
    );
  }

  function handleToggleAutoplay() {
    if (isReplayComplete) {
      handleReplayReset();
      return;
    }

    setIsAutoPlaying((currentValue) => !currentValue);
  }

  return createPortal(
    <div className="pipeline-replay-modal__backdrop">
      <div
        aria-labelledby="pipeline-replay-title"
        aria-modal="true"
        className="pipeline-replay-modal"
        ref={dialogRef}
        role="dialog"
      >
        <div className="pipeline-replay-modal__header">
          <div>
            <p className="text-label">Browser-only replay</p>
            <h2 className="text-headline mt-3" id="pipeline-replay-title">
              Replay walkthrough
            </h2>
            <p className="text-body text-secondary mt-4">
              Step through the shared stage model with slower, presentation-safe
              pacing and no backend writes.
            </p>
          </div>
          <div className="pipeline-replay-modal__header-actions">
            <StatusPill tone={isReplayComplete ? "success" : "warning"}>
              SIMULATED
            </StatusPill>
            <StatusPill tone={isAutoPlaying ? "warning" : "neutral"}>
              {modeLabel}
            </StatusPill>
            <button
              aria-label="Close walkthrough"
              className="btn-ghost pipeline-replay-modal__close"
              onClick={onClose}
              type="button"
            >
              Close
            </button>
          </div>
        </div>

        <div className="pipeline-replay-modal__progress mt-4">
          <span className="text-label">
            Stage {Math.min(activeStageIndex + 1, replaySteps.length)} of{" "}
            {replaySteps.length}
          </span>
          <div
            aria-hidden="true"
            className="pipeline-replay-modal__progress-bar"
          >
            <span
              className="pipeline-replay-modal__progress-fill"
              style={{ width: `${progressValue}%` }}
            />
          </div>
        </div>

        <div className="pipeline-replay-modal__grid mt-4">
          <div className="pipeline-replay-modal__rail">
            {replaySteps.map((step, index) => {
              const isActive = index === activeStageIndex;

              return (
                <button
                  className={`pipeline-replay-modal__rail-card pipeline-replay-modal__rail-card--${step.status}${
                    isActive ? " pipeline-replay-modal__rail-card--active" : ""
                  }`}
                  key={step.name}
                  onClick={() => handleStepSelect(index)}
                  type="button"
                >
                  <span className="pipeline-replay-modal__rail-meta">
                    Stage {String(index + 1).padStart(2, "0")}
                    {" // "}
                    {step.status}
                  </span>
                  <span className="pipeline-replay-modal__rail-title mt-3">
                    {step.title}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="pipeline-replay-modal__detail-stack">
            <div className="card">
              <div className="panel-header">
                <div>
                  <p className="text-label">Active stage</p>
                  <h3 className="text-headline mt-3">{activeStep.title}</h3>
                </div>
                <StatusPill tone={getStatusTone(activeStep.status)}>
                  {activeStep.status.toUpperCase()}
                </StatusPill>
              </div>
              <p className="text-body text-secondary mt-4">
                <FormattedStory text={activeStep.story} />
              </p>
              <div className="execution-step-card__note mt-4">
                <span className="text-label">Stage outcome</span>
                <p className="text-body text-secondary mt-3">
                  {activeStep.outcome}
                </p>
              </div>
              <div className="execution-step-card__note mt-4">
                <span className="text-label">Why this pace helps</span>
                <p className="text-body text-secondary mt-3">
                  {activeStep.latencyNote}
                </p>
              </div>
              <StepSimulation
                activityLabel="Activity"
                isRunning={!isReplayComplete}
                stepName={activeStep.name}
                tick={activityTick}
              />
            </div>

            <div className="terminal-panel">
              <p className="text-label">Presentation feed</p>
              <pre className="terminal-panel__output text-metric text-secondary mt-3">
                {buildReplayTerminalOutput(
                  activeStep,
                  replaySteps,
                  isReplayComplete,
                  activityTick,
                )}
                {!isReplayComplete ? (
                  <span className="terminal-cursor" />
                ) : null}
              </pre>
            </div>
          </div>
        </div>

        <div className="button-row pipeline-replay-modal__footer mt-4">
          <button
            className="btn-ghost"
            disabled={activeStageIndex === 0}
            onClick={handleBack}
            type="button"
          >
            Back
          </button>
          <button
            className="btn-ghost"
            onClick={handleToggleAutoplay}
            type="button"
          >
            {isAutoPlaying ? "Pause auto-play" : "Resume auto-play"}
          </button>
          <button
            className="btn-ghost"
            onClick={handleReplayReset}
            type="button"
          >
            Replay from start
          </button>
          <button
            className="btn-primary"
            disabled={activeStageIndex === replaySteps.length - 1}
            onClick={handleNext}
            type="button"
          >
            Next stage
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

PipelineReplayModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  replayVersion: PropTypes.number.isRequired,
};

export function PipelineTrigger() {
  const navigate = useNavigate();
  const modeButtonRefs = useRef({});
  const [mode, setMode] = useState("real");
  const [status, setStatus] = useState(null);
  const [requestError, setRequestError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activityTick, setActivityTick] = useState(0);
  const [isReplayModalOpen, setIsReplayModalOpen] = useState(false);
  const [demoReplayVersion, setDemoReplayVersion] = useState(0);

  const modeData =
    PIPELINE_TRIGGER_MODES.find((option) => option.key === mode) ||
    PIPELINE_TRIGGER_MODES[0];
  const demoStatus = buildDemoStatus();
  const displayStatus = mode === "real" ? status : demoStatus;
  const executionSteps = decoratePipelineSteps(
    displayStatus?.steps?.length
      ? displayStatus.steps
      : buildDefaultPipelineSteps(),
  );
  const runningStep =
    executionSteps.find((step) => step.status === "running") || null;
  const activeStageActivity = runningStep
    ? getActivePipelineStageActivity(runningStep.name, activityTick)
    : null;
  const terminalOutput = buildTerminalLines(
    mode,
    displayStatus,
    executionSteps,
    activeStageActivity,
    activityTick,
  );
  const pipelineReady = mode === "real" && status?.status === "complete";
  const completedSteps = executionSteps.filter(
    (step) => step.status === "complete",
  ).length;

  useEffect(() => {
    if (mode !== "real") {
      return undefined;
    }

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
  }, [mode]);

  useEffect(() => {
    if (mode !== "real" || status?.status !== "running") {
      return undefined;
    }

    let isActive = true;
    const intervalId = window.setInterval(async () => {
      try {
        const nextStatus = await apiRequest("/pipeline/status");

        if (!isActive) {
          return;
        }

        setStatus(nextStatus);
        setRequestError("");

        if (nextStatus.status !== "running") {
          window.clearInterval(intervalId);
        }
      } catch (error) {
        if (isActive) {
          setRequestError(error.message);
        }
        window.clearInterval(intervalId);
      }
    }, 750);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [mode, status?.status]);

  useEffect(() => {
    if (mode !== "real" || displayStatus?.status !== "running") {
      setActivityTick(0);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setActivityTick((currentTick) => currentTick + 1);
    }, PIPELINE_ACTIVITY_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [displayStatus?.status, mode]);

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

  function handleModeChange(nextMode) {
    setMode(nextMode);
    setRequestError("");
    setIsReplayModalOpen(false);
  }

  function handleModeSwitchKeyDown(event, optionIndex) {
    const lastIndex = PIPELINE_TRIGGER_MODES.length - 1;
    let nextIndex = optionIndex;

    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = optionIndex === lastIndex ? 0 : optionIndex + 1;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = optionIndex === 0 ? lastIndex : optionIndex - 1;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = lastIndex;
    } else {
      return;
    }

    event.preventDefault();
    handleModeChange(PIPELINE_TRIGGER_MODES[nextIndex].key);
    modeButtonRefs.current[PIPELINE_TRIGGER_MODES[nextIndex].key]?.focus();
  }

  function handleDemoReplay() {
    setDemoReplayVersion((currentReplayId) => currentReplayId + 1);
    setIsReplayModalOpen(true);
  }

  return (
    <div className="page page--trigger container">
      <PageHeader
        actions={
          <div
            aria-label="Pipeline mode"
            className="pipeline-mode-switch"
            role="radiogroup"
          >
            {PIPELINE_TRIGGER_MODES.map((option, index) => (
              <button
                aria-checked={mode === option.key}
                className={`pipeline-mode-switch__button${
                  mode === option.key
                    ? " pipeline-mode-switch__button--active"
                    : ""
                }`}
                key={option.key}
                onKeyDown={(event) => handleModeSwitchKeyDown(event, index)}
                onClick={() => handleModeChange(option.key)}
                ref={(node) => {
                  if (node) {
                    modeButtonRefs.current[option.key] = node;
                  }
                }}
                role="radio"
                tabIndex={mode === option.key ? 0 : -1}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
        }
        description="Choose a truthful real run or a frontend-only demo walkthrough. Both use the same stage model and tell the same product story."
        eyebrow="PIPELINE CONTROL"
        meta="Shared stage model · truthful backend state · frontend-only demo"
        title="Pipeline Trigger"
      />

      <section className="section-gap">
        <div className="card trigger-hero">
          <div className="panel-header">
            <div>
              <p className="text-label">{modeData.eyebrow}</p>
              <h2 className="text-headline mt-3">{modeData.title}</h2>
              <p className="text-body text-secondary mt-4">
                {modeData.description}
              </p>
            </div>
            <StatusPill
              tone={
                mode === "demo"
                  ? "warning"
                  : getStatusTone(displayStatus?.status)
              }
            >
              {mode === "demo"
                ? "SIMULATED"
                : (displayStatus?.status || "idle").toUpperCase()}
            </StatusPill>
          </div>

          <div
            className={`pipeline-mode-note pipeline-mode-note--${mode} mt-4`}
          >
            <div>
              <p className="text-label">{modeData.boundaryLabel}</p>
              <p className="text-body text-secondary mt-3">
                {modeData.boundaryDetail}
              </p>
            </div>
            <StatusPill tone={modeData.tone}>
              {mode === "real" ? "LIVE" : "SIMULATED"}
            </StatusPill>
          </div>

          <div className="button-row mt-4">
            <button
              className="btn-primary"
              type="button"
              onClick={mode === "real" ? handleTrigger : handleDemoReplay}
              disabled={
                mode === "real" &&
                (isSubmitting || displayStatus?.status === "running")
              }
            >
              {mode === "real"
                ? displayStatus?.status === "running"
                  ? modeData.replayLabel
                  : isSubmitting
                    ? "Starting real run"
                    : modeData.actionLabel
                : modeData.actionLabel}
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

          {mode === "demo" ? (
            <div className="pipeline-replay-launch-note mt-3">
              <p className="text-label">Replay surface</p>
              <p className="text-body text-secondary mt-3">
                Replay walkthrough opens as a modal wizard so the explanation
                can move stage by stage without pretending the backend is
                running.
              </p>
            </div>
          ) : null}

          <div className="button-row mt-4">
            <Link className="shell-inline-link" to="/">
              Return to overview
            </Link>
            <Link className="shell-inline-link" to="/pipeline">
              Open architecture page
            </Link>
          </div>

          {mode === "real" && requestError ? (
            <p className="text-body text-critical mt-4">{requestError}</p>
          ) : null}
        </div>
      </section>

      <section className="kpi-row section-gap">
        <KpiCard
          freshness={
            mode === "real" ? "TRUTHFUL BACKEND STATE" : "FRONTEND-ONLY REPLAY"
          }
          label="Run Mode"
          status={mode === "real" ? "Live" : "Simulated"}
          statusTone={modeData.tone}
          value={modeData.label.toUpperCase()}
        />
        <KpiCard
          freshness={buildStatusFreshness(mode, displayStatus)}
          label="Execution Status"
          status={mode === "real" ? "Current" : "Replay"}
          statusTone={
            mode === "demo" ? "warning" : getStatusTone(displayStatus?.status)
          }
          value={(displayStatus?.status || "idle").toUpperCase()}
        />
        <KpiCard
          freshness={`${executionSteps.length} TRACKED STAGES`}
          label="Stages Completed"
          status={`${completedSteps}/${executionSteps.length}`}
          statusTone={completedSteps > 0 ? "success" : "neutral"}
          value={completedSteps}
        />
        <KpiCard
          freshness="17-COUNTRY PANEL STORY"
          label="Truth Boundary"
          status={mode === "real" ? "Backend only" : "No backend writes"}
          statusTone={modeData.tone}
          value={mode === "real" ? "API ONLY" : "BROWSER ONLY"}
        />
      </section>

      <section className="trigger-grid section-gap">
        <div className="card">
          <div className="panel-header">
            <div>
              <p className="text-label">Execution sequence</p>
              <h2 className="text-headline mt-3">Shared pipeline stages</h2>
            </div>
            <StatusPill tone={modeData.tone}>{modeData.label}</StatusPill>
          </div>
          <div className="execution-step-list mt-4">
            {executionSteps.map((step, index) => {
              const isRunning = step.status === "running";

              return (
                <article
                  className={`execution-step-card execution-step-card--${getStatusTone(step.status)} ${isRunning ? "is-animating-border" : ""}`}
                  key={step.name}
                >
                  <div className="panel-header">
                    <div>
                      <p className="text-label">
                        Stage {String(index + 1).padStart(2, "0")}
                      </p>
                      <h3 className="text-title mt-3">{step.title}</h3>
                      <p className="execution-step-card__stage-name mt-3">
                        {step.name}
                      </p>
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
                    <FormattedStory text={getExecutionCopy(step)} />
                  </p>
                  <div className="execution-step-card__note mt-4">
                    <span className="text-label">What changes here</span>
                    <p className="text-body text-secondary mt-3">
                      <FormattedStory text={step.story} />
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <div className="terminal-panel">
          <p className="text-label">Execution feed</p>
          <pre className="terminal-panel__output text-metric text-secondary mt-3">
            {terminalOutput}
            {displayStatus?.status === "running" && (
              <span className="terminal-cursor" />
            )}
          </pre>
        </div>
      </section>

      <PipelineReplayModal
        isOpen={mode === "demo" && isReplayModalOpen}
        onClose={() => setIsReplayModalOpen(false)}
        replayVersion={demoReplayVersion}
      />
    </div>
  );
}
