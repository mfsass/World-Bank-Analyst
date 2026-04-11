"""Pandas statistical analysis module.

Processes raw World Bank data to compute year-over-year changes,
detect anomalies, and prepare structured context for the LLM.
Python + Pandas handles the math. The LLM writes the narrative.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLD = 3.0  # Percentage change threshold for anomaly detection


def compute_changes(data_points: list[dict[str, Any]]) -> pd.DataFrame:
    """Compute year-over-year percentage changes for indicator data.

    Args:
        data_points: List of dicts with 'country_code', 'indicator_code',
                     'year', and 'value' keys.

    Returns:
        DataFrame with added 'percent_change' and 'is_anomaly' columns.
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

    df["is_anomaly"] = df["percent_change"].abs() > ANOMALY_THRESHOLD

    logger.info(
        "Processed %d data points, %d anomalies detected",
        len(df),
        df["is_anomaly"].sum(),
    )
    return df


def prepare_llm_context(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Prepare structured context for the LLM analysis step.

    Extracts the latest data point per country-indicator pair with
    computed statistics ready for the AI analysis chain.

    Args:
        df: DataFrame with percent_change and is_anomaly columns.

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
            "is_anomaly": bool(row.get("is_anomaly", False)),
            "data_year": int(row["year"]),
        })

    logger.info("Prepared %d LLM context entries", len(contexts))
    return contexts
