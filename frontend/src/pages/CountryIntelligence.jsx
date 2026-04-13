import Flag from "react-world-flags";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { AIInsightPanel } from "../components/AIInsightPanel";
import { CountryTimeline } from "../components/CountryTimeline";
import { MarketSwitcher } from "../components/MarketSwitcher";
import { StatusPill } from "../components/StatusPill";
import { apiRequest } from "../api";
import {
  formatChange,
  getAnomalyLabel,
  getDesiredDirectionLabel,
  getDisplayChangeBasis,
  getDisplayChangeValue,
  getSignalDisposition,
  getSignalTone,
} from "../lib/indicatorSignals.js";
import {
  getCachedCountry,
  getCountriesList,
  setCachedCountry,
  setCountriesList,
} from "../lib/countryDetailCache";
import {
  formatSourceDateRange,
  getLatestDataYear,
  getOutlookTone,
} from "./globalOverviewModel";

/* Indicators surfaced in the KPI row — the 4 most decision-relevant metrics */
const FEATURED_INDICATORS = [
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
  "GC.DOD.TOTL.GD.ZS",
];

function formatRegimeLabel(regimeLabel) {
  if (!regimeLabel) {
    return "";
  }

  const humanLabel = regimeLabel.replace(/_/g, " ");
  return humanLabel.charAt(0).toUpperCase() + humanLabel.slice(1);
}

function getRegimeTone(regimeLabel) {
  if (regimeLabel === "recovery" || regimeLabel === "expansion") {
    return "success";
  }

  if (regimeLabel === "overheating") {
    return "accent";
  }

  if (regimeLabel === "contraction" || regimeLabel === "stagnation") {
    return "critical";
  }

  return "neutral";
}

function formatMetric(indicatorCode, value) {
  if (value == null) {
    return "n/a";
  }
  if (indicatorCode === "NY.GDP.MKTP.CD") {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }
  return `${value.toFixed(1)}%`;
}

function LoadingSwitcher() {
  return (
    <div className="country-header__switcher" aria-hidden="true">
      {Array.from({ length: 17 }, (_, index) => (
        <span
          className="skeleton market-switcher__pill--skeleton"
          key={index}
        />
      ))}
    </div>
  );
}

