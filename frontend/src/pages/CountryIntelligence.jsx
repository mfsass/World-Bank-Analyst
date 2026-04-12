import Flag from "react-world-flags";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { MarketSwitcher } from "../components/MarketSwitcher";
import { PageHeader } from "../components/PageHeader";
import { StatusPill } from "../components/StatusPill";
import { apiRequest } from "../api";
import {
  formatSourceDateRange,
  getLatestDataYear,
  getOutlookTone,
  getSignalTone,
} from "./globalOverviewModel";

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

function buildTitle(code, label, isPlaceholder = false) {
  return (
    <span className="page-title-with-flag">
      <span
        className={`flag-frame flag-frame--lg page-title-with-flag__flag${
          isPlaceholder ? " flag-frame--placeholder" : ""
        }`}
      >
        {isPlaceholder ? null : <Flag code={code} height="100%" />}
      </span>
      <span>{label}</span>
    </span>
  );
}

function LoadingSwitcher() {
  return (
    <section className="market-switcher market-switcher--placeholder">
      <p className="text-label">Switch market</p>
      <div className="market-switcher__row mt-3">
        {Array.from({ length: 8 }, (_, index) => (
          <span
            className="market-switcher__pill market-switcher__pill--placeholder"
            key={index}
          >
            --
          </span>
        ))}
      </div>
    </section>
  );
}

