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
GDP_LEVEL_INDICATOR_CODE = "NY.GDP.MKTP.CD"
INFLATION_INDICATOR_CODE = "FP.CPI.TOTL.ZG"
UNEMPLOYMENT_INDICATOR_CODE = "SL.UEM.TOTL.ZS"
CURRENT_ACCOUNT_INDICATOR_CODE = "BN.CAB.XOKA.GD.ZS"
GOVERNMENT_DEBT_INDICATOR_CODE = "GC.DOD.TOTL.GD.ZS"
RELATIVE_PERCENT_CHANGE_BASIS = "relative_percent"
PERCENTAGE_POINT_CHANGE_BASIS = "percentage_point"
HIGHER_IS_BETTER_POLARITY = "higher_is_better"
LOWER_IS_BETTER_POLARITY = "lower_is_better"
RATE_BASED_INDICATOR_CODES = {
    GDP_GROWTH_INDICATOR_CODE,
    INFLATION_INDICATOR_CODE,
    UNEMPLOYMENT_INDICATOR_CODE,
    CURRENT_ACCOUNT_INDICATOR_CODE,
    GOVERNMENT_DEBT_INDICATOR_CODE,
}
HIGHER_IS_BETTER_INDICATOR_CODES = {
    GDP_LEVEL_INDICATOR_CODE,
    GDP_GROWTH_INDICATOR_CODE,
    CURRENT_ACCOUNT_INDICATOR_CODE,
}
LOWER_IS_BETTER_INDICATOR_CODES = {
    INFLATION_INDICATOR_CODE,
    UNEMPLOYMENT_INDICATOR_CODE,
    GOVERNMENT_DEBT_INDICATOR_CODE,
}

# Anomaly detection: hybrid z-score approach
# -------------------------------------------
# Two complementary z-score lenses flag anomalous moves:
#
#  1. Cross-panel z (z_score): pool all 17 countries' YoY percent changes per
#     indicator.  Catches moves that are unusual relative to global peers.
#     Good for GDP growth and unemployment where peer comparison is meaningful.
#
#  2. Per-country z (z_score_local): each country's own historical mean/std
#     per indicator.  Catches moves that are unusual for *that* country's own
#     history, regardless of what peers are doing.  Fixes the current account
#     balance problem where pooled std across wildly different economies is so
#     large that nothing gets flagged.
#
# is_anomaly = |z_global| >= threshold  OR  |z_local| >= threshold
#
# Why 2.0σ?  The conventional outer-5% level.  Defensible in a finance
# context and keeps signal-to-noise practical across a 17-country panel.
Z_SCORE_THRESHOLD = 2.0


def _compute_z_scores(
    df: pd.DataFrame,
    group_cols: list[str],
    z_col_name: str,
    *,
    value_col: str,
) -> pd.DataFrame:
    """Compute z-scores for percent_change grouped by the given columns.

    Helper shared by both the cross-panel and per-country z-score paths.
    Adds a column named ``z_col_name`` to the DataFrame.

    Args:
        df: DataFrame with the column named by ``value_col``.
        group_cols: Columns to group by for mean/std computation.
        z_col_name: Name for the resulting z-score column.
        value_col: Column used for mean/std computation.

    Returns:
        DataFrame with the z-score column added.
    """
    stats = (
        df.groupby(group_cols)[value_col]
        .agg(["mean", "std"])
        .rename(columns={"mean": "_z_mean", "std": "_z_std"})
    )
    df = df.join(stats, on=group_cols)

    # z = (x - μ) / σ; where std is 0 or NaN, treat as non-anomalous
    valid_std = df["_z_std"].replace(0, pd.NA).notna()
    df[z_col_name] = pd.NA
    df.loc[valid_std, z_col_name] = (
        (df.loc[valid_std, value_col] - df.loc[valid_std, "_z_mean"])
        / df.loc[valid_std, "_z_std"]
    )

    df = df.drop(columns=["_z_mean", "_z_std"])
    return df


