import Flag from "react-world-flags";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { KpiCard } from "../components/KpiCard";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest } from "../api";
import {
  deriveCoverageBoard,
  deriveOverviewMetrics,
  deriveRegionalBreakdown,
  formatChange,
  formatMetricValue,
  formatTimestamp,
  getEmptyStateBody,
  getEmptyStateHeading,
  getOutlookTone,
  getOverviewNarrative,
  getSignalTone,
  getStepSummary,
  getStepTone,
} from "./globalOverviewModel";

// These positions are tuned to the shipped raster map rather than generic lat/lng.
const MARKER_POSITIONS = {
  za: { top: 63, left: 51.5 },
  ng: { top: 48, left: 42 },
  ke: { top: 52, left: 58 },
  eg: { top: 35, left: 52 },
  gh: { top: 48, left: 39 },
  et: { top: 46, left: 58 },
  ma: { top: 32, left: 38 },
  de: { top: 24, left: 48 },
  fr: { top: 27, left: 45 },
  br: { top: 60, left: 30 },
  in: { top: 40, left: 72 },
  cn: { top: 32, left: 78 },
  us: { top: 32, left: 20 },
  gb: { top: 23, left: 44 },
  jp: { top: 32, left: 86 },
};

const DETAIL_SIGNAL_CODES = [
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
];

async function fetchCountryBriefing(countryCode) {
  try {
    return await apiRequest(`/countries/${countryCode}`);
  } catch (error) {
    if (error.status === 404) {
      return null;
    }

    throw error;
  }
}

async function fetchOverviewData() {
  const [status, countries, indicators] = await Promise.all([
    apiRequest("/pipeline/status"),
    apiRequest("/countries"),
    apiRequest("/indicators"),
  ]);

  const briefings = (
    await Promise.all(
      countries.map((country) => fetchCountryBriefing(country.code)),
    )
  ).filter(Boolean);

  return { status, countries, indicators, briefings };
}

function getPipelineTone(status) {
  if (status === "complete") {
    return "success";
  }

  if (status === "running") {
    return "warning";
  }

  if (status === "failed") {
    return "critical";
  }

  return "neutral";
}

function getIndicatorValue(briefing, indicatorCode) {
  return briefing?.indicators?.find(
    (indicator) => indicator.indicator_code === indicatorCode,
  );
}

function getMarkerToneClass(briefing) {
  if (!briefing) {
    return "overview-map-marker__dot--pending";
  }

  return `overview-map-marker__dot--${getOutlookTone(briefing.outlook)}`;
}

function buildMarketMetrics(briefing) {
  return DETAIL_SIGNAL_CODES.map((indicatorCode) =>
    getIndicatorValue(briefing, indicatorCode),
  ).filter(Boolean);
}

function getMapPopoverTransform(position) {
  const anchorRight = position.left >= 72;
  const anchorLeft = position.left <= 28;
  const openBelow = position.top <= 28;
  const horizontalShift = anchorRight ? "-100%" : anchorLeft ? "0%" : "-50%";
  const horizontalOffset = anchorRight ? "-16px" : anchorLeft ? "16px" : "0px";
  const verticalShift = openBelow ? "0%" : "-100%";
  const verticalOffset = openBelow ? "16px" : "-16px";

  return `translate(${horizontalShift}, ${verticalShift}) translate(${horizontalOffset}, ${verticalOffset})`;
}

