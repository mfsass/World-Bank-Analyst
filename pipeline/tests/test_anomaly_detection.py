"""Business tests for per-indicator z-score anomaly detection.

These tests prove requirements, not implementation details.  Each test
asserts a concrete, finance-grounded expectation about what the analyser
should flag — and, importantly, what it should not flag.

Design rationale for the detection approach is documented in analyser.py
and in ADR-008.
"""

from __future__ import annotations

from pipeline.analyser import Z_SCORE_THRESHOLD, compute_changes, prepare_llm_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_points(
    indicator: str,
    country: str,
    year_value_pairs: list[tuple[int, float]],
) -> list[dict]:
    """Build minimal data-point dicts for a single country-indicator series."""
    return [
        {"country_code": country, "indicator_code": indicator, "year": y, "value": v}
        for y, v in year_value_pairs
    ]


def _make_panel(
    indicator: str,
    panel: dict[str, list[tuple[int, float]]],
) -> list[dict]:
    """Build data points for multiple countries on the same indicator."""
    points = []
    for country_code, series in panel.items():
        points.extend(_make_points(indicator, country_code, series))
    return points


# ---------------------------------------------------------------------------
# Core detection: z-score flags large cross-panel outliers
# ---------------------------------------------------------------------------


def test_extreme_shock_is_flagged_as_anomaly() -> None:
    """A move that is many standard deviations from the panel mean must be flagged.

    Real-world parallel: COVID-2020 GDP contractions (-6% to -10%) relative to
    the historic cross-panel baseline of ~+2-3% annual growth.
    """
    # 9 countries with normal GDP growth, 1 with a large shock.
    normal_series = [(2017, 100.0), (2018, 103.0), (2019, 103.0)]  # ~3% each year
    shock_series = [(2017, 100.0), (2018, 100.0), (2019, 60.0)]    # -40% shock

    panel = {f"C{i:02d}": normal_series for i in range(9)}
    panel["SHOCK"] = shock_series

    df = compute_changes(_make_panel("NY.GDP.MKTP.KD.ZG", panel))

    shock_latest = df[
        (df["country_code"] == "SHOCK") & (df["year"] == 2019)
    ]
    assert shock_latest["is_anomaly"].all(), (
        "A -40% GDP shock must be flagged as anomalous."
    )


def test_routine_gdp_growth_is_not_flagged() -> None:
    """Routine growth within the normal range for the panel must not be flagged.

    A uniform pool of routine growth has zero std; even a slightly different
    country should not be flagged if the panel itself has no meaningful spread.
    This verifies the detector doesn't produce spurious flags on clean data.
    """
    routine_series = [(2017, 100.0), (2018, 102.0), (2019, 103.0)]  # ~2% growth

    panel = {f"C{i:02d}": routine_series for i in range(10)}

    df = compute_changes(_make_panel("NY.GDP.MKTP.KD.ZG", panel))

    assert not df["is_anomaly"].any(), (
        "Uniform routine growth must produce no anomaly flags."
    )


def test_each_indicator_is_judged_by_its_own_baseline() -> None:
    """A move that is normal for one indicator may be anomalous for another.

    GDP growth of 5% is routine.  A 5% single-year shift in an unemployment
    rate that historically moves by <1% per year is a genuine shock.
    This verifies that cross-indicator pooling is NOT happening.
    """
    # GDP indicator: historical moves cluster around 4-6%, so a 5% move is typical.
    gdp_panel = {
        "BR": [(2017, 100.0), (2018, 104.0), (2019, 109.0)],
        "US": [(2017, 100.0), (2018, 106.0), (2019, 111.0)],
        "GB": [(2017, 100.0), (2018, 105.0), (2019, 110.0)],
        "DE": [(2017, 100.0), (2018, 104.5), (2019, 109.5)],
        "FR": [(2017, 100.0), (2018, 104.0), (2019, 108.0)],
        "JP": [(2017, 100.0), (2018, 104.0), (2019, 109.0)],
        "AU": [(2017, 100.0), (2018, 105.0), (2019, 110.0)],
        "CA": [(2017, 100.0), (2018, 104.0), (2019, 109.0)],
        "KR": [(2017, 100.0), (2018, 104.5), (2019, 108.5)],
        "TEST": [(2017, 100.0), (2018, 104.0), (2019, 109.2)],  # ~5%: routine for GDP
    }

    # Unemployment: historically stable (<0.5% change), then a 5-point jump.
    unemp_panel = {
        "BR": [(2017, 10.0), (2018, 10.1), (2019, 10.2)],
        "US": [(2017, 4.0), (2018, 4.1), (2019, 4.0)],
        "GB": [(2017, 5.0), (2018, 5.0), (2019, 5.1)],
        "DE": [(2017, 3.5), (2018, 3.6), (2019, 3.5)],
        "FR": [(2017, 9.0), (2018, 9.1), (2019, 9.0)],
        "JP": [(2017, 2.8), (2018, 2.9), (2019, 2.8)],
        "AU": [(2017, 5.1), (2018, 5.2), (2019, 5.1)],
        "CA": [(2017, 6.2), (2018, 6.3), (2019, 6.2)],
        "KR": [(2017, 3.5), (2018, 3.6), (2019, 3.5)],
        "TEST": [(2017, 5.0), (2018, 5.1), (2019, 10.0)],  # sudden spike: anomalous
    }

    gdp_points = _make_panel("NY.GDP.MKTP.KD.ZG", gdp_panel)
    unemp_points = _make_panel("SL.UEM.TOTL.ZS", unemp_panel)
    df = compute_changes(gdp_points + unemp_points)

    gdp_test = df[
        (df["country_code"] == "TEST")
        & (df["indicator_code"] == "NY.GDP.MKTP.KD.ZG")
        & (df["year"] == 2019)
    ]
    unemp_test = df[
        (df["country_code"] == "TEST")
        & (df["indicator_code"] == "SL.UEM.TOTL.ZS")
        & (df["year"] == 2019)
    ]

    assert not gdp_test["is_anomaly"].all(), (
        "A ~5% GDP move within the normal panel range must NOT be flagged."
    )
    assert unemp_test["is_anomaly"].all(), (
        "A large unemployment spike relative to the stable panel must be flagged."
    )


