import PropTypes from "prop-types";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  formatChange,
  getAnomalyLabel,
  getDesiredDirectionLabel,
  getDisplayChangeBasis,
  getDisplayChangeValue,
  getSignalDisposition,
  getSignalTone,
} from "../lib/indicatorSignals.js";

function getToneColor(indicatorCode, indicatorPoint = {}) {
  const tone = getSignalTone(indicatorCode, getDisplayChangeValue(indicatorPoint));

  if (tone === "text-critical") {
    return "var(--color-critical)";
  }

  if (tone === "text-success") {
    return "var(--color-success)";
  }

  return "var(--color-text-secondary)";
}

function formatTimelineValue(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "n/a";
  }

  const absoluteValue = Math.abs(value);
  if (absoluteValue >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (absoluteValue >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (absoluteValue >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  if (absoluteValue >= 100) {
    return value.toFixed(0);
  }
  return value.toFixed(1);
}

function TimelineDot({ cx, cy, indicatorCode, payload, latestYear }) {
  if (typeof cx !== "number" || typeof cy !== "number") {
    return null;
  }

  const isLatest = payload?.year === latestYear;
  const isAnomaly = Boolean(payload?.is_anomaly);
  if (!isLatest && !isAnomaly) {
    return null;
  }

  return (
    <circle
      cx={cx}
      cy={cy}
      r={isLatest ? 4 : 3}
      fill={isLatest ? getToneColor(indicatorCode, payload) : "var(--surface-card)"}
      stroke={isAnomaly ? "var(--color-critical)" : "var(--surface-card)"}
      strokeWidth={isAnomaly ? 2 : 1}
    />
  );
}

TimelineDot.propTypes = {
  cx: PropTypes.number,
  cy: PropTypes.number,
  indicatorCode: PropTypes.string.isRequired,
  latestYear: PropTypes.number,
  payload: PropTypes.shape({
    change_basis: PropTypes.string,
    change_value: PropTypes.number,
    is_anomaly: PropTypes.bool,
    percent_change: PropTypes.number,
    year: PropTypes.number,
  }),
};

function TimelineTooltip({ active, indicatorCode, payload }) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0]?.payload;
  if (!point) {
    return null;
  }

  const changeLabel = formatChange(
    getDisplayChangeValue(point),
    getDisplayChangeBasis(point),
    {
      includePeriod: true,
      nullLabel: "No prior year",
    },
  );
  const directionSummary = `${getDesiredDirectionLabel(
    indicatorCode,
  )} / Latest move ${getSignalDisposition(
    indicatorCode,
    getDisplayChangeValue(point),
  )}`;

  return (
    <div className="timeline-tooltip">
      <span className="timeline-tooltip__year">{point.year}</span>
      <span className="timeline-tooltip__value">
        {formatTimelineValue(point.value)}
      </span>
      <span
        className={`timeline-tooltip__change ${getSignalTone(
          indicatorCode,
          getDisplayChangeValue(point),
        )}`}
      >
        {changeLabel}
      </span>
      <span className="timeline-tooltip__note">{directionSummary}</span>
      {point.is_anomaly ? (
        <span className="timeline-tooltip__anomaly">
          {getAnomalyLabel(point.anomaly_basis)}
        </span>
      ) : null}
    </div>
  );
}

TimelineTooltip.propTypes = {
  active: PropTypes.bool,
  indicatorCode: PropTypes.string.isRequired,
  payload: PropTypes.arrayOf(
    PropTypes.shape({
      payload: PropTypes.shape({
        anomaly_basis: PropTypes.string,
        change_basis: PropTypes.string,
        change_value: PropTypes.number,
        is_anomaly: PropTypes.bool,
        value: PropTypes.number,
        year: PropTypes.number,
      }),
    }),
  ),
};

function renderTimelineCard(indicator, compact) {
  const series = indicator.time_series ?? [];
  const years = series.map((point) => point.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const anomalyCount = series.filter((point) => point.is_anomaly).length;

  return (
    <div
      className={compact ? "country-timeline__compact" : "country-timeline__chart"}
      key={indicator.indicator_code}
    >
      <div className="country-timeline__chart-header">
        <div className="country-timeline__chart-context">
          {!compact ? (
            <span className="text-label">{indicator.indicator_name}</span>
          ) : null}
          <span className="text-label text-secondary">{minYear}-{maxYear}</span>
          <span className="text-label text-secondary">
            {getDesiredDirectionLabel(indicator.indicator_code)}
          </span>
        </div>
        <span
          className={`country-timeline__chart-note${
            anomalyCount ? " text-warning" : ""
          }`}
        >
          {anomalyCount
            ? `${anomalyCount} anomaly year${anomalyCount === 1 ? "" : "s"}`
            : "No anomaly years"}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={compact ? 176 : 220}>
        <LineChart
          data={series}
          margin={
            compact
              ? { top: 8, right: 8, bottom: 0, left: 0 }
              : { top: 8, right: 12, bottom: 0, left: 0 }
          }
        >
          <CartesianGrid
            vertical={false}
            stroke="var(--color-border)"
            strokeDasharray="2 2"
          />
          <XAxis
            axisLine={{ stroke: "var(--color-border)" }}
            dataKey="year"
            minTickGap={compact ? 20 : 16}
            tick={{
              fill: "var(--color-text-secondary)",
              fontFamily: "var(--font-mono)",
              fontSize: compact ? 10 : 11,
            }}
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            tick={{
              fill: "var(--color-text-secondary)",
              fontFamily: "var(--font-mono)",
              fontSize: compact ? 10 : 11,
            }}
            tickFormatter={formatTimelineValue}
            tickLine={false}
            width={compact ? 40 : 56}
          />
          <Tooltip
            content={<TimelineTooltip indicatorCode={indicator.indicator_code} />}
          />
          <Line
            activeDot={{
              fill: "var(--color-text-primary)",
              r: 5,
              stroke: "var(--surface-card)",
              strokeWidth: 2,
            }}
            connectNulls
            dataKey="value"
            dot={
              <TimelineDot
                indicatorCode={indicator.indicator_code}
                latestYear={maxYear}
              />
            }
            stroke="var(--color-text-primary)"
            strokeWidth={2}
            type="monotone"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CountryTimeline({ indicators, compact = false }) {
  const timelineIndicators = indicators.filter(
    (indicator) => indicator.time_series && indicator.time_series.length > 1,
  );

  if (!timelineIndicators.length) {
    return null;
  }

  if (compact) {
    return timelineIndicators.map((indicator) => renderTimelineCard(indicator, true));
  }

  return (
    <section className="country-timeline section-gap">
      <div className="panel-header">
        <div>
          <p className="text-label">Historical context</p>
          <h2 className="text-headline mt-3">Indicator timelines</h2>
        </div>
      </div>
      <div className="country-timeline__grid mt-4">
        {timelineIndicators.map((indicator) => renderTimelineCard(indicator, false))}
      </div>
    </section>
  );
}

CountryTimeline.propTypes = {
  compact: PropTypes.bool,
  indicators: PropTypes.arrayOf(
    PropTypes.shape({
      indicator_code: PropTypes.string.isRequired,
      indicator_name: PropTypes.string.isRequired,
      time_series: PropTypes.arrayOf(
        PropTypes.shape({
          anomaly_basis: PropTypes.string,
          change_basis: PropTypes.string,
          change_value: PropTypes.number,
          is_anomaly: PropTypes.bool,
          percent_change: PropTypes.number,
          value: PropTypes.number,
          year: PropTypes.number.isRequired,
        }),
      ),
    }),
  ).isRequired,
};

export default CountryTimeline;
