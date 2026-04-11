/**
 * Global Overview — the landing page.
 *
 * Summary KPIs, live slice status, and the latest materialised briefing.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiRequest } from "../api";
import {
  deriveOverviewMetrics,
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
  TARGET_COUNTRY,
} from "./globalOverviewModel";

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

  // Coverage comes from materialised country briefings, not raw indicator rows.
  const briefings = (
    await Promise.all(
      countries.map((country) => fetchCountryBriefing(country.code)),
    )
  ).filter(Boolean);

  return { status, countries, indicators, briefings };
}

export function GlobalOverview() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState({
    status: null,
    countries: [],
    indicators: [],
    briefings: [],
  });
  const [viewState, setViewState] = useState("loading");
  const [requestError, setRequestError] = useState("");

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
    // Mirror the trigger page while the in-process local pipeline is still running.
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
  const monitoredCountryLabel =
    monitoredCountries === 1 ? "country" : "countries";
  const headerNarrative =
    viewState === "ready"
      ? getOverviewNarrative(
          pipelineStatus,
          monitoredCountries,
          materialisedCountries,
        )
      : viewState === "error"
        ? "The overview could not load from the current local/API slice. Open the trigger flow or retry once the API is reachable."
        : "Loading the current local/API slice so the landing page reflects live monitored coverage instead of placeholder content.";

  return (
    <main className="container">
      <header className="section-gap">
        <h1 className="text-display">Global Overview</h1>
        <p className="text-label">
          WORLD ANALYST // CURRENT MONITORED COVERAGE
        </p>
        <p className="text-body text-secondary mt-4">{headerNarrative}</p>
        <div className="button-row mt-4">
          <Link className="btn-primary" to="/trigger">
            {pipelineStatus === "running"
              ? "MONITOR PIPELINE"
              : "OPEN PIPELINE TRIGGER"}
          </Link>
          <button
            className="btn-ghost"
            type="button"
            onClick={() => navigate(`/country/${TARGET_COUNTRY.toLowerCase()}`)}
            disabled={!featuredCountry}
          >
            OPEN ZA BRIEFING
          </button>
        </div>
      </header>

      {viewState === "loading" ? (
        <section className="section-gap">
          <div className="card">
            <h2 className="text-headline">Loading Current Coverage</h2>
            <p className="text-body text-secondary mt-4">
              Pulling pipeline status, monitored countries, and any materialised
              country briefing from the live local slice.
            </p>
          </div>
        </section>
      ) : null}

      {viewState === "error" ? (
        <section className="section-gap">
          <div className="card">
            <h2 className="text-headline">Overview Unavailable</h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
          </div>
        </section>
      ) : null}

      {viewState === "ready" ? (
        <>
          <section className="kpi-row section-gap" aria-live="polite">
            <div className="kpi-card">
              <span className="kpi-card__label">Pipeline Status</span>
              <span className="kpi-card__value">{pipelineStatus.toUpperCase()}</span>
              <span className="kpi-card__freshness">
                {overview.status?.started_at
                  ? `UPDATED ${formatTimestamp(
                      overview.status.completed_at || overview.status.started_at,
                    )}`
                  : "AWAITING FIRST RUN"}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-card__label">Countries Materialised</span>
              <span className="kpi-card__value">{materialisedCountries}</span>
              <span className="kpi-card__freshness">
                {monitoredCountries} MONITORED IN LOCAL SLICE
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-card__label">Indicators Analysed</span>
              <span className="kpi-card__value">{overview.indicators.length}</span>
              <span className="kpi-card__freshness">
                {latestRefresh
                  ? `REFRESH ${formatTimestamp(latestRefresh)}`
                  : "NO MATERIALISED DATA"}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-card__label">Anomalies Flagged</span>
              <span className="kpi-card__value">{anomalyCount}</span>
              <span className="kpi-card__freshness">
                {featuredCountry?.outlook
                  ? `${featuredCountry.outlook.toUpperCase()} OUTLOOK`
                  : "OUTLOOK PENDING"}
              </span>
            </div>
          </section>

          <section className="section-gap">
            <div className="detail-grid">
              {featuredCountry ? (
                <div className="ai-insight">
                  <p className="text-label">LIVE COUNTRY BRIEFING</p>
                  <div className="panel-header mt-4">
                    <h2 className="text-headline">
                      <span className="ai-insight__icon">✦ </span>
                      South Africa Macro Snapshot
                    </h2>
                    <span
                      className={`status-pill status-pill--${getOutlookTone(
                        featuredCountry.outlook,
                      )}`}
                    >
                      {featuredCountry.outlook.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-body mt-4">
                    {featuredCountry.macro_synthesis}
                  </p>

                  <div className="indicator-list mt-4">
                    {leadSignals.map((indicator) => (
                      <article
                        className="indicator-card"
                        key={indicator.indicator_code}
                      >
                        <div className="panel-header">
                          <h3 className="text-title">{indicator.indicator_name}</h3>
                          {indicator.is_anomaly ? (
                            <span className="status-pill status-pill--failed">
                              ANOMALY
                            </span>
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
                          <span className="text-label">
                            YEAR {indicator.data_year}
                          </span>
                        </div>
                        <p className="text-body text-secondary mt-4">
                          {indicator.ai_analysis}
                        </p>
                      </article>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="card">
                  <p className="text-label">MATERIALISATION STATUS</p>
                  <div className="panel-header mt-4">
                    <h2 className="text-headline">
                      {getEmptyStateHeading(pipelineStatus)}
                    </h2>
                    <span className={`status-pill status-pill--${pipelineStatus}`}>
                      {pipelineStatus.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-body text-secondary mt-4">
                    {getEmptyStateBody(pipelineStatus)}
                  </p>
                  <ul className="risk-list mt-4">
                    <li className="text-body">
                      Current monitored coverage: {monitoredCountries} configured
                      {" "}
                      {monitoredCountryLabel} in the local slice.
                    </li>
                    <li className="text-body">
                      Materialised briefings: {materialisedCountries}. Indicator
                      insights: {overview.indicators.length}.
                    </li>
                    <li className="text-body">
                      Use the pipeline trigger to populate macro synthesis,
                      outlook, and country detail for {TARGET_COUNTRY}.
                    </li>
                  </ul>
                </div>
              )}

              <div className="panel-stack">
                <div className="card">
                  <p className="text-label">OPERATING CONTEXT</p>
                  <div className="panel-header mt-4">
                    <h2 className="text-headline">Pipeline State</h2>
                    <span className={`status-pill status-pill--${pipelineStatus}`}>
                      {pipelineStatus.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-body text-secondary mt-4">
                    {materialisedCountries} of {monitoredCountries} monitored
                    countries currently have a materialised briefing in the
                    local slice.
                  </p>
                  {overview.status?.error ? (
                    <p className="text-body text-critical mt-4">
                      {overview.status.error}
                    </p>
                  ) : null}
                  {requestError ? (
                    <p className="text-body text-critical mt-4">
                      {requestError}
                    </p>
                  ) : null}
                  <ul className="risk-list mt-4">
                    {pipelineSteps.map((step) => (
                      <li key={step.name}>
                        <div className="panel-header">
                          <span className="text-label">{step.name}</span>
                          <span
                            className={`status-pill status-pill--${getStepTone(
                              step.status,
                            )}`}
                          >
                            {step.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-body text-secondary mt-3">
                          {getStepSummary(step)}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="card">
                  <p className="text-label">RISK FLAGS</p>
                  <div className="panel-header mt-4">
                    <h2 className="text-headline">Finance Lens</h2>
                    <span
                      className={`status-pill status-pill--${getOutlookTone(
                        featuredCountry?.outlook,
                      )}`}
                    >
                      {featuredCountry?.outlook
                        ? featuredCountry.outlook.toUpperCase()
                        : "PENDING"}
                    </span>
                  </div>
                  {featuredCountry ? (
                    <ul className="risk-list mt-4">
                      {featuredCountry.risk_flags.map((riskFlag) => (
                        <li className="text-body" key={riskFlag}>
                          {riskFlag}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-body text-secondary mt-4">
                      Run the local ZA slice to materialise the macro synthesis,
                      outlook, and risk flags on this landing page.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </section>
        </>
      ) : null}

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
