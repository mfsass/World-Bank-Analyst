import PropTypes from "prop-types";

import {
  getActivePipelineStageActivity,
  getPipelineStageActivities,
} from "../pipelineStageModel";

export function PipelineStepSimulation({
  activityLabel,
  isRunning,
  stepName,
  tick,
}) {
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

PipelineStepSimulation.propTypes = {
  activityLabel: PropTypes.string.isRequired,
  isRunning: PropTypes.bool.isRequired,
  stepName: PropTypes.string.isRequired,
  tick: PropTypes.number.isRequired,
};
