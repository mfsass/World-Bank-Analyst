import {
  getDisplayChangeBasis,
  getDisplayChangeValue,
  getSignalPolarity,
  isAdverseMove,
} from "../lib/indicatorSignals.js";

export { formatChange, getSignalTone } from "../lib/indicatorSignals.js";

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

export function formatSourceDateRange(value) {
  if (!value) {
    return "Pending";
  }

  const [startYear, endYear] = String(value).split(":");
  if (!startYear && !endYear) {
    return "Pending";
  }

  if (!endYear || startYear === endYear) {
    return startYear || endYear;
  }

  return `${startYear}-${endYear}`;
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

export function getLatestDataYear(records = []) {
  const materialisedYears = records
    .map((record) => Number(record?.data_year))
    .filter((year) => Number.isFinite(year));

  return materialisedYears.length ? Math.max(...materialisedYears) : null;
}

function getMaterialisedCountryCodeSet(
  briefings = [],
  materialisedCountryCodes = [],
) {
  const codes = materialisedCountryCodes.length
    ? materialisedCountryCodes
    : briefings.map((briefing) => briefing.code);

  return new Set(codes.filter(Boolean));
}

export function getOverviewNarrative(
  status,
  monitoredCountries,
  materialisedCountries,
) {
  if (status === "running") {
    return "The data pipeline is running. Country briefings are loading — the overview will refresh automatically when complete.";
  }

  if (status === "complete") {
    return `Showing the current global economic outlook across ${materialisedCountries} of ${monitoredCountries} tracked markets. Select a country below to drill into its indicator trends and briefing.`;
  }

  if (status === "failed") {
    return "The latest data refresh failed. The overview reflects the most recent available data. Run the pipeline again from the trigger page to refresh.";
  }

  return `Showing the current global economic outlook. ${monitoredCountries} markets are tracked, with ${materialisedCountries} briefings currently available.`;
}

export function getEmptyStateHeading(status) {
  if (status === "running") {
    return "Loading market data";
  }

  if (status === "failed") {
    return "Data refresh failed";
  }

  return "No data yet";
}

export function getEmptyStateBody(status) {
  if (status === "running") {
    return "The pipeline is fetching, analysing, and storing the latest economic data. This page will update automatically once the briefings are ready.";
  }

  if (status === "failed") {
    return "The last pipeline run ended in failure. Review the error details on the trigger page and run again to refresh the market briefings.";
  }

  return "No market briefings are available yet. Run the pipeline from the trigger page to fetch and analyze the latest World Bank economic data.";
}

function getOutlookCounts(briefings = []) {
  return briefings.reduce(
    (counts, briefing) => {
      const outlookKey = briefing.outlook?.toLowerCase() || "neutral";
      counts[outlookKey] = (counts[outlookKey] || 0) + 1;
      return counts;
    },
    {
      bearish: 0,
      bullish: 0,
      cautious: 0,
      neutral: 0,
    },
  );
}

function getStressRank(indicatorCode, changeValue) {
  if (changeValue == null) {
    return -1;
  }

  if (getSignalPolarity(indicatorCode) === "higher_is_better") {
    return changeValue * -1;
  }

  return changeValue;
}

function getStatisticalAnomalyLabel(anomalyCount) {
  if (anomalyCount === 1) {
    return "1 statistical anomaly";
  }

  return `${anomalyCount} statistical anomalies`;
}

export function getPanelSignals(indicators = []) {
  return SIGNAL_PRIORITY.map((indicatorCode) => {
    const signalIndicators = indicators.filter(
      (indicator) => indicator.indicator_code === indicatorCode,
    );

    if (!signalIndicators.length) {
      return null;
    }

    const adverseCount = signalIndicators.filter((indicator) =>
      isAdverseMove(indicatorCode, getDisplayChangeValue(indicator)),
    ).length;
    const anomalyCount = signalIndicators.filter(
      (indicator) => indicator.is_anomaly,
    ).length;
    const stressedIndicator = [...signalIndicators]
      .filter((indicator) => getDisplayChangeValue(indicator) != null)
      .sort(
        (left, right) =>
          getStressRank(indicatorCode, getDisplayChangeValue(right)) -
          getStressRank(indicatorCode, getDisplayChangeValue(left)),
      )[0];

    return {
      indicator_code: indicatorCode,
      indicator_name:
        signalIndicators[0].indicator_name ||
        signalIndicators[0].indicator_code,
      anomalyCount,
      statisticalAnomalyLabel: getStatisticalAnomalyLabel(anomalyCount),
      statisticalAnomalyTone:
        anomalyCount > 0 ? "text-critical" : "text-secondary",
      adverseCount,
      coverageCount: signalIndicators.length,
      stressedMarketCode: stressedIndicator?.country_code || null,
      stressedMarketChange: getDisplayChangeValue(stressedIndicator),
      stressedMarketChangeBasis: getDisplayChangeBasis(stressedIndicator),
    };
  }).filter(Boolean);
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
    return `${step.duration_ms}ms elapsed in the active runtime.`;
  }

  if (step.status === "running") {
    return "Currently executing in the active runtime.";
  }

  if (step.status === "failed") {
    return "Execution failed before the slice could complete.";
  }

  if (step.status === "complete") {
    return "Step completed for the latest available data.";
  }

  return "Awaiting pipeline execution.";
}

