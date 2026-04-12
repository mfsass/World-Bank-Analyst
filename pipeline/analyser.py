"""Pandas statistical analysis module.

Processes raw World Bank data to compute year-over-year changes,
detect anomalies, and prepare structured context for the LLM.
Python + Pandas handles the math. The LLM writes the narrative.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

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
        contexts.append({
            "country_code": row["country_code"],
            "country_name": row.get("country_name", ""),
            "indicator_code": row["indicator_code"],
            "indicator_name": row.get("indicator_name", ""),
            "latest_value": round(row["value"], 4),
            "previous_value": round(row["previous_value"], 4)
            if pd.notna(row.get("previous_value"))
            else None,
            "percent_change": round(row["percent_change"], 2)
            if pd.notna(row.get("percent_change"))
            else None,
            # z_score gives the LLM the anomaly severity, not just a boolean.
            "z_score": round(float(row["z_score"]), 2)
            if pd.notna(row.get("z_score"))
            else None,
            "is_anomaly": bool(row.get("is_anomaly", False)),
            "data_year": int(row["year"]),
        })

    logger.info("Prepared %d LLM context entries", len(contexts))
    return contexts
