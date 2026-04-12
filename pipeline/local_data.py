"""Deterministic fixture data for local development and CI.

This module is NOT a runtime concern. It exists so that ``PIPELINE_MODE=local``
(the dev/test override) and the live-pipeline unit tests can run without hitting
the World Bank API. It must not be imported or exercised in any deployed Cloud Run
environment.

Two fixture countries are supported:
- ``LOCAL_TARGET_COUNTRY`` ("ZA") — the original test fixture; used by pipeline
  unit tests that call ``run_pipeline()`` without an explicit country code, and by
  live-fetch tests that need a deterministic single-country slice.
- ``LOCAL_DEV_COUNTRY`` ("BR") — the default fixture for the Pipeline Trigger
  endpoint, so pressing "Run Pipeline" in the browser produces data for a country
  that is actually in the 17-country monitored panel.

The ``PIPELINE_MODE`` runtime default is ``"local"`` so local commands and tests
stay deterministic unless a deployed runtime explicitly opts into live fetches.
"""

from __future__ import annotations

from typing import Any

# ZA is kept as the test fixture country.  Pipeline unit tests that call
# run_pipeline() without an explicit country_code use this default and expect
# to find ZA records in the repository afterward.
LOCAL_TARGET_COUNTRY = "ZA"
LOCAL_TARGET_COUNTRY_NAME = "South Africa"
LOCAL_TARGET_COUNTRY_REGION = "Sub-Saharan Africa"
LOCAL_TARGET_COUNTRY_INCOME_LEVEL = "Upper middle income"

# BR is used by the Pipeline Trigger endpoint so the browser sees a monitored
# panel country after clicking "Run Pipeline" in PIPELINE_MODE=local.
LOCAL_DEV_COUNTRY = "BR"

LOCAL_SOURCE_NAME = "world_analyst_local_fixture"
LOCAL_SOURCE_DATE_RANGE = "2017:2023"

# South Africa fixture — original test slice, 7 data points per indicator.
_ZA_DATA_BY_INDICATOR: dict[str, list[tuple[int, float]]] = {
    "NY.GDP.MKTP.CD": [
        (2017, 349_554_116_353.0),
        (2018, 368_135_901_663.0),
        (2019, 351_431_649_241.0),
        (2020, 301_923_639_248.0),
        (2021, 419_015_389_291.0),
        (2022, 405_869_505_982.0),
        (2023, 377_781_197_441.0),
    ],
    "NY.GDP.MKTP.KD.ZG": [
        (2017, 1.4),
        (2018, 0.8),
        (2019, 0.2),
        (2020, -6.3),
        (2021, 4.7),
        (2022, 1.9),
        (2023, 0.6),
    ],
    "FP.CPI.TOTL.ZG": [
        (2017, 5.3),
        (2018, 4.6),
        (2019, 4.1),
        (2020, 3.3),
        (2021, 4.6),
        (2022, 6.9),
        (2023, 6.0),
    ],
    "SL.UEM.TOTL.ZS": [
        (2017, 27.1),
        (2018, 27.5),
        (2019, 28.7),
        (2020, 29.2),
        (2021, 33.6),
        (2022, 32.7),
        (2023, 32.1),
    ],
    "BN.CAB.XOKA.GD.ZS": [
        (2017, -2.4),
        (2018, -3.5),
        (2019, -2.8),
        (2020, 2.0),
        (2021, 3.7),
        (2022, -0.6),
        (2023, -1.8),
    ],
    "GC.DOD.TOTL.GD.ZS": [
        (2017, 49.1),
        (2018, 52.6),
        (2019, 56.3),
        (2020, 69.2),
        (2021, 68.0),
        (2022, 71.1),
        (2023, 74.8),
    ],
}

