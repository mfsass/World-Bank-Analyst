export const TARGET_COUNTRY = "ZA";

export const SIGNAL_PRIORITY = [
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "GC.DOD.TOTL.GD.ZS",
  "BN.CAB.XOKA.GD.ZS",
];

export const FALLBACK_STEPS = [
  { name: "fetch", status: "pending" },
  { name: "analyse", status: "pending" },
  { name: "synthesise", status: "pending" },
  { name: "store", status: "pending" },
];

const HIGHER_IS_BETTER = new Set([
  "NY.GDP.MKTP.CD",
  "NY.GDP.MKTP.KD.ZG",
  "BN.CAB.XOKA.GD.ZS",
]);

const LOWER_IS_BETTER = new Set([
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
  "GC.DOD.TOTL.GD.ZS",
]);

const OUTLOOK_TONE_MAP = {
  bearish: "critical",
  bullish: "success",
  cautious: "warning",
  neutral: "neutral",
};

function getRegionalTone(outlookCounts) {
  if (outlookCounts.bearish > 0) {
    return "critical";
  }

  if (outlookCounts.cautious > 0) {
    return "warning";
  }

  if (outlookCounts.bullish > 0) {
    return "success";
  }

  return "neutral";
}

export function formatTimestamp(value) {
  if (!value) {
    return "NOT AVAILABLE";
  }

  return new Date(value).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMetricValue(indicatorCode, value) {
  if (value == null) {
    return "n/a";
  }

  if (indicatorCode === "NY.GDP.MKTP.CD") {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }

  return `${value.toFixed(1)}%`;
}

export function formatChange(value) {
  if (value == null) {
    return "NO PRIOR YEAR";
  }

  const direction = value >= 0 ? "UP" : "DOWN";
  return `${direction} ${Math.abs(value).toFixed(2)}% YOY`;
}

export function getLatestRefresh(indicators, pipelineStatus) {
  const latestIndicatorUpdate = indicators.reduce((latest, indicator) => {
    if (!indicator.updated_at) {
      return latest;
    }
    if (!latest) {
      return indicator.updated_at;
    }
    return new Date(indicator.updated_at) > new Date(latest)
      ? indicator.updated_at
      : latest;
  }, null);

  return latestIndicatorUpdate || pipelineStatus?.completed_at || null;
}

export function getOverviewNarrative(
  status,
  monitoredCountries,
  materialisedCountries,
) {
  const monitoredCountryLabel =
    monitoredCountries === 1 ? "country" : "countries";

  if (status === "running") {
    return "Polling the active pipeline run while the current coverage slice materialises. Counts below reflect confirmed country briefings until the run completes.";
  }

  if (status === "complete") {
    return `The landing page reflects the current materialised local coverage universe. ${materialisedCountries} of ${monitoredCountries} monitored countries now have a live briefing.`;
  }

  if (status === "failed") {
    return "The latest local run failed. Any previously materialised briefing remains visible below, while the status feed preserves the failure state for follow-up.";
  }

  return `The landing page is wired to the live local/API slice. ${monitoredCountries} ${monitoredCountryLabel} ${monitoredCountries === 1 ? "is" : "are"} currently configured, with ${materialisedCountries} confirmed briefing${materialisedCountries === 1 ? "" : "s"} until the pipeline runs.`;
}

export function getEmptyStateHeading(status) {
  if (status === "running") {
    return "Materialising Coverage";
  }

  if (status === "failed") {
    return "Latest Run Failed";
  }

  return "No Live Briefing Yet";
}

export function getEmptyStateBody(status) {
  if (status === "running") {
    return "The current slice is fetching, analysing, synthesising, and storing monitored market data in-process. This page will refresh once the status feed leaves the running state.";
  }

  if (status === "failed") {
    return "The last trigger ended in failure before the market briefing could be refreshed. Review the step status, rerun the pipeline, and reopen the market view once the slice completes.";
  }

  return "Run the pipeline to materialise the next market briefing and populate anomaly, outlook, and macro synthesis fields on this page.";
}

export function getLeadSignals(featuredCountry, indicators) {
  const featuredCode = featuredCountry?.code || indicators[0]?.country_code;
  const sourceIndicators =
    featuredCountry?.indicators ||
    indicators.filter((indicator) => indicator.country_code === featuredCode);

  const byCode = new Map(
    sourceIndicators.map((indicator) => [indicator.indicator_code, indicator]),
  );

  return SIGNAL_PRIORITY.map((indicatorCode) =>
    byCode.get(indicatorCode),
  ).filter(Boolean);
}

export function getStepTone(status) {
  if (status === "complete") {
    return "complete";
  }

  if (status === "failed") {
    return "failed";
  }

  if (status === "running") {
    return "running";
  }

  return "idle";
}

export function getStepSummary(step) {
  if (step.duration_ms) {
    return `${step.duration_ms}ms elapsed in the local process.`;
  }

  if (step.status === "running") {
    return "Currently executing inside the API process.";
  }

  if (step.status === "failed") {
    return "Execution failed before the slice could complete.";
  }

  if (step.status === "complete") {
    return "Step completed for the latest local slice.";
  }

  return "Awaiting pipeline execution.";
}

export function getOutlookTone(outlook) {
  if (!outlook) {
    return "neutral";
  }

  return OUTLOOK_TONE_MAP[outlook.toLowerCase()] || "neutral";
}

export function getSignalTone(indicatorCode, percentChange) {
  if (percentChange == null) {
    return "text-secondary";
  }

  if (HIGHER_IS_BETTER.has(indicatorCode)) {
    return percentChange >= 0 ? "text-success" : "text-critical";
  }

  if (LOWER_IS_BETTER.has(indicatorCode)) {
    return percentChange >= 0 ? "text-critical" : "text-success";
  }

  return percentChange >= 0 ? "text-success" : "text-critical";
}

export function deriveOverviewMetrics(overview) {
  const pipelineStatus = overview.status?.status || "idle";
  const monitoredCountries = overview.countries.length;
  const materialisedCountryCodes = [
    ...new Set(overview.briefings.map((briefing) => briefing.code)),
  ];
  const materialisedCountries = materialisedCountryCodes.length;
  const anomalyCount = overview.indicators.filter(
    (indicator) => indicator.is_anomaly,
  ).length;
  const latestRefresh = getLatestRefresh(overview.indicators, overview.status);
  const featuredCountry = overview.briefings[0] || null;
  const leadSignals = getLeadSignals(featuredCountry, overview.indicators);
  const pipelineSteps = overview.status?.steps?.length
    ? overview.status.steps
    : FALLBACK_STEPS;

  return {
    pipelineStatus,
    monitoredCountries,
    materialisedCountries,
    anomalyCount,
    latestRefresh,
    featuredCountry,
    leadSignals,
    pipelineSteps,
  };
}

export function deriveRegionalBreakdown(countries = [], briefings = []) {
  const briefingByCode = new Map(
    briefings.map((briefing) => [briefing.code, briefing]),
  );
  const regionMap = new Map();

  countries.forEach((country) => {
    const regionName = country.region || "Unassigned";
    const region = regionMap.get(regionName) || {
      region: regionName,
      monitoredCount: 0,
      materialisedCount: 0,
      outlookCounts: {
        bearish: 0,
        bullish: 0,
        cautious: 0,
        neutral: 0,
      },
    };

    region.monitoredCount += 1;

    const briefing = briefingByCode.get(country.code);
    if (briefing) {
      region.materialisedCount += 1;
      const outlookKey = briefing.outlook?.toLowerCase() || "neutral";
      region.outlookCounts[outlookKey] =
        (region.outlookCounts[outlookKey] || 0) + 1;
    }

    regionMap.set(regionName, region);
  });

  return [...regionMap.values()]
    .map((region) => ({
      ...region,
      tone: getRegionalTone(region.outlookCounts),
      summary: `${region.materialisedCount}/${region.monitoredCount} live briefings`,
    }))
    .sort((left, right) => {
      if (right.materialisedCount !== left.materialisedCount) {
        return right.materialisedCount - left.materialisedCount;
      }

      return right.monitoredCount - left.monitoredCount;
    });
}

export function deriveCoverageBoard(
  countries = [],
  briefings = [],
  featuredCode = null,
) {
  const briefingByCode = new Map(
    briefings.map((briefing) => [briefing.code, briefing]),
  );

  return countries.map((country) => {
    const briefing = briefingByCode.get(country.code);
    const isMaterialised = Boolean(briefing);
    const isFeatured = country.code === featuredCode;

    return {
      code: country.code,
      href: `/country/${country.code.toLowerCase()}`,
      isFeatured,
      isMaterialised,
      name: country.name,
      region: country.region || "Unassigned",
      statusLabel: isMaterialised ? "Live" : "Pending",
      summary: isMaterialised
        ? `${country.name} briefing materialised in the current slice.`
        : `${country.name} is monitored but not yet materialised.`,
      tone: isMaterialised ? getOutlookTone(briefing.outlook) : "neutral",
    };
  });
}
