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

const RATE_BASED_CHANGE = new Set([
  "NY.GDP.MKTP.KD.ZG",
  "FP.CPI.TOTL.ZG",
  "SL.UEM.TOTL.ZS",
  "BN.CAB.XOKA.GD.ZS",
  "GC.DOD.TOTL.GD.ZS",
]);

export function getDisplayChangeValue(indicator = {}) {
  if (indicator?.change_value != null) {
    return indicator.change_value;
  }

  return indicator?.percent_change ?? null;
}

export function getDisplayChangeBasis(indicatorOrCode) {
  if (
    indicatorOrCode &&
    typeof indicatorOrCode === "object" &&
    indicatorOrCode.change_basis
  ) {
    return indicatorOrCode.change_basis;
  }

  const indicatorCode =
    typeof indicatorOrCode === "string"
      ? indicatorOrCode
      : indicatorOrCode?.indicator_code;

  return RATE_BASED_CHANGE.has(indicatorCode)
    ? "percentage_point"
    : "relative_percent";
}

export function getSignalPolarity(indicatorOrCode) {
  if (
    indicatorOrCode &&
    typeof indicatorOrCode === "object" &&
    indicatorOrCode.signal_polarity
  ) {
    return indicatorOrCode.signal_polarity;
  }

  const indicatorCode =
    typeof indicatorOrCode === "string"
      ? indicatorOrCode
      : indicatorOrCode?.indicator_code;

  if (HIGHER_IS_BETTER.has(indicatorCode)) {
    return "higher_is_better";
  }

  if (LOWER_IS_BETTER.has(indicatorCode)) {
    return "lower_is_better";
  }

  return "higher_is_better";
}

export function formatChange(
  value,
  changeBasis = "relative_percent",
  { includePeriod = false, nullLabel = "--" } = {},
) {
  if (value == null) {
    return nullLabel;
  }

  const sign = value >= 0 ? "+" : "-";
  const suffix = changeBasis === "percentage_point" ? "pp" : "%";
  const periodSuffix = includePeriod ? " YoY" : "";
  return `${sign}${Math.abs(value).toFixed(2)}${suffix}${periodSuffix}`;
}

export function isAdverseMove(indicatorCode, changeValue) {
  if (changeValue == null) {
    return false;
  }

  return getSignalPolarity(indicatorCode) === "lower_is_better"
    ? changeValue > 0
    : changeValue < 0;
}

export function getSignalTone(indicatorCode, changeValue) {
  if (changeValue == null) {
    return "text-secondary";
  }

  return isAdverseMove(indicatorCode, changeValue)
    ? "text-critical"
    : "text-success";
}

export function getSignalDisposition(indicatorCode, changeValue) {
  if (changeValue == null || Math.abs(changeValue) < 0.001) {
    return "stable";
  }

  return isAdverseMove(indicatorCode, changeValue) ? "worsening" : "improving";
}

export function getDesiredDirectionLabel(indicatorCode) {
  return getSignalPolarity(indicatorCode) === "lower_is_better"
    ? "Better when lower"
    : "Better when higher";
}

export function getAnomalyLabel(anomalyBasis) {
  if (anomalyBasis === "panel") {
    return "Peer anomaly";
  }

  if (anomalyBasis === "historical") {
    return "Historical anomaly";
  }

  if (anomalyBasis === "panel_and_historical") {
    return "Peer + historical anomaly";
  }

  return "Anomaly";
}