export function getBoundedOverlayPosition(point, bounds, overlay) {
  const [x, y] = point;
  const preferredLeft = x - overlay.width / 2;
  const maximumLeft = Math.max(
    overlay.edgePadding,
    bounds.width - overlay.width - overlay.edgePadding,
  );
  const clampedLeft = Math.min(
    maximumLeft,
    Math.max(overlay.edgePadding, preferredLeft),
  );
  const availableAbove = y - overlay.gap - overlay.edgePadding;
  const availableBelow = bounds.height - y - overlay.gap - overlay.edgePadding;
  const openBelow =
    availableBelow >= overlay.height || availableBelow >= availableAbove;
  const preferredTop = openBelow
    ? y + overlay.gap
    : y - (overlay.height + overlay.gap);
  const maximumTop = Math.max(
    overlay.edgePadding,
    bounds.height - overlay.height - overlay.edgePadding,
  );
  const clampedTop = Math.min(
    maximumTop,
    Math.max(overlay.edgePadding, preferredTop),
  );

  return {
    left: clampedLeft,
    top: clampedTop,
  };
}

export function getOutlookTone(outlook) {
  if (!outlook) {
    return "neutral";
  }

  return OUTLOOK_TONE_MAP[outlook.toLowerCase()] || "neutral";
}

export function deriveOverviewMetrics(overview) {
  const pipelineStatus = overview.status?.status || "idle";
  const monitoredCountries = overview.countries.length;
  const materialisedCountryCodes = overview.panelOverview?.country_codes?.length
    ? overview.panelOverview.country_codes
    : [...new Set(overview.briefings.map((briefing) => briefing.code))];
  const materialisedCountries = materialisedCountryCodes.length;
  const anomalyCount = overview.indicators.filter(
    (indicator) => indicator.is_anomaly,
  ).length;
  const latestRefresh = getLatestRefresh(overview.indicators, overview.status);
  const panelSignals = getPanelSignals(overview.indicators);
  const outlookCounts = getOutlookCounts(overview.briefings);
  const pipelineSteps = overview.status?.steps?.length
    ? overview.status.steps
    : FALLBACK_STEPS;

  return {
    pipelineStatus,
    monitoredCountries,
    materialisedCountries,
    anomalyCount,
    latestRefresh,
    outlookCounts,
    panelSignals,
    panelOverview: overview.panelOverview || null,
    pipelineSteps,
    riskLoadedMarkets: outlookCounts.bearish + outlookCounts.cautious,
  };
}

