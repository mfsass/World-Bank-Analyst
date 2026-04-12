import PropTypes from "prop-types";
import { useEffect, useState } from "react";

import { StatusPill } from "./StatusPill";
import { PipelineStepSimulation } from "./PipelineStepSimulation";
import {
  PIPELINE_STAGE_MODEL,
  getActivePipelineStageActivity,
} from "../pipelineStageModel";

const REPLAY_ADVANCE_INTERVAL_MS = 1400;
const REPLAY_ACTIVITY_INTERVAL_MS = 900;

function getStatusTone(status) {
  if (status === "complete") {
    return "success";
  }

  if (status === "running") {
    return "running";
  }

  return "neutral";
}

function buildReplaySteps(activeIndex) {
  return PIPELINE_STAGE_MODEL.map((stage, index) => ({
    ...stage,
    status:
      index < activeIndex ? "complete" : index === activeIndex ? "running" : "pending",
  }));
}

function buildReplayTerminalLines(replaySteps, activeActivity, autoplay) {
  const lines = [
    "> MODE: DEMO WALKTHROUGH (SIMULATED)",
    "> SOURCE: FRONTEND-ONLY MODAL REPLAY",
    `> CONTROL: ${autoplay ? "AUTO-PLAY" : "MANUAL"}`,
  ];

  replaySteps.forEach((step) => {
    lines.push(`> ${step.name.toUpperCase().padEnd(10, " ")} ${step.status.toUpperCase()}`);
  });

  lines.push(
    `> ACTIVE OPERATION: ${activeActivity.verb.toUpperCase()} ${activeActivity.label.toUpperCase()}`,
  );
  lines.push("> COUNTRY PAGE REMAINS LOCKED UNTIL A REAL RUN COMPLETES");

  return lines;
}

export function PipelineReplayModal({ isOpen, onClose, replayVersion }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [autoplay, setAutoplay] = useState(true);
  const [tick, setTick] = useState(0);

  const replaySteps = buildReplaySteps(activeIndex);
  const activeStage = replaySteps[activeIndex];
  const activeActivity = getActivePipelineStageActivity(activeStage.name, tick);
  const replayAnnouncement = `Demo walkthrough stage ${activeIndex + 1} of ${
    replaySteps.length
  }: ${activeStage.title}.`;

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    setActiveIndex(0);
    setAutoplay(true);
    setTick(0);

    return undefined;
  }, [isOpen, replayVersion]);

  useEffect(() => {
    if (!isOpen || !autoplay) {
      return undefined;
    }

    if (activeIndex >= PIPELINE_STAGE_MODEL.length - 1) {
      setAutoplay(false);
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setActiveIndex((currentIndex) =>
        currentIndex >= PIPELINE_STAGE_MODEL.length - 1
          ? currentIndex
          : currentIndex + 1,
      );
    }, REPLAY_ADVANCE_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [activeIndex, autoplay, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setTick((currentTick) => currentTick + 1);
    }, REPLAY_ACTIVITY_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="pipeline-replay-modal__backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        aria-labelledby="pipeline-replay-title"
        aria-modal="true"
        className="pipeline-replay-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <p aria-live="polite" className="sr-only">
          {replayAnnouncement}
        </p>

        <div className="panel-header">
          <div>
            <p className="text-label">Frontend-only simulation</p>
            <h2 className="text-headline mt-3" id="pipeline-replay-title">
              Replay walkthrough
            </h2>
            <p className="text-body text-secondary mt-4">
              The modal replays the same stage model the live page uses, but it
              never touches backend state.
            </p>
          </div>
          <div className="pipeline-replay-modal__status">
            <StatusPill tone="warning">SIMULATED</StatusPill>
            <StatusPill tone={autoplay ? "warning" : "neutral"}>
              {autoplay ? "AUTO-PLAY" : "MANUAL"}
            </StatusPill>
          </div>
        </div>

        <div className="pipeline-replay-modal__controls mt-4">
          <button
            className="btn-ghost"
            onClick={() => setAutoplay((currentValue) => !currentValue)}
            type="button"
          >
            {autoplay ? "Pause auto-play" : "Resume auto-play"}
          </button>
          <button
            className="btn-ghost"
            onClick={() =>
              setActiveIndex((currentIndex) =>
                currentIndex >= PIPELINE_STAGE_MODEL.length - 1
                  ? currentIndex
                  : currentIndex + 1,
              )
            }
            type="button"
          >
            Next stage
          </button>
        </div>

        <div className="pipeline-replay-modal__grid mt-4">
          <div className="pipeline-replay-modal__rail">
            {replaySteps.map((step, index) => (
              <button
                className={`pipeline-replay-stage pipeline-replay-stage--${step.status} ${
                  index === activeIndex ? "pipeline-replay-stage--active" : ""
                }`}
                key={step.name}
                onClick={() => {
                  setActiveIndex(index);
                  setAutoplay(false);
                }}
                type="button"
              >
                <div className="pipeline-replay-stage__header">
                  <span className="text-label">
                    Stage {String(index + 1).padStart(2, "0")}
                  </span>
                  <StatusPill tone={getStatusTone(step.status)}>
                    {step.status.toUpperCase()}
                  </StatusPill>
                </div>
                <span className="pipeline-replay-stage__title mt-3">
                  {step.title}
                </span>
                <span className="pipeline-replay-stage__name mt-2">
                  {step.name}
                </span>
              </button>
            ))}
          </div>

          <div className="pipeline-replay-modal__detail">
            <div className="pipeline-replay-modal__detail-card">
              <div className="panel-header">
                <div>
                  <p className="text-label">Replay activity</p>
                  <h3 className="text-headline mt-3">{activeStage.title}</h3>
                </div>
                <StatusPill tone={autoplay ? "warning" : "neutral"}>
                  {autoplay ? "AUTO-PLAY" : "MANUAL"}
                </StatusPill>
              </div>
              <p className="text-body text-secondary mt-4">{activeStage.story}</p>
              <div className="execution-step-card__note mt-4">
                <span className="text-label">Output</span>
                <p className="text-body text-secondary mt-3">
                  {activeStage.outcome}
                </p>
              </div>
              <div className="execution-step-card__note mt-4">
                <span className="text-label">Why this stage takes time</span>
                <p className="text-body text-secondary mt-3">
                  {activeStage.latencyNote}
                </p>
              </div>
              <PipelineStepSimulation
                activityLabel="Replay activity"
                isRunning={true}
                stepName={activeStage.name}
                tick={tick}
              />
            </div>

            <div className="terminal-panel pipeline-replay-modal__terminal">
              <p className="text-label">Replay feed</p>
              <pre className="terminal-panel__output text-metric text-secondary mt-3">
                {buildReplayTerminalLines(replaySteps, activeActivity, autoplay).join(
                  "\n",
                )}
                <span className="terminal-cursor" />
              </pre>
            </div>
          </div>
        </div>

        <div className="pipeline-replay-modal__footer mt-4">
          <p className="text-body text-secondary">
            This popup is simulated. It never writes fake status back to the API.
          </p>
          <button
            className="btn-ghost pipeline-replay-modal__close"
            onClick={onClose}
            type="button"
          >
            Close walkthrough
          </button>
        </div>
      </div>
    </div>
  );
}

PipelineReplayModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  replayVersion: PropTypes.number.isRequired,
};
