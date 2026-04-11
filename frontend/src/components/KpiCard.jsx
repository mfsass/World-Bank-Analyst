import PropTypes from "prop-types";

import { StatusPill } from "./StatusPill";

export function KpiCard({
  label,
  value,
  status,
  statusTone,
  freshness,
  accentTone,
}) {
  const accentClass = accentTone ? ` kpi-card--${accentTone}` : "";

  return (
    <div className={`kpi-card${accentClass}`}>
      <div className="kpi-card__header">
        <span className="kpi-card__label">{label}</span>
        {status ? <StatusPill tone={statusTone}>{status}</StatusPill> : null}
      </div>
      <span className="kpi-card__value">{value}</span>
      {freshness ? (
        <span className="kpi-card__freshness">{freshness}</span>
      ) : null}
    </div>
  );
}

KpiCard.propTypes = {
  label: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  value: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
    PropTypes.node,
  ]).isRequired,
  status: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  statusTone: PropTypes.string,
  freshness: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  accentTone: PropTypes.string,
};
