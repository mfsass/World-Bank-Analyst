"""Pandas statistical analysis module.

Processes raw World Bank data to compute year-over-year changes,
detect anomalies, and prepare structured context for the LLM.
Python + Pandas handles the math. The LLM writes the narrative.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)
GDP_GROWTH_INDICATOR_CODE = "NY.GDP.MKTP.KD.ZG"
INFLATION_INDICATOR_CODE = "FP.CPI.TOTL.ZG"
UNEMPLOYMENT_INDICATOR_CODE = "SL.UEM.TOTL.ZS"

# Anomaly detection uses a per-indicator z-score rather than a single fixed
# percentage threshold.  A move is flagged when its year-over-year percent
# change is more than Z_SCORE_THRESHOLD standard deviations from that
# indicator's own historical mean across the full cross-panel window.
#
# Why z-score?
#   A uniform 3% threshold treats GDP growth and unemployment identically.
#   GDP growth crossing 3% is routine; CPI crossing 3% may signal overheating;
#   a 3% shift in debt-to-GDP is almost invisible.  Each indicator has its own
#   natural volatility range, so the anomaly bar must be relative to that
#   indicator's own history, not an arbitrary constant.
#
# Why 2.0 standard deviations?
#   The conventional statistical significance threshold — roughly the outer 5%
#   of a normal distribution.  Defensible in a finance context and keeps the
#   signal-to-noise ratio practical across a 17-country, 6-indicator panel.
#
# Why pool across all countries per indicator (not per country)?
#   With ~7 annual observations per country, per-country std collapses to noise.
#   The cross-panel pool gives ~119 observations per indicator — enough for a
#   meaningful baseline while also measuring each country against the global
#   peer group, which is the right frame for a risk-flagging system.
Z_SCORE_THRESHOLD = 2.0


def _add_anomaly_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows whose change is anomalous relative to the indicator's history.

    Computes z-scores per indicator across the full cross-country window, then
    marks as anomalous any row where |z| >= Z_SCORE_THRESHOLD.  Rows without a
    prior-year value (first observation per country-indicator) are never flagged.

    Args:
        df: DataFrame with a 'percent_change' column.

    Returns:
        Same DataFrame with 'z_score' and 'is_anomaly' columns added in-place.
    """
    # Compute cross-panel mean and std per indicator (pooled across all countries).
    indicator_stats = (
        df.groupby("indicator_code")["percent_change"]
        .agg(["mean", "std"])
        .rename(columns={"mean": "_ind_mean", "std": "_ind_std"})
    )
    df = df.join(indicator_stats, on="indicator_code")

    # z = (x - μ) / σ; where std is 0 or NaN, treat every point as non-anomalous
    non_zero_std = df["_ind_std"].replace(0, pd.NA).notna()
    df["z_score"] = pd.NA
    df.loc[non_zero_std, "z_score"] = (
        (df.loc[non_zero_std, "percent_change"] - df.loc[non_zero_std, "_ind_mean"])
        / df.loc[non_zero_std, "_ind_std"]
    )

    df["is_anomaly"] = df["z_score"].abs() >= Z_SCORE_THRESHOLD

    # Drop intermediate stats columns — callers don't need them.
    df = df.drop(columns=["_ind_mean", "_ind_std"])
    return df


def compute_changes(data_points: list[dict[str, Any]]) -> pd.DataFrame:
    """Compute year-over-year changes and flag statistically anomalous moves.

    Args:
        data_points: List of dicts with 'country_code', 'indicator_code',
                     'year', and 'value' keys.

    Returns:
        DataFrame with added 'percent_change', 'z_score', and 'is_anomaly'
        columns.  'is_anomaly' is True when the year-over-year percent change
        exceeds Z_SCORE_THRESHOLD standard deviations from the indicator's
        cross-panel mean.
    """
    if not data_points:
        return pd.DataFrame()

    df = pd.DataFrame(data_points)
    df = df.sort_values(["country_code", "indicator_code", "year"])

    df["previous_value"] = df.groupby(
        ["country_code", "indicator_code"]
    )["value"].shift(1)

    df["percent_change"] = (
        (df["value"] - df["previous_value"]) / df["previous_value"].abs() * 100
    )

    df = _add_anomaly_flags(df)

    logger.info(
        "Processed %d data points, %d anomalies detected (z >= %.1f σ)",
        len(df),
        int(df["is_anomaly"].sum()),
        Z_SCORE_THRESHOLD,
    )
    return df