export function GlobalOverview() {
  const [overview, setOverview] = useState({
    status: null,
    countries: [],
    indicators: [],
    briefings: [],
  });
  const [viewState, setViewState] = useState("loading");
  const [requestError, setRequestError] = useState("");
  const [selectedMapCountry, setSelectedMapCountry] = useState(null);

  useEffect(() => {
    let isActive = true;

    async function loadOverview() {
      try {
        const nextOverview = await fetchOverviewData();
        if (!isActive) {
          return;
        }

        setOverview(nextOverview);
        setViewState("ready");
        setRequestError("");
      } catch (error) {
        if (!isActive) {
          return;
        }

        setViewState("error");
        setRequestError(error.message);
      }
    }

    loadOverview();

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (overview.status?.status !== "running") {
      return undefined;
    }

    let isActive = true;
    const intervalId = window.setInterval(async () => {
      try {
        const nextStatus = await apiRequest("/pipeline/status");
        if (!isActive) {
          return;
        }

        setOverview((currentOverview) => ({
          ...currentOverview,
          status: nextStatus,
        }));
        setRequestError("");

        if (nextStatus.status !== "running") {
          window.clearInterval(intervalId);
          const nextOverview = await fetchOverviewData();
          if (!isActive) {
            return;
          }

          setOverview(nextOverview);
        }
      } catch (error) {
        if (!isActive) {
          return;
        }

        setRequestError(error.message);
        window.clearInterval(intervalId);
      }
    }, 750);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [overview.status?.status]);

  const {
    anomalyCount,
    featuredCountry,
    latestRefresh,
    leadSignals,
    materialisedCountries,
    monitoredCountries,
    pipelineStatus,
    pipelineSteps,
  } = deriveOverviewMetrics(overview);

  const coverageBoard = deriveCoverageBoard(
    overview.countries,
    overview.briefings,
    selectedMapCountry || featuredCountry?.code || null,
  );
  const regionalBreakdown = deriveRegionalBreakdown(
    overview.countries,
    overview.briefings,
  );
  const highlightedMarketCode =
    selectedMapCountry ||
    coverageBoard.find((market) => market.isFeatured)?.code ||
    coverageBoard.find((market) => market.isMaterialised)?.code ||
    overview.countries[0]?.code ||
    null;
  const highlightedMarket =
    coverageBoard.find((market) => market.code === highlightedMarketCode) ||
    null;
  const highlightedBriefing = overview.briefings.find(
    (briefing) => briefing.code === highlightedMarketCode,
  );
  const highlightedMetrics = buildMarketMetrics(highlightedBriefing);
  const marketOpenHref = highlightedMarket?.href || "/trigger";
  const highlightedPosition = highlightedMarketCode
    ? MARKER_POSITIONS[highlightedMarketCode.toLowerCase()]
    : null;
  const highlightedStatusTone = highlightedBriefing?.outlook
    ? getOutlookTone(highlightedBriefing.outlook)
    : highlightedMarket?.tone || getOutlookTone(featuredCountry?.outlook);
  const headerNarrative =
    viewState === "ready"
      ? getOverviewNarrative(
          pipelineStatus,
          monitoredCountries,
          materialisedCountries,
        )
      : viewState === "error"
        ? "The overview could not load from the current slice. Open the trigger flow or retry once the API is reachable."
        : "Loading the current slice so the landing surface reflects live monitored coverage rather than placeholder content.";

  const sharedActions = (
    <div className="shell-command-row">
      <Link className="shell-command-link shell-command-link--accent" to="/trigger">
        {pipelineStatus === "running" ? "Monitor pipeline" : "Open pipeline"}
      </Link>
      <Link className="shell-command-link" to={marketOpenHref}>
        {selectedMapCountry ? "Open selected market" : "Open lead market"}
      </Link>
    </div>
  );

  function toggleMapFocus(countryCode) {
    setSelectedMapCountry((currentCountryCode) =>
      currentCountryCode === countryCode ? null : countryCode,
    );
  }

  if (viewState === "loading") {
    return (
      <div className="page page--overview container">
        <PageHeader
          description={headerNarrative}
          eyebrow="AI-GENERATED OVERVIEW"
          meta="Coverage board // current slice // live-compatible state"
          title="Global Overview"
        />

        <section className="section-gap">
          <div className="card state-panel">
            <p className="text-label">Loading current coverage</p>
            <div className="mt-3">
              <div className="skeleton skeleton-title" />
            </div>
            <div className="mt-4">
              <div className="skeleton skeleton-text overview-skeleton-line" />
              <div className="skeleton skeleton-text overview-skeleton-line overview-skeleton-line--short" />
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (viewState === "error") {
    return (
      <div className="page page--overview container">
        <PageHeader
          actions={sharedActions}
          description={headerNarrative}
          eyebrow="AI-GENERATED OVERVIEW"
          meta="Coverage board // current slice // live-compatible state"
          title="Global Overview"
        />

        <section className="section-gap">
          <div className="card state-panel">
            <p className="text-label">Overview unavailable</p>
            <h2 className="text-headline mt-3">The landing page could not hydrate</h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="page page--overview container">
      <PageHeader
        actions={sharedActions}
        description={headerNarrative}
        eyebrow="AI-GENERATED OVERVIEW"
        meta={`Latest refresh // ${latestRefresh ? formatTimestamp(latestRefresh) : "Pending"}`}
        title="Global Overview"
      />

      <section className="section-gap">
        <AIInsightPanel
          eyebrow="AI operating picture"
          footer={
            <div className="overview-hero-footer">
              <span className="text-label">
                Live briefings // {materialisedCountries}/{monitoredCountries}
              </span>
              <span className="text-label">
                Focus market // {highlightedMarket?.code || "Pending"}
              </span>
            </div>
          }
          status={pipelineStatus.toUpperCase()}
          title="Macro scanning surface"
          tone={getPipelineTone(pipelineStatus)}
        >
          <p className="text-body">
            {highlightedBriefing?.macro_synthesis ||
              featuredCountry?.macro_synthesis ||
              headerNarrative}
          </p>
          <div className="overview-hero-grid mt-4">
            <article className="card overview-hero-stat">
              <span className="text-label">Coverage</span>
              <span className="text-metric mt-3">
                {materialisedCountries}/{monitoredCountries}
              </span>
              <p className="text-body text-secondary mt-3">
                Live briefings confirmed in the active monitored set.
              </p>
            </article>
            <article className="card overview-hero-stat">
              <span className="text-label">Signal pressure</span>
              <span className="text-metric mt-3">{anomalyCount}</span>
              <p className="text-body text-secondary mt-3">
                Indicator anomalies flagged in the latest pool.
              </p>
            </article>
            <article className="card overview-hero-stat">
              <span className="text-label">Lead market</span>
              <span className="text-metric mt-3">
                {highlightedMarket?.code || "Pending"}
              </span>
              <p className="text-body text-secondary mt-3">
                {highlightedMarket
                  ? `${highlightedMarket.name} is the current focal market on this surface.`
                  : "A lead market will appear once a briefing is materialised."}
              </p>
            </article>
          </div>
        </AIInsightPanel>
      </section>

      {anomalyCount > 0 ? (
        <section className="section-gap">
          <div className="anomaly-banner">
            <div className="anomaly-banner__content">
              <span className="material-symbols-outlined anomaly-banner__icon">
                warning
              </span>
              <span>
                {anomalyCount} anomalies flagged across the current indicator set
              </span>
            </div>
            <Link className="anomaly-banner__action" to="/trigger">
              Review pipeline
            </Link>
          </div>
        </section>
      ) : null}

      <section className="kpi-row section-gap" aria-live="polite">
        <KpiCard
          freshness={
            overview.status?.started_at
              ? `UPDATED ${formatTimestamp(
                  overview.status.completed_at || overview.status.started_at,
                )}`
              : "AWAITING FIRST RUN"
          }
          label="Pipeline Status"
          status={pipelineStatus.toUpperCase()}
          statusTone={getStepTone(pipelineStatus)}
          value={pipelineStatus.toUpperCase()}
        />
        <KpiCard
          freshness={`${monitoredCountries} MONITORED IN CURRENT SCOPE`}
          label="Countries Materialised"
          status={`${materialisedCountries}/${monitoredCountries}`}
          statusTone={materialisedCountries > 0 ? "success" : "neutral"}
          value={materialisedCountries}
        />
        <KpiCard
          freshness={
            latestRefresh
              ? `REFRESH ${formatTimestamp(latestRefresh)}`
              : "NO MATERIALISED DATA"
          }
          label="Indicators Analysed"
          status={`${overview.indicators.length} ROWS`}
          statusTone={overview.indicators.length > 0 ? "success" : "neutral"}
          value={overview.indicators.length}
        />
        <KpiCard
          freshness={
            highlightedBriefing?.outlook
              ? `${highlightedBriefing.outlook.toUpperCase()} OUTLOOK`
              : "OUTLOOK PENDING"
          }
          label="Anomalies Flagged"
          status={anomalyCount > 0 ? "Escalated" : "Contained"}
          statusTone={anomalyCount > 0 ? "critical" : "success"}
          value={anomalyCount}
        />
      </section>

      <section className="overview-main-grid section-gap">
        <div className="card overview-panel">
          <div className="panel-header">
            <div>
              <p className="text-label">Global risk overview</p>
              <h2 className="text-headline mt-3">Monitored markets</h2>
            </div>
            <StatusPill tone="neutral">Current slice</StatusPill>
          </div>
          <div className="overview-map-surface mt-4">
            <img
              alt="World coverage map"
              className="overview-map-surface__image"
              src="/map-dark.png"
            />
            <div className="overview-map-surface__markers">
              {overview.countries.map((country) => {
                const position = MARKER_POSITIONS[country.code.toLowerCase()];
                const briefing = overview.briefings.find(
                  (item) => item.code === country.code,
                );

                if (!position) {
                  return null;
                }

                return (
                  <div
                    className="overview-map-marker"
                    key={country.code}
                    style={{ top: `${position.top}%`, left: `${position.left}%` }}
                  >
                    <button
                      className="map-marker-btn"
                      aria-label={`Focus ${country.name} market`}
                      aria-pressed={country.code === selectedMapCountry}
                      onClick={() => toggleMapFocus(country.code)}
                      title={`View ${country.name}`}
                      type="button"
                    >
                      <span
                        className={`overview-map-marker__dot${
                            country.code === highlightedMarketCode
                              ? " overview-map-marker__dot--selected"
                              : ""
                        }`}
                          aria-hidden="true"
                        >
                          <span
                            className={`overview-map-marker__dot-core ${getMarkerToneClass(
                              briefing,
                            )}`}
                          />
                        </span>
                      </button>
                    </div>
                  );
                })}
              </div>

              {selectedMapCountry && highlightedMarket && highlightedPosition ? (
                <div
                  aria-live="polite"
                  className="overview-map-popover"
                  style={{
                    top: `${highlightedPosition.top}%`,
                    left: `${highlightedPosition.left}%`,
                    transform: getMapPopoverTransform(highlightedPosition),
                  }}
                >
                  <div className="overview-map-popover__header">
                    <div>
                      <p className="text-label">Map focus</p>
                      <div className="overview-map-popover__market mt-3">
                        <span className="flag-frame flag-frame--sm">
                          <Flag code={highlightedMarket.code} height="100%" />
                        </span>
                        <div>
                          <h3 className="text-title">{highlightedMarket.name}</h3>
                          <p className="text-body text-secondary mt-3">
                            {highlightedMarket.region}
                          </p>
                        </div>
                      </div>
                    </div>
                    <StatusPill tone={highlightedStatusTone}>
                      {highlightedBriefing?.outlook
                        ? highlightedBriefing.outlook.toUpperCase()
                        : highlightedMarket.statusLabel}
                    </StatusPill>
                  </div>

                  <p className="text-body text-secondary mt-4">
                    {highlightedBriefing?.macro_synthesis || highlightedMarket.summary}
                  </p>

                  <div className="overview-map-popover__actions mt-4">
                    <Link className="shell-command-link shell-command-link--accent" to={marketOpenHref}>
                      Open country intelligence
                    </Link>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="overview-market-command-list mt-4" role="list">
              {coverageBoard.map((market) => (
                <button
                  className={`overview-market-command${
                    market.code === highlightedMarketCode
                      ? " overview-market-command--active"
                      : ""
                  }`}
                  key={market.code}
                  onClick={() => toggleMapFocus(market.code)}
                  type="button"
                >
                  <span className="overview-market-command__code">{market.code}</span>
                  <span className="overview-market-command__status">
                    {market.isMaterialised ? "Live" : "Pending"}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel-stack">
            <div className="card overview-panel">
              <div className="panel-header">
                <div>
                  <p className="text-label">Selected market</p>
                  <h2 className="text-headline mt-3">Market detail</h2>
                </div>
                <StatusPill tone={highlightedMarket?.tone || "neutral"}>
                  {highlightedMarket?.statusLabel || "Pending"}
                </StatusPill>
              </div>
              {highlightedMarket ? (
                <>
                  <div className="overview-context-market mt-4" aria-live="polite">
                    <span className="flag-frame flag-frame--md">
                      <Flag code={highlightedMarket.code} height="100%" />
                    </span>
                    <div>
                      <p className="text-label">
                        {selectedMapCountry ? "Focused market" : "Lead market"}
                      </p>
                      <h3 className="text-title mt-3">{highlightedMarket.name}</h3>
                      <p className="text-body text-secondary mt-3">
                        {highlightedMarket.region}
                      </p>
                    </div>
                    <StatusPill tone={highlightedStatusTone}>
                      {highlightedBriefing?.outlook
                        ? highlightedBriefing.outlook.toUpperCase()
                        : "PENDING"}
                    </StatusPill>
                  </div>

                  <p className="text-body text-secondary mt-4 overview-market-summary">
                    {highlightedBriefing?.macro_synthesis || highlightedMarket.summary}
                  </p>

                  {highlightedMetrics.length ? (
                    <div className="overview-market-metrics mt-4">
                      {highlightedMetrics.map((indicator) => (
                        <article className="overview-market-metric" key={indicator.indicator_code}>
                          <span className="text-label">{indicator.indicator_name}</span>
                          <span className="text-metric mt-3">
                            {formatMetricValue(
                              indicator.indicator_code,
                              indicator.latest_value,
                            )}
                          </span>
                          <span
                            className={`text-label mt-3 ${getSignalTone(
                              indicator.indicator_code,
                              indicator.percent_change,
                            )}`}
                          >
                            {formatChange(indicator.percent_change)}
                          </span>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="text-body text-secondary mt-4">
                      No live signal pack is materialised for this market yet.
                    </p>
                  )}

                  <div className="shell-command-row mt-4">
                    <Link
                      className="shell-command-link shell-command-link--accent"
                      to={marketOpenHref}
                    >
                      Open market
                    </Link>
                    {selectedMapCountry ? (
                      <button
                        className="shell-command-link"
                        onClick={() => setSelectedMapCountry(null)}
                        type="button"
                      >
                        Reset focus
                      </button>
                    ) : null}
                  </div>
                </>
              ) : null}
            </div>

            <div className="card overview-panel">
              <div className="panel-header">
                <div>
                  <p className="text-label">Current slice</p>
                  <h2 className="text-headline mt-3">Pipeline state</h2>
                </div>
                <StatusPill tone={getPipelineTone(pipelineStatus)}>
                  {pipelineStatus.toUpperCase()}
                </StatusPill>
              </div>
              <div className="overview-step-list mt-4">
                {pipelineSteps.map((step) => (
                  <article className="overview-step-card" key={step.name}>
                    <div className="panel-header">
                      <span className="text-label">{step.name}</span>
                      <StatusPill tone={getStepTone(step.status)}>
                        {step.status.toUpperCase()}
                      </StatusPill>
                    </div>
                    <p className="text-body text-secondary mt-3">
                      {getStepSummary(step)}
                    </p>
                  </article>
                ))}
              </div>
            </div>

            <div className="card overview-panel">
              <div className="panel-header">
                <div>
                  <p className="text-label">Regional breakdown</p>
                  <h2 className="text-headline mt-3">Coverage by region</h2>
                </div>
                <StatusPill tone="neutral">Live coverage</StatusPill>
              </div>
              <div className="overview-region-list mt-4">
                {regionalBreakdown.map((region) => (
                  <article className="overview-region-card" key={region.region}>
                    <div className="panel-header">
                      <div>
                        <h3 className="text-title">{region.region}</h3>
                        <p className="text-body text-secondary mt-3">
                          {region.summary}
                        </p>
                      </div>
                      <StatusPill tone={region.tone}>
                        {region.materialisedCount > 0 ? "Live" : "Pending"}
                      </StatusPill>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="section-gap">
          <div className="panel-header">
            <div>
              <p className="text-label">Market depth</p>
              <h2 className="text-headline mt-3">Signals and posture</h2>
            </div>
            <StatusPill tone={highlightedStatusTone}>
              {highlightedBriefing?.outlook
                ? highlightedBriefing.outlook.toUpperCase()
                : featuredCountry?.outlook
                  ? featuredCountry.outlook.toUpperCase()
                  : "PENDING"}
            </StatusPill>
          </div>
          <div className="overview-depth-grid mt-4">
            {coverageBoard.slice(0, 2).map((market, index) => {
              const briefing = overview.briefings.find(
                (item) => item.code === market.code,
              );
              const leadIndicator = briefing
                ? getIndicatorValue(briefing, "NY.GDP.MKTP.KD.ZG") ||
                  getIndicatorValue(briefing, "FP.CPI.TOTL.ZG")
                : null;

              return (
                <Link className="market-card" key={market.code} to={market.href}>
                  <div className="market-card__header">
                    <div>
                      <p className="market-card__node-id">
                        NODE-{String(index + 1).padStart(3, "0")}
                      </p>
                      <div className="market-card__title-row mt-3">
                        <span className="flag-frame flag-frame--sm market-card__flag">
                          <Flag code={market.code} height="100%" />
                        </span>
                        <h3 className="market-card__country">{market.name}</h3>
                      </div>
                    </div>
                    <StatusPill tone={market.tone}>{market.statusLabel}</StatusPill>
                  </div>
                  <p className="market-card__insight mt-4">
                    {briefing?.macro_synthesis
                      ? briefing.macro_synthesis
                      : getEmptyStateBody(pipelineStatus)}
                  </p>
                  <div className="market-card__meta mt-4">
                    <span>{market.region}</span>
                    <span>
                      {leadIndicator
                        ? `${formatMetricValue(
                            leadIndicator.indicator_code,
                            leadIndicator.latest_value,
                          )} // ${formatChange(leadIndicator.percent_change)}`
                        : "Awaiting briefing"}
                    </span>
                  </div>
                </Link>
              );
            })}

            {leadSignals[0] ? (
              <article className="card overview-depth-card">
                <p className="text-label">Lead signal pack</p>
                <div className="overview-signal-list mt-4">
                  {leadSignals.slice(0, 2).map((indicator) => (
                    <div className="overview-signal-card" key={indicator.indicator_code}>
                      <div className="panel-header">
                        <h3 className="text-title">{indicator.indicator_name}</h3>
                        {indicator.is_anomaly ? (
                          <StatusPill tone="critical">Anomaly</StatusPill>
                        ) : null}
                      </div>
                      <div className="indicator-meta mt-3">
                        <span className="text-metric">
                          {formatMetricValue(
                            indicator.indicator_code,
                            indicator.latest_value,
                          )}
                        </span>
                        <span
                          className={`text-label ${getSignalTone(
                            indicator.indicator_code,
                            indicator.percent_change,
                          )}`}
                        >
                          {formatChange(indicator.percent_change)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ) : (
            <article className="card overview-depth-card">
              <p className="text-label">Lead signal pack</p>
              <h3 className="text-headline mt-3">{getEmptyStateHeading(pipelineStatus)}</h3>
              <p className="text-body text-secondary mt-4">
                {getEmptyStateBody(pipelineStatus)}
              </p>
            </article>
          )}
        </div>
      </section>
    </div>
  );
}
export default GlobalOverview;