function CountryIntelligence() {
  const { id } = useParams();
  const countryCode = (id || "br").toUpperCase();
  const [country, setCountry] = useState(null);
  const [countries, setCountries] = useState([]);
  const [viewState, setViewState] = useState("loading");
  const [requestError, setRequestError] = useState("");

  useEffect(() => {
    let isActive = true;

    async function loadCountry() {
      setViewState("loading");
      try {
        const [countryResult, countriesResult] = await Promise.allSettled([
          apiRequest(`/countries/${countryCode}`),
          apiRequest("/countries"),
        ]);

        if (countriesResult.status === "fulfilled" && isActive) {
          setCountries(countriesResult.value);
        }

        if (countryResult.status === "rejected") {
          throw countryResult.reason;
        }

        if (isActive) {
          setCountry(countryResult.value);
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
            "This market is tracked, but its briefing is not yet available.",
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
  const sourceWindowLabel = formatSourceDateRange(country?.source_date_range);
  const latestDataYear = getLatestDataYear(country?.indicators ?? []);
  const latestDataYearLabel = latestDataYear
    ? String(latestDataYear)
    : "Pending";

  const sharedActions = (
    <div className="button-row">
      <Link className="btn-primary" to="/trigger">
        Open pipeline
      </Link>
      <Link className="btn-ghost" to="/">
        Return to overview
      </Link>
    </div>
  );

  const marketSwitcher = countries.length ? (
    <MarketSwitcher
      activeCode={viewState === "ready" ? country.code : countryCode}
      getHref={(market) => `/country/${market.code.toLowerCase()}`}
      items={countries}
      label="Switch market"
    />
  ) : (
    <LoadingSwitcher />
  );

  if (viewState === "loading") {
    return (
      <div className="page page--country container">
        <nav className="breadcrumb-row breadcrumb-row--loading">
          <Link className="shell-inline-link" to="/">
            Global Overview
          </Link>
          <span className="breadcrumb-row__separator">/</span>
          <span className="text-label">{countryCode}</span>
        </nav>

        {marketSwitcher}

        <PageHeader
          actions={sharedActions}
          description="Loading the latest country briefing and monitored market list from the active slice."
          eyebrow="COUNTRY INTELLIGENCE"
          meta={`Market code · ${countryCode}`}
          title={buildTitle(countryCode, countryCode, true)}
        />

        <section className="country-identity section-gap">
          <div className="card state-panel">
            <p className="text-label">Loading country posture</p>
            <div className="mt-3">
              <div className="skeleton skeleton-title" />
            </div>
            <div className="mt-4">
              <div className="skeleton skeleton-text overview-skeleton-line" />
            </div>
          </div>
          <div className="card state-panel">
            <p className="text-label">Loading briefing depth</p>
            <div className="mt-3">
              <div className="skeleton skeleton-title overview-skeleton-line--short" />
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (viewState !== "ready") {
    return (
      <div className="page page--country container">
        <nav className="breadcrumb-row">
          <Link className="shell-inline-link" to="/">
            Global Overview
          </Link>
          <span className="breadcrumb-row__separator">/</span>
          <span className="text-label">{countryCode}</span>
        </nav>

        {marketSwitcher}

        <PageHeader
          actions={sharedActions}
          description={requestError}
          eyebrow="COUNTRY INTELLIGENCE"
          meta={`Market code · ${countryCode}`}
          title={buildTitle(countryCode, countryCode, true)}
        />

        <section className="section-gap">
          <div className="card state-panel">
            <h2 className="text-headline">Briefing unavailable</h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="page page--country container">
      <nav className="breadcrumb-row">
        <Link className="shell-inline-link" to="/">
          Global Overview
        </Link>
        <span className="breadcrumb-row__separator">/</span>
        <span className="text-label">{country.name}</span>
      </nav>

      {marketSwitcher}

      <PageHeader
        actions={sharedActions}
        description={`Current signals, macro synthesis, and forward-looking risk for ${country.name}. The source window below reflects the underlying World Bank data rather than the pipeline rerun timestamp.`}
        eyebrow="COUNTRY INTELLIGENCE"
        meta={`${country.code} · ${country.region} · ${country.income_level}`}
        title={buildTitle(country.code, country.name)}
      />

      <section className="section-gap">
        <AIInsightPanel
          eyebrow="Country synthesis"
          footer={
            <div className="country-briefing-meta">
              <span className="text-label">
                Outlook // {country.outlook.toUpperCase()}
              </span>
              <span className="text-label">
                Risk flags // {country.risk_flags.length}
              </span>
              <span className="text-label">
                Source window // {sourceWindowLabel}
              </span>
              <span className="text-label">
                Latest data year // {latestDataYearLabel}
              </span>
            </div>
          }
          status={country.outlook.toUpperCase()}
          title="Country briefing"
          tone={getOutlookTone(country.outlook)}
        >
          <p className="text-body">{country.macro_synthesis}</p>
        </AIInsightPanel>
      </section>

      <section className="country-identity section-gap">
        <div className="card country-identity__primary">
          <p className="text-label">Current posture</p>
          <div className="panel-header mt-4">
            <div>
              <h2 className="text-headline">{country.name}</h2>
              <p className="text-body text-secondary mt-3">
                {country.region} · {country.income_level}
              </p>
            </div>
            <StatusPill tone={getOutlookTone(country.outlook)}>
              {country.outlook.toUpperCase()}
            </StatusPill>
          </div>
        </div>
        <div className="card country-identity__secondary">
          <p className="text-label">Briefing depth</p>
          <span className="text-metric mt-3">{country.indicators.length}</span>
          <p className="text-body text-secondary mt-3">
            World Bank data window {sourceWindowLabel}; latest year
            {latestDataYearLabel} across this briefing.
          </p>
        </div>
      </section>

      <section className="kpi-row section-gap">
        {featuredIndicators.map((indicator) => (
          <article className="kpi-card" key={indicator.indicator_code}>
            <span className="kpi-card__label">{indicator.indicator_name}</span>
            <span className="kpi-card__value">
              {formatMetric(indicator.indicator_code, indicator.latest_value)}
            </span>
            <span
              className={`kpi-card__trend kpi-card__trend--${
                indicator.percent_change >= 0 ? "up" : "down"
              }`}
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined kpi-trend-icon"
              >
                {indicator.percent_change >= 0
                  ? "trending_up"
                  : "trending_down"}
              </span>{" "}
              {formatChange(indicator.percent_change)}
            </span>
          </article>
        ))}
      </section>

      <section className="section-gap">
        <div className="country-detail-grid">
          <div className="card country-detail-panel">
            <div className="panel-header">
              <div>
                <p className="text-label">Analyst signal pack</p>
                <h2 className="text-headline mt-3">Current risk signals</h2>
              </div>
            </div>
            <p className="text-body text-secondary country-detail-panel__summary">
              Indicator-level narratives, year stamps, and direction-of-travel
              signals from the current country slice.
            </p>
            <div className="indicator-list">
              {country.indicators.map((indicator) => (
                <article
                  className="indicator-card"
                  key={indicator.indicator_code}
                >
                  <div className="panel-header">
                    <h3 className="text-title">{indicator.indicator_name}</h3>
                    {indicator.is_anomaly ? (
                      <StatusPill tone="critical">Anomaly</StatusPill>
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

          <div className="card country-detail-panel">
            <div className="panel-header">
              <div>
                <p className="text-label">Analyst outlook</p>
                <h2 className="text-headline mt-3">Forward view</h2>
              </div>
              <StatusPill tone={getOutlookTone(country.outlook)}>
                {country.outlook.toUpperCase()}
              </StatusPill>
            </div>
            <p className="text-body text-secondary country-detail-panel__summary">
              Forward-looking risk flags derived from the current country
              briefing.
            </p>
            <ul className="risk-list">
              {country.risk_flags.map((riskFlag) => (
                <li className="text-body" key={riskFlag}>
                  {riskFlag}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

export { CountryIntelligence };
export default CountryIntelligence;
