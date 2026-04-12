import PropTypes from "prop-types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

/* Custom dot renderer: anomaly years get a red dot, the latest point gets accent. */
function TimelineDot({ cx, cy, payload, latestYear }) {
  const isLatest = payload?.year === latestYear;

  if (isLatest) {
    return <circle cx={cx} cy={cy} r={4} fill="#FF4500" stroke="none" />;
  }
  if (payload?.is_anomaly) {
    return <circle cx={cx} cy={cy} r={3} fill="#EF4444" stroke="none" />;
  }
  return null;
}

TimelineDot.propTypes = {
  cx: PropTypes.number,
  cy: PropTypes.number,
  payload: PropTypes.shape({
    is_anomaly: PropTypes.bool,
    year: PropTypes.number,
  }),
  latestYear: PropTypes.number,
};

/* Custom tooltip matching the design system Level 3 surface. */
function TimelineTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  const changeLabel =
    point.percent_change != null
      ? `${point.percent_change >= 0 ? "+" : ""}${point.percent_change.toFixed(2)}% YoY`
      : "No prior year";
  return (
    <div className="timeline-tooltip">
      <span className="timeline-tooltip__year">{point.year}</span>
      <span className="timeline-tooltip__value">{point.value?.toFixed(2)}</span>
      <span className="timeline-tooltip__change">{changeLabel}</span>
    </div>
  );
}

TimelineTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.arrayOf(
    PropTypes.shape({
      payload: PropTypes.shape({
        year: PropTypes.number,
        value: PropTypes.number,
        percent_change: PropTypes.number,
      }),
    }),
  ),
};

export function CountryTimeline({ indicators }) {
  /* Filter to indicators that have time_series data */
  const timelineIndicators = indicators.filter(
    (ind) => ind.time_series && ind.time_series.length > 1,
  );

  if (!timelineIndicators.length) return null;

  return (
    <section className="country-timeline section-gap">
      <div className="panel-header">
        <div>
          <p className="text-label">Historical context</p>
          <h2 className="text-headline mt-3">Indicator timelines</h2>
        </div>
      </div>
      <div className="country-timeline__grid mt-4">
        {timelineIndicators.map((indicator) => {
          const series = indicator.time_series;
          const years = series.map((p) => p.year);
          const minYear = Math.min(...years);
          const maxYear = Math.max(...years);
          const mean =
            series.reduce((sum, p) => sum + (p.value ?? 0), 0) / series.length;
          const latestYear = maxYear;

          return (
            <div className="country-timeline__chart" key={indicator.indicator_code}>
              <div className="country-timeline__chart-header">
                <span className="text-label">{indicator.indicator_name}</span>
                <span className="text-label text-secondary">
                  {minYear}–{maxYear}
                </span>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart
                  data={series}
                  margin={{ top: 8, right: 32, bottom: 4, left: 8 }}
                >
                  <XAxis
                    dataKey="year"
                    tick={{ fill: "#737373", fontFamily: "'Commit Mono', monospace", fontSize: 11 }}
                    axisLine={{ stroke: "#262626" }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#737373", fontFamily: "'Commit Mono', monospace", fontSize: 11 }}
                    axisLine={{ stroke: "#262626" }}
                    tickLine={false}
                    width={48}
                  />
                  <Tooltip content={<TimelineTooltip />} />
                  <ReferenceLine
                    y={mean}
                    stroke="#737373"
                    strokeDasharray="4 4"
                    label={{
                      value: "MEAN",
                      fill: "#737373",
                      fontSize: 10,
                      fontFamily: "'Commit Mono', monospace",
                      position: "right",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#F5F5F5"
                    strokeWidth={1.5}
                    dot={<TimelineDot latestYear={latestYear} />}
                    activeDot={{ r: 4, fill: "#FF4500" }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          );
        })}
      </div>
    </section>
  );
}

CountryTimeline.propTypes = {
  indicators: PropTypes.arrayOf(
    PropTypes.shape({
      indicator_code: PropTypes.string.isRequired,
      indicator_name: PropTypes.string.isRequired,
      time_series: PropTypes.arrayOf(
        PropTypes.shape({
          year: PropTypes.number.isRequired,
          value: PropTypes.number,
          percent_change: PropTypes.number,
          is_anomaly: PropTypes.bool,
        }),
      ),
    }),
  ).isRequired,
};

export default CountryTimeline;