def _add_anomaly_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows whose change is anomalous using a hybrid z-score approach.

    Two complementary z-scores are computed:
      - z_score: cross-panel (all countries pooled per indicator)
      - z_score_local: per-country (each country's own history per indicator)

    A row is flagged when *either* |z| >= Z_SCORE_THRESHOLD.  This catches both
    globally unusual moves and historically unusual moves for the specific
    country.

    Args:
        df: DataFrame with a canonical 'change_value' column.

    Returns:
        DataFrame with 'z_score', 'z_score_local', and 'is_anomaly' columns.
    """
    # 1. Cross-panel z-score: compares each country against global peers
    df = _compute_z_scores(
        df, ["indicator_code"], "z_score", value_col="change_value"
    )

    # 2. Per-country z-score: compares each year against the country's own
    #    history for that indicator — catches moves unusual for *this* economy
    df = _compute_z_scores(
        df,
        ["country_code", "indicator_code"],
        "z_score_local",
        value_col="change_value",
    )

    # Anomaly if either lens flags the move.
    global_flag = (df["z_score"].abs() >= Z_SCORE_THRESHOLD).fillna(False)
    local_flag = (df["z_score_local"].abs() >= Z_SCORE_THRESHOLD).fillna(False)
    df["is_anomaly"] = global_flag | local_flag
    df["anomaly_basis"] = pd.NA
    df.loc[global_flag & ~local_flag, "anomaly_basis"] = "panel"
    df.loc[~global_flag & local_flag, "anomaly_basis"] = "historical"
    df.loc[global_flag & local_flag, "anomaly_basis"] = "panel_and_historical"

    return df


def _add_indicator_change_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Attach indicator-aware movement metrics to the analysed frame.

    ``percent_change`` remains the backward-compatible relative-percent field used
    throughout the existing API contract. The new canonical anomaly input is
    ``change_value`` paired with ``change_basis``:

    - level indicators (for this product, GDP in current US$) use relative %
    - rate and ratio indicators use percentage-point deltas
    """
    rate_based_mask = df["indicator_code"].astype(str).isin(RATE_BASED_INDICATOR_CODES)
    relative_previous = df["previous_value"].abs().replace(0, pd.NA)
    df["percent_change"] = (
        (df["value"] - df["previous_value"]) / relative_previous * 100
    )

    df["change_basis"] = RELATIVE_PERCENT_CHANGE_BASIS
    df.loc[rate_based_mask, "change_basis"] = PERCENTAGE_POINT_CHANGE_BASIS
    df["change_value"] = df["percent_change"]
    df.loc[rate_based_mask, "change_value"] = (
        df.loc[rate_based_mask, "value"] - df.loc[rate_based_mask, "previous_value"]
    )
    df["signal_polarity"] = HIGHER_IS_BETTER_POLARITY
    lower_is_better_mask = df["indicator_code"].astype(str).isin(
        LOWER_IS_BETTER_INDICATOR_CODES
    )
    df.loc[lower_is_better_mask, "signal_polarity"] = LOWER_IS_BETTER_POLARITY
    return df


def compute_changes(data_points: list[dict[str, Any]]) -> pd.DataFrame:
    """Compute year-over-year changes and flag statistically anomalous moves.

    Args:
        data_points: List of dicts with 'country_code', 'indicator_code',
                     'year', and 'value' keys.

    Returns:
        DataFrame with legacy ``percent_change`` plus canonical
        ``change_value``/``change_basis`` signal columns, along with anomaly
        fields.
    """
    if not data_points:
        return pd.DataFrame()

    df = pd.DataFrame(data_points)
    df = df.sort_values(["country_code", "indicator_code", "year"])

    df["previous_value"] = df.groupby(
        ["country_code", "indicator_code"]
    )["value"].shift(1)

    df = _add_indicator_change_metrics(df)
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
                "change_value": _round_optional_number(
                    row.get("change_value"), digits=2
                ),
                "change_basis": _optional_string(row.get("change_basis")),
                "signal_polarity": _optional_string(row.get("signal_polarity")),
                # z_score gives the LLM the anomaly severity, not just a boolean.
                "z_score": _round_optional_number(row.get("z_score"), digits=2),
                "is_anomaly": _as_bool(row.get("is_anomaly")),
                "anomaly_basis": _optional_string(row.get("anomaly_basis")),
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
        "is_anomaly": _as_bool(row.get("is_anomaly")),
    }
    previous_value = _round_optional_number(row.get("previous_value"), digits=4)
    percent_change = _round_optional_number(row.get("percent_change"), digits=2)
    z_score = _round_optional_number(row.get("z_score"), digits=2)
    z_score_local = _round_optional_number(row.get("z_score_local"), digits=2)

    if previous_value is not None:
        point["previous_value"] = previous_value
    if percent_change is not None:
        point["percent_change"] = percent_change
    change_value = _round_optional_number(row.get("change_value"), digits=2)
    if change_value is not None:
        point["change_value"] = change_value
    change_basis = _optional_string(row.get("change_basis"))
    if change_basis is not None:
        point["change_basis"] = change_basis
    signal_polarity = _optional_string(row.get("signal_polarity"))
    if signal_polarity is not None:
        point["signal_polarity"] = signal_polarity
    if z_score is not None:
        point["z_score"] = z_score
    if z_score_local is not None:
        point["z_score_local"] = z_score_local
    anomaly_basis = _optional_string(row.get("anomaly_basis"))
    if anomaly_basis is not None:
        point["anomaly_basis"] = anomaly_basis

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


def _optional_string(value: Any) -> str | None:
    """Return a string when the value is present, else None."""

    if value is None or pd.isna(value):
        return None

    return str(value)


def _as_bool(value: Any) -> bool:
    """Return a stable bool while treating missing values as False."""

    if value is None or pd.isna(value):
        return False

    return bool(value)
