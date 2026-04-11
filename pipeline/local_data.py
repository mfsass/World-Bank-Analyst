"""Deterministic local ZA fixture data for the first vertical slice."""

from __future__ import annotations

from typing import Any

LOCAL_TARGET_COUNTRY = "ZA"
LOCAL_TARGET_COUNTRY_NAME = "South Africa"

_LOCAL_DATA_BY_INDICATOR: dict[str, list[tuple[int, float]]] = {
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

_INDICATOR_NAMES = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of total labor force)",
    "BN.CAB.XOKA.GD.ZS": "Current account balance (% of GDP)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt, total (% of GDP)",
}


def load_local_data_points(country_code: str = LOCAL_TARGET_COUNTRY) -> list[dict[str, Any]]:
    """Load deterministic World Bank-like fixture data for the local slice.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.

    Returns:
        List of raw data point dictionaries.

    Raises:
        ValueError: If the requested country is outside the first-slice scope.
    """
    normalized = country_code.upper()
    if normalized != LOCAL_TARGET_COUNTRY:
        raise ValueError(f"Local first slice only supports {LOCAL_TARGET_COUNTRY}")

    data_points: list[dict[str, Any]] = []
    for indicator_code, year_values in _LOCAL_DATA_BY_INDICATOR.items():
        for year, value in year_values:
            data_points.append(
                {
                    "country_code": normalized,
                    "country_name": LOCAL_TARGET_COUNTRY_NAME,
                    "country_iso3": "ZAF",
                    "indicator_code": indicator_code,
                    "indicator_name": _INDICATOR_NAMES[indicator_code],
                    "year": year,
                    "value": value,
                }
            )

    return data_points