def test_z_score_is_present_and_numerically_consistent() -> None:
    """z_score column must be present and agree with is_anomaly.

    Verifies: abs(z_score) >= Z_SCORE_THRESHOLD ↔ is_anomaly is True.
    """
    normal_series = [(2017, 100.0), (2018, 102.0), (2019, 104.0)]
    shock_series = [(2017, 100.0), (2018, 102.0), (2019, 60.0)]

    panel = {f"C{i}": normal_series for i in range(8)}
    panel["SHOCK"] = shock_series

    df = compute_changes(_make_panel("FP.CPI.TOTL.ZG", panel))

    flagged = df[df["is_anomaly"]]
    not_flagged = df[~df["is_anomaly"] & df["z_score"].notna()]

    assert (flagged["z_score"].abs() >= Z_SCORE_THRESHOLD).all(), (
        "Every flagged row must have |z_score| >= threshold."
    )
    assert (not_flagged["z_score"].abs() < Z_SCORE_THRESHOLD).all(), (
        "Every non-flagged row must have |z_score| < threshold."
    )


def test_first_observation_is_never_flagged() -> None:
    """The first year of data has no prior value, so it must not produce a flag.

    There is no meaningful year-over-year change for the first observation,
    so treating it as anomalous would create noise in the signal.
    """
    series = [(2017, 100.0), (2018, 110.0), (2019, 111.0)]
    panel = {f"C{i}": series for i in range(5)}

    df = compute_changes(_make_panel("GC.DOD.TOTL.GD.ZS", panel))

    first_obs = df[df["year"] == 2017]
    assert not first_obs["is_anomaly"].any(), (
        "First observation per country must never be flagged as anomalous."
    )


def test_empty_input_returns_empty_dataframe() -> None:
    """An empty input list must return an empty DataFrame without raising."""
    df = compute_changes([])
    assert df.empty


# ---------------------------------------------------------------------------
# Context enrichment: z_score passes through to LLM context
# ---------------------------------------------------------------------------


def test_llm_context_includes_z_score() -> None:
    """prepare_llm_context must forward z_score so the LLM knows anomaly severity."""
    shock_series = [(2017, 100.0), (2018, 100.0), (2019, 50.0)]
    normal_series = [(2017, 100.0), (2018, 102.0), (2019, 104.0)]

    panel = {f"C{i}": normal_series for i in range(8)}
    panel["SHOCK"] = shock_series

    df = compute_changes(_make_panel("NY.GDP.MKTP.KD.ZG", panel))
    contexts = prepare_llm_context(df)

    shock_ctx = next(c for c in contexts if c["country_code"] == "SHOCK")

    assert "z_score" in shock_ctx, "z_score must be present in LLM context."
    assert shock_ctx["is_anomaly"] is True
    assert shock_ctx["z_score"] is not None
    assert abs(shock_ctx["z_score"]) >= Z_SCORE_THRESHOLD


def test_llm_context_z_score_none_when_no_history() -> None:
    """A country with a single observation has no z_score and must pass None."""
    # Single-observation country (no prior year).
    single = [{"country_code": "X1", "indicator_code": "IND", "year": 2023, "value": 5.0}]

    df = compute_changes(single)
    contexts = prepare_llm_context(df)

    assert contexts[0]["z_score"] is None
    assert contexts[0]["is_anomaly"] is False