def build_indicator_time_series(
    df: pd.DataFrame,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Build ordered per-country indicator histories from the analysed frame.

    The API needs more than the latest snapshot for Phase 1. This helper keeps
    the history fully deterministic by reusing the analysed DataFrame rather
    than reconstructing yearly values later from raw payloads.

    Args:
        df: DataFrame returned by ``compute_changes``.

    Returns:
        Mapping of ``(country_code, indicator_code)`` to ascending yearly points.
    """
    if df.empty:
        return {}

    history_by_indicator: dict[tuple[str, str], list[dict[str, Any]]] = {}
    ordered_df = df.sort_values(["country_code", "indicator_code", "year"])

    for (country_code, indicator_code), group in ordered_df.groupby(
        ["country_code", "indicator_code"], sort=False
    ):
        history_by_indicator[(str(country_code).upper(), str(indicator_code))] = [
            _build_time_series_point(row) for _, row in group.iterrows()
        ]

    return history_by_indicator


def prepare_llm_context(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Prepare structured context for the LLM analysis step.

    Extracts the latest data point per country-indicator pair with
    computed statistics ready for the AI analysis chain.  Includes z_score
    so the LLM can distinguish a 2.1σ move from a 4.0σ shock in narrative.

    Args:
        df: DataFrame with percent_change, z_score, and is_anomaly columns.

    Returns:
        List of context dicts suitable for LLM prompt injection.
    """
    if df.empty:
        return []

    latest = df.sort_values("year").groupby(
        ["country_code", "indicator_code"]
    ).last().reset_index()

    contexts = []
    for _, row in latest.iterrows():
        contexts.append(
            {
                "country_code": str(row["country_code"]).upper(),
                "country_name": row.get("country_name", ""),
                "indicator_code": row["indicator_code"],
                "indicator_name": row.get("indicator_name", ""),
                "latest_value": _round_optional_number(row.get("value"), digits=4),
                "previous_value": _round_optional_number(
                    row.get("previous_value"), digits=4
                ),
                "percent_change": _round_optional_number(
                    row.get("percent_change"), digits=2
                ),
                # z_score gives the LLM the anomaly severity, not just a boolean.
                "z_score": _round_optional_number(row.get("z_score"), digits=2),
                "is_anomaly": bool(row.get("is_anomaly", False)),
                "data_year": int(row["year"]),
            }
        )

    logger.info("Prepared %d LLM context entries", len(contexts))
    return contexts


def classify_country_regimes(
    indicator_contexts: list[dict[str, Any]],
) -> dict[str, str]:
    """Classify one deterministic macro regime label per country.

    The label is intentionally rule-based rather than model-generated so the UI
    can use it as stable directional context without introducing another AI
    decision boundary.

    Args:
        indicator_contexts: Latest indicator contexts per country.

    Returns:
        Mapping of country code to regime label.
    """
    indicators_by_country: dict[str, list[dict[str, Any]]] = {}
    for context in indicator_contexts:
        country_code = str(context.get("country_code", "")).upper()
        indicators_by_country.setdefault(country_code, []).append(context)

    return {
        country_code: classify_regime_label(indicators)
        for country_code, indicators in indicators_by_country.items()
    }


def classify_regime_label(indicators: list[dict[str, Any]]) -> str:
    """Return a deterministic macro regime label from the latest signal mix.

    The rules deliberately stay legible:
    - contraction: outright negative growth, or near-flat growth with sharply
      worsening unemployment
    - recovery: growth has turned positive after contraction, or labour slack is
      improving materially while growth stays positive
    - overheating: solid growth plus elevated inflation
    - stagnation: weak but non-negative growth without a clearer recovery signal
    - expansion: the residual state when growth is positive and broad stress is
      not acute

    Args:
        indicators: Latest indicator contexts for one country.

    Returns:
        One regime label from the approved fixed set.
    """
    indicators_by_code = {
        str(indicator.get("indicator_code", "")): indicator for indicator in indicators
    }
    growth = indicators_by_code.get(GDP_GROWTH_INDICATOR_CODE, {})
    inflation = indicators_by_code.get(INFLATION_INDICATOR_CODE, {})
    unemployment = indicators_by_code.get(UNEMPLOYMENT_INDICATOR_CODE, {})

    growth_value = _as_float(growth.get("latest_value"))
    previous_growth_value = _as_float(growth.get("previous_value"))
    inflation_value = _as_float(inflation.get("latest_value"))
    unemployment_change = _as_float(unemployment.get("percent_change"))

    if growth_value is None:
        return "stagnation"

    if growth_value < 0 or (
        growth_value < 1.0
        and unemployment_change is not None
        and unemployment_change >= 3.0
    ):
        return "contraction"

    if growth_value > 0 and (
        (previous_growth_value is not None and previous_growth_value < 0)
        or (
            unemployment_change is not None
            and unemployment_change <= -2.0
            and growth_value >= 1.0
        )
    ):
        return "recovery"

    if growth_value >= 3.0 and inflation_value is not None and inflation_value >= 6.0:
        return "overheating"

    if growth_value < 1.5:
        return "stagnation"

    return "expansion"


def _build_time_series_point(row: Any) -> dict[str, Any]:
    """Convert one analysed row into the API's historical point shape."""
    point: dict[str, Any] = {
        "year": int(row["year"]),
        "value": round(float(row["value"]), 4),
        "is_anomaly": bool(row.get("is_anomaly", False)),
    }
    previous_value = _round_optional_number(row.get("previous_value"), digits=4)
    percent_change = _round_optional_number(row.get("percent_change"), digits=2)
    z_score = _round_optional_number(row.get("z_score"), digits=2)

    if previous_value is not None:
        point["previous_value"] = previous_value
    if percent_change is not None:
        point["percent_change"] = percent_change
    if z_score is not None:
        point["z_score"] = z_score

    return point


def _round_optional_number(value: Any, *, digits: int) -> float | None:
    """Round a numeric value when present, else return None."""
    numeric_value = _as_float(value)
    if numeric_value is None:
        return None
    return round(numeric_value, digits)


def _as_float(value: Any) -> float | None:
    """Return a float when the value is present and numeric."""
    if value is None or pd.isna(value):
        return None
    return float(value)