# Brazil fixture — used by the Pipeline Trigger endpoint so the browser sees a
# country from the active 17-country monitored panel even in deterministic local mode.
_BR_DATA_BY_INDICATOR: dict[str, list[tuple[int, float]]] = {
    "NY.GDP.MKTP.CD": [
        (2017, 2_063_512_487_357.0),
        (2018, 1_916_933_162_193.0),
        (2019, 1_873_196_645_030.0),
        (2020, 1_448_559_134_530.0),
        (2021, 1_649_622_207_600.0),
        (2022, 1_920_095_768_173.0),
        (2023, 2_173_665_015_480.0),
    ],
    "NY.GDP.MKTP.KD.ZG": [
        (2017, 1.3),
        (2018, 1.8),
        (2019, 1.2),
        (2020, -3.9),
        (2021, 5.0),
        (2022, 3.0),
        (2023, 2.9),
    ],
    "FP.CPI.TOTL.ZG": [
        (2017, 3.5),
        (2018, 3.7),
        (2019, 3.7),
        (2020, 3.2),
        (2021, 8.3),
        (2022, 9.3),
        (2023, 4.6),
    ],
    "SL.UEM.TOTL.ZS": [
        (2017, 12.8),
        (2018, 12.3),
        (2019, 11.9),
        (2020, 13.5),
        (2021, 13.2),
        (2022, 9.3),
        (2023, 7.8),
    ],
    "BN.CAB.XOKA.GD.ZS": [
        (2017, -0.7),
        (2018, -2.2),
        (2019, -2.7),
        (2020, -1.6),
        (2021, -2.8),
        (2022, -2.9),
        (2023, -1.5),
    ],
    "GC.DOD.TOTL.GD.ZS": [
        (2017, 74.2),
        (2018, 77.2),
        (2019, 79.9),
        (2020, 96.1),
        (2021, 90.6),
        (2022, 87.6),
        (2023, 88.1),
    ],
}

_INDICATOR_NAMES = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of total labor force)",
    "BN.CAB.XOKA.GD.ZS": "Current account balance (% of GDP)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt, total (% of GDP)",
}

_COUNTRY_METADATA: dict[str, dict[str, str]] = {
    "ZA": {
        "name": "South Africa",
        "iso3": "ZAF",
        "region": LOCAL_TARGET_COUNTRY_REGION,
        "income_level": LOCAL_TARGET_COUNTRY_INCOME_LEVEL,
    },
    "BR": {
        "name": "Brazil",
        "iso3": "BRA",
        "region": "Latin America & Caribbean",
        "income_level": "Upper middle income",
    },
}

_DATA_BY_COUNTRY: dict[str, dict[str, list[tuple[int, float]]]] = {
    "ZA": _ZA_DATA_BY_INDICATOR,
    "BR": _BR_DATA_BY_INDICATOR,
}


def load_local_data_points(country_code: str = LOCAL_TARGET_COUNTRY) -> list[dict[str, Any]]:
    """Load deterministic World Bank-like fixture data for the local slice.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.  Supported values are
            ``LOCAL_TARGET_COUNTRY`` ("ZA", the CI fixture) and ``LOCAL_DEV_COUNTRY``
            ("BR", used by the browser pipeline trigger).

    Returns:
        List of raw data point dictionaries.

    Raises:
        ValueError: If the requested country has no local fixture.
    """
    normalized = country_code.upper()
    country_data = _DATA_BY_COUNTRY.get(normalized)
    if country_data is None:
        raise ValueError(
            f"No local fixture for {normalized!r}. "
            f"Supported: {', '.join(_DATA_BY_COUNTRY)}"
        )

    meta = _COUNTRY_METADATA[normalized]
    data_points: list[dict[str, Any]] = []
    for indicator_code, year_values in country_data.items():
        for year, value in year_values:
            data_points.append(
                {
                    "country_code": normalized,
                    "country_name": meta["name"],
                    "country_iso3": meta["iso3"],
                    "indicator_code": indicator_code,
                    "indicator_name": _INDICATOR_NAMES[indicator_code],
                    "year": year,
                    "value": value,
                    "source_name": LOCAL_SOURCE_NAME,
                    "source_date_range": LOCAL_SOURCE_DATE_RANGE,
                }
            )

    return data_points
