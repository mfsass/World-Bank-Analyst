/**
 * Country Intelligence — per-country deep dive.
 *
 * Indicator charts, AI analysis narrative, risk flags.
 * Each country gets its own URL (/country/:id) so it's shareable.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiRequest } from "../api";

const FEATURED_INDICATORS = [
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
  "GC.DOD.TOTL.GD.ZS",
];

function formatMetric(indicatorCode, value) {
  if (value == null) {
    return "n/a";
  }
  if (indicatorCode === "NY.GDP.MKTP.CD") {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }
  return `${value.toFixed(1)}%`;
}

function formatChange(value) {
  if (value == null) {
    return "NO PRIOR YEAR";
  }
  const direction = value >= 0 ? "+" : "-";
  return `${direction}${Math.abs(value).toFixed(2)}% YOY`;
}

export function CountryIntelligence() {
  const { id } = useParams();
  const countryCode = (id || "za").toUpperCase();
  const [country, setCountry] = useState(null);
  const [viewState, setViewState] = useState("loading");
  const [requestError, setRequestError] = useState("");

  useEffect(() => {
    let isActive = true;

    async function loadCountry() {
      setViewState("loading");
      try {
        const payload = await apiRequest(`/countries/${countryCode}`);
        if (isActive) {
          setCountry(payload);
          setViewState("ready");
          setRequestError("");
        }
      } catch (error) {
        if (!isActive) {
          return;
        }
        if (error.status === 404) {
          setViewState("not-found");
          setRequestError(
            "Run the local pipeline to materialise the ZA country briefing.",
          );
          return;
        }
        setViewState("error");
        setRequestError(error.message);
      }
    }

    loadCountry();

    return () => {
      isActive = false;
    };
  }, [countryCode]);

  const featuredIndicators = FEATURED_INDICATORS.map((indicatorCode) =>
    country?.indicators?.find(
      (indicator) => indicator.indicator_code === indicatorCode,
    ),
  ).filter(Boolean);

  if (viewState === "loading") {
    return (
      <main className="container">
        <header className="section-gap">
          <p className="text-label">COUNTRY INTELLIGENCE</p>
          <h1 className="text-display">{countryCode}</h1>
        </header>

        <section className="section-gap">
          <div className="card">
            <p className="text-body text-secondary">
              Loading live country intelligence from the local slice.
            </p>
          </div>
        </section>
      </main>
    );
  }

  if (viewState !== "ready") {
    return (
      <main className="container">
        <header className="section-gap">
          <p className="text-label">COUNTRY INTELLIGENCE</p>
          <h1 className="text-display">{countryCode}</h1>
        </header>

        <section className="section-gap">
          <div className="card">
            <h2 className="text-headline">Briefing Unavailable</h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
            <div className="button-row mt-4">
              <Link className="btn-primary" to="/trigger">
                OPEN PIPELINE TRIGGER
              </Link>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="container">
      <header className="section-gap">
        <p className="text-label">COUNTRY INTELLIGENCE</p>
        <h1 className="text-display">{country.name}</h1>
        <p className="text-body text-secondary mt-4">
          {country.code}
          {' // '}
          {country.region}
          {' // '}
          {country.income_level}
        </p>
      </header>

      <section className="kpi-row section-gap">
        {featuredIndicators.map((indicator) => (
          <div className="kpi-card" key={indicator.indicator_code}>
            <span className="kpi-card__label">{indicator.indicator_name}</span>
            <span className="kpi-card__value">
              {formatMetric(indicator.indicator_code, indicator.latest_value)}
            </span>
            <span
              className={`kpi-card__trend ${indicator.percent_change >= 0 ? "kpi-card__trend--up" : "kpi-card__trend--down"}`}
            >
              {formatChange(indicator.percent_change)}
            </span>
            <span className="kpi-card__freshness">
              YEAR {indicator.data_year}
            </span>
          </div>
        ))}
      </section>

      <section className="section-gap">
        <div className="detail-grid">
          <div className="card">
            <p className="text-label">INDICATOR ANALYSIS</p>
            <h2 className="text-headline mt-4">Risk-Weighted Signals</h2>
            <div className="indicator-list mt-4">
              {country.indicators.map((indicator) => (
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
                      {formatMetric(
                        indicator.indicator_code,
                        indicator.latest_value,
                      )}
                    </span>
                    <span
                      className={`text-label ${indicator.percent_change >= 0 ? "text-success" : "text-critical"}`}
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

          <div className="panel-stack">
            <div className="ai-insight">
              <h2 className="text-headline">
                <span className="ai-insight__icon">✦ </span>
                Macro Synthesis
              </h2>
              <p className="text-body mt-4">{country.macro_synthesis}</p>
            </div>

            <div className="card">
              <p className="text-label">OUTLOOK</p>
              <div className="panel-header mt-4">
                <h2 className="text-headline">Forward View</h2>
                <span
                  className={`status-pill status-pill--${country.outlook === "bearish" ? "failed" : "running"}`}
                >
                  {country.outlook.toUpperCase()}
                </span>
              </div>
              <ul className="risk-list mt-4">
                {country.risk_flags.map((riskFlag) => (
                  <li className="text-body" key={riskFlag}>
                    {riskFlag}
                  </li>
                ))}
              </ul>
            </div>

            <div className="card">
              <p className="text-label">RESPONSIBLE AI</p>
              <p className="text-body text-secondary mt-4">
                AI-generated content may contain inaccuracies. Verify before
                acting.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