export function deriveRegionalBreakdown(
  countries = [],
  briefings = [],
  materialisedCountryCodes = [],
) {
  const briefingByCode = new Map(
    briefings.map((briefing) => [briefing.code, briefing]),
  );
  const materialisedCodeSet = getMaterialisedCountryCodeSet(
    briefings,
    materialisedCountryCodes,
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
    if (materialisedCodeSet.has(country.code)) {
      region.materialisedCount += 1;
    }
    if (briefing) {
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
  options = {},
) {
  const { focusedCode = null, materialisedCountryCodes = [] } = options;
  const briefingByCode = new Map(
    briefings.map((briefing) => [briefing.code, briefing]),
  );
  const materialisedCodeSet = getMaterialisedCountryCodeSet(
    briefings,
    materialisedCountryCodes,
  );

  return countries.map((country) => {
    const briefing = briefingByCode.get(country.code);
    const isMaterialised = materialisedCodeSet.has(country.code);
    const isFocused = country.code === focusedCode;

    return {
      code: country.code,
      href: `/country/${country.code.toLowerCase()}`,
      isFocused,
      isMaterialised,
      name: country.name,
      region: country.region || "Unassigned",
      statusLabel: isMaterialised ? "Live" : "Pending",
      summary: isMaterialised
        ? `${country.name} briefing is available in the current slice.`
        : `${country.name} is tracked but its briefing is not yet available.`,
      tone: isMaterialised ? getOutlookTone(briefing?.outlook) : "neutral",
    };
  });
}

function getCountryPressureScore(countryIndicators = []) {
  return countryIndicators.reduce((score, indicator) => {
    let nextScore = score;

    if (indicator.is_anomaly) {
      nextScore += 4;
    }

    const changeValue = getDisplayChangeValue(indicator);
    if (isAdverseMove(indicator.indicator_code, changeValue)) {
      nextScore += 2;
    }

    if (changeValue != null) {
      nextScore += Math.min(
        3,
        Math.abs(Number(changeValue) || 0) / 3,
      );
    }

    return nextScore;
  }, 0);
}

export function derivePressureQueue(
  countries = [],
  indicators = [],
  materialisedCountryCodes = [],
) {
  const indicatorsByCountry = new Map();
  const materialisedCodeSet = getMaterialisedCountryCodeSet(
    [],
    materialisedCountryCodes,
  );

  indicators.forEach((indicator) => {
    const countryCode = indicator.country_code;
    if (!countryCode) {
      return;
    }

    const currentIndicators = indicatorsByCountry.get(countryCode) || [];
    currentIndicators.push(indicator);
    indicatorsByCountry.set(countryCode, currentIndicators);
  });

  return countries
    .map((country) => {
      const countryIndicators = indicatorsByCountry.get(country.code) || [];
      const anomalyCount = countryIndicators.filter(
        (indicator) => indicator.is_anomaly,
      ).length;
      const adverseCount = countryIndicators.filter((indicator) =>
        isAdverseMove(
          indicator.indicator_code,
          getDisplayChangeValue(indicator),
        ),
      ).length;

      return {
        code: country.code,
        isMaterialised: materialisedCodeSet.has(country.code),
        anomalyCount,
        adverseCount,
        pressureScore: getCountryPressureScore(countryIndicators),
      };
    })
    .sort((left, right) => {
      if (left.isMaterialised !== right.isMaterialised) {
        return left.isMaterialised ? -1 : 1;
      }

      if (right.pressureScore !== left.pressureScore) {
        return right.pressureScore - left.pressureScore;
      }

      if (right.anomalyCount !== left.anomalyCount) {
        return right.anomalyCount - left.anomalyCount;
      }

      if (right.adverseCount !== left.adverseCount) {
        return right.adverseCount - left.adverseCount;
      }

      return left.code.localeCompare(right.code);
    });
}

function getLeadIndicatorForCountry(countryIndicators = []) {
  return (
    SIGNAL_PRIORITY.map((indicatorCode) =>
      countryIndicators.find(
        (indicator) => indicator.indicator_code === indicatorCode,
      ),
    ).find(Boolean) || countryIndicators[0] || null
  );
}

function getWatchlistStatusLabel(market, briefing) {
  if (briefing?.outlook) {
    return briefing.outlook.toUpperCase();
  }

  return market.isMaterialised ? "LIVE" : "PENDING";
}

export function derivePressureWatchlist(
  countries = [],
  briefings = [],
  indicators = [],
  materialisedCountryCodes = [],
  limit = 3,
) {
  const coverageBoard = deriveCoverageBoard(countries, briefings, {
    materialisedCountryCodes,
  });
  const coverageBoardByCode = new Map(
    coverageBoard.map((market) => [market.code, market]),
  );
  const briefingByCode = new Map(
    briefings.map((briefing) => [briefing.code, briefing]),
  );
  const indicatorsByCountry = new Map();

  indicators.forEach((indicator) => {
    const countryCode = indicator.country_code;
    if (!countryCode) {
      return;
    }

    const currentIndicators = indicatorsByCountry.get(countryCode) || [];
    currentIndicators.push(indicator);
    indicatorsByCountry.set(countryCode, currentIndicators);
  });

  return derivePressureQueue(countries, indicators, materialisedCountryCodes)
    .map((queueMarket) => {
      const market = coverageBoardByCode.get(queueMarket.code);
      if (!market) {
        return null;
      }

      const briefing = briefingByCode.get(queueMarket.code) || null;
      const countryIndicators = indicatorsByCountry.get(queueMarket.code) || [];
      const leadIndicator = getLeadIndicatorForCountry(countryIndicators);

      return {
        code: market.code,
        href: market.href,
        isMaterialised: market.isMaterialised,
        name: market.name,
        region: market.region,
        statusLabel: getWatchlistStatusLabel(market, briefing),
        statusTone: briefing?.outlook
          ? getOutlookTone(briefing.outlook)
          : market.tone,
        summary: briefing?.macro_synthesis || market.summary,
        anomalyCount: queueMarket.anomalyCount,
        adverseCount: queueMarket.adverseCount,
        pressureScore: queueMarket.pressureScore,
        leadIndicatorCode: leadIndicator?.indicator_code || null,
        leadIndicatorName: leadIndicator?.indicator_name || null,
        leadChange: getDisplayChangeValue(leadIndicator),
        leadChangeBasis: getDisplayChangeBasis(leadIndicator),
      };
    })
    .filter(Boolean)
    .slice(0, limit);
}