function CountryIntelligence() {
  const { id } = useParams();
  const countryCode = (id || "br").toUpperCase();
  const [country, setCountry] = useState(null);
  // Init from session cache so the market switcher is instant on navigations
  // after the first page that fetched /countries (Landing or Overview).
  const [countries, setCountries] = useState(() => getCountriesList() ?? []);
  const [viewState, setViewState] = useState("loading");
  const [requestError, setRequestError] = useState("");

  useEffect(() => {
    let isActive = true;

    async function loadCountry() {
      // Cache hit — render the country page immediately without a loading
      // state. The market switcher list is still fetched in the background
      // since it is not part of the country detail payload.
      const cached = getCachedCountry(countryCode);
      if (cached) {
        if (isActive) {
          setCountry(cached);
          setViewState("ready");
          setRequestError("");
        }
        apiRequest("/countries")
          .then((result) => {
            if (isActive) setCountries(result);
            setCountriesList(result);
          })
          .catch(() => {});
        return;
      }

      setViewState("loading");
      try {
        const [countryResult, countriesResult] = await Promise.allSettled([
          apiRequest(`/countries/${countryCode}`),
          apiRequest("/countries"),
        ]);

        if (countriesResult.status === "fulfilled" && isActive) {
          setCountries(countriesResult.value);
          setCountriesList(countriesResult.value);
        }

        if (countryResult.status === "rejected") {
          throw countryResult.reason;
        }

        if (isActive) {
          setCountry(countryResult.value);
          // Populate the shared cache so navigating back to this country
          // later in the same session is also instant.
          setCachedCountry(countryCode, countryResult.value);
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
  const outlookLabel = country?.outlook?.toUpperCase() ?? "UNKNOWN";

  /* ── Market switcher ─────────────────────────────────────────────── */
  const marketSwitcherPills = countries.length ? (
    <MarketSwitcher
      activeCode={viewState === "ready" ? country.code : countryCode}
      getHref={(market) => `/country/${market.code.toLowerCase()}`}
      items={countries}
      label="Switch market"
    />
  ) : (
    <LoadingSwitcher />
  );

  /* ── Loading state ───────────────────────────────────────────────── */
  if (viewState === "loading") {
    return (
      <div className="page page--country container">
        <header className="country-header section-gap">
          <div className="country-header__identity">
            <span className="flag-frame flag-frame--lg flag-frame--placeholder" />
            <div>
              <h1 className="text-headline">{countryCode}</h1>
              <p className="text-label mt-3">Loading market intelligence…</p>
            </div>
          </div>
        </header>

        <section className="section-gap">
          <div className="card state-panel" style={{ gridColumn: "1 / -1" }}>
            <p className="text-label">Loading country posture</p>
            <div className="mt-3">
              <div className="skeleton skeleton-title" />
            </div>
            <div className="mt-4">
              <div className="skeleton skeleton-text overview-skeleton-line" />
            </div>
          </div>
        </section>
      </div>
    );
  }

  /* ── Error / Not Found state ─────────────────────────────────────── */
  if (viewState !== "ready") {
    return (
      <div className="page page--country container">
        <header className="country-header section-gap">
          <div className="country-header__identity">
            <span className="flag-frame flag-frame--lg flag-frame--placeholder" />
            <div>
              <h1 className="text-headline">{countryCode}</h1>
              <p className="text-label mt-3">{requestError}</p>
            </div>
          </div>
        </header>

        <section className="section-gap">
          <div className="card state-panel">
            <h2 className="text-headline">Briefing unavailable</h2>
            <p className="text-body text-secondary mt-4">{requestError}</p>
          </div>
        </section>
      </div>
    );
  }

  /* ── Ready state ─────────────────────────────────────────────────── */
  return (
    <div className="page page--country container">
      {/* ── IDENTITY STRIP ──────────────────────────────────────────── */}
        <header className="country-header">
          <div className="country-header__identity">
            <span className="flag-frame flag-frame--lg">
              <Flag code={country.code} height="100%" />
            </span>
            <div>
              <div className="country-header__title-row">
                <h1 className="text-headline">{country.name}</h1>
                {country.regime_label ? (
                  <StatusPill tone={getRegimeTone(country.regime_label)}>
                    {formatRegimeLabel(country.regime_label)}
                  </StatusPill>
                ) : null}
              </div>
              <p className="text-label mt-3">
                {country.code} · {country.region} · {country.income_level}
              </p>
            </div>
          </div>
        <div className="country-header__market-strip">
          {marketSwitcherPills}
        </div>
      </header>

      {/* ── § EXECUTIVE POSITION ───────────────────────────────────────
           The single most important section: AI synthesis + risk flags.
           Positioned immediately after the identity strip so a CFO sees
           the macro assessment without scrolling.                        */}
      <section className="section-gap">
        <AIInsightPanel
          eyebrow="Executive position"
          footer={
            <div className="country-briefing-meta">
              <span className="text-label">
                Outlook // {outlookLabel}
              </span>
              <span className="text-label">
                Source window // {sourceWindowLabel}
              </span>
              <span className="text-label">
                Latest data year // {latestDataYearLabel}
              </span>
            </div>
          }
          status={outlookLabel}
          title="Macro Intelligence"
          tone={getOutlookTone(country.outlook)}
        >
          <p className="text-body">{country.macro_synthesis}</p>
          {country.risk_flags?.length > 0 ? (
            <div className="country-risk-flags mt-4">
              <h3 className="text-label">Risk flags</h3>
              <ul className="country-risk-flags__list mt-3">
                {country.risk_flags.map((riskFlag) => (
                  <li className="country-risk-flags__chip" key={riskFlag}>
                    {riskFlag}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </AIInsightPanel>
      </section>

      {/* ── § KEY METRICS ──────────────────────────────────────────────
           4 featured KPI cards that validate the AI's assessment.       */}
      <section className="kpi-row section-gap">
        {featuredIndicators.map((indicator) => {
          const changeValue = getDisplayChangeValue(indicator);
          const changeBasis = getDisplayChangeBasis(indicator);
          const signalTone = getSignalTone(indicator.indicator_code, changeValue);

          return (
            <article className="kpi-card" key={indicator.indicator_code}>
              <span className="kpi-card__label">{indicator.indicator_name}</span>
              <span className="kpi-card__value">
                {formatMetric(indicator.indicator_code, indicator.latest_value)}
              </span>
              <span className={`kpi-card__trend ${signalTone}`}>
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined kpi-trend-icon"
                >
                  {changeValue >= 0 ? "trending_up" : "trending_down"}
                </span>{" "}
                {formatChange(changeValue, changeBasis, {
                  includePeriod: true,
                  nullLabel: "NO PRIOR YEAR",
                })}
              </span>
            </article>
          );
        })}
      </section>

      {/* ── § INDICATOR DEEP DIVES ─────────────────────────────────────
           Each indicator rendered as a unified card: chart left,
           narrative + KPI right. Chart and narrative paired together
           instead of split into separate sections.                      */}
      <section className="section-gap">
        <div className="panel-header">
          <div>
            <p className="text-label">Indicator analysis</p>
            <h2 className="text-headline mt-3">Current Risk Signals</h2>
          </div>
          <StatusPill tone={getOutlookTone(country.outlook)}>
            {outlookLabel}
          </StatusPill>
        </div>

        <div className="indicator-deep-dives mt-4">
          {country.indicators.map((indicator) => {
            const hasTimeSeries = indicator.time_series?.length > 1;
            const changeValue = getDisplayChangeValue(indicator);
            const changeBasis = getDisplayChangeBasis(indicator);
            const signalTone = getSignalTone(indicator.indicator_code, changeValue);
            const signalDisposition = getSignalDisposition(
              indicator.indicator_code,
              changeValue,
            );
            return (
              <article
                className="indicator-dive-card"
                key={indicator.indicator_code}
              >
                {/* Chart side — full historical line chart when time-series data exists. */}
                {hasTimeSeries && (
                  <div className="indicator-dive-card__chart">
                    <CountryTimeline
                      indicators={[indicator]}
                      compact
                    />
                  </div>
                )}

                {/* Narrative side — KPI value, change, AI analysis */}
                <div className="indicator-dive-card__narrative">
                  <div className="panel-header">
                    <h3 className="text-title">{indicator.indicator_name}</h3>
                    {indicator.is_anomaly ? (
                      <StatusPill tone="critical">
                        {getAnomalyLabel(indicator.anomaly_basis)}
                      </StatusPill>
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
                      className={`text-label ${signalTone}`}
                    >
                      {formatChange(changeValue, changeBasis)}
                    </span>
                    <span className="text-label">
                      YEAR {indicator.data_year}
                    </span>
                  </div>
                  <div className="indicator-signal-context mt-3">
                    <span className="text-label text-secondary">
                      {getDesiredDirectionLabel(indicator.indicator_code)}
                    </span>
                    <span className={`text-label ${signalTone}`}>
                      Latest move {signalDisposition}
                    </span>
                  </div>
                  <p className="text-body text-secondary mt-4">
                    {indicator.ai_analysis}
                  </p>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export { CountryIntelligence };
export default CountryIntelligence;
