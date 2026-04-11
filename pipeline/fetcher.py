"""World Bank API data fetcher.

Retrieves economic indicator data from the World Bank Data API (v2).
No authentication required — this is a free, public API.

Reference: .github/skills/world-bank-api/SKILL.md
"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2"

# Core indicators for the economic intelligence dashboard.
# All verified against live World Bank API — April 2026.
# See .github/skills/world-bank-api/SKILL.md for full reference.
INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of total labor force)",
    "BN.CAB.XOKA.GD.ZS": "Current account balance (% of GDP)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt, total (% of GDP)",
}

# 15 countries: ML6 office markets + geographic/economic diversity.
# All ISO2 codes verified against World Bank API.
TARGET_COUNTRIES = [
    "be", "nl", "de", "gb", "fr",  # Europe (ML6 markets)
    "us", "br", "ca",               # Americas
    "cn", "jp", "in", "au",         # Asia-Pacific
    "za", "ng", "eg",               # Africa / MENA
]


def fetch_indicator(
    indicator_code: str,
    country_codes: list[str] | None = None,
    date_range: str = "2017:2023",
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch a single indicator for multiple countries from the World Bank API.

    Uses semicolon-separated country codes for batch requests (one API call).
    Implements exponential backoff on failure.

    Args:
        indicator_code: World Bank indicator code (e.g., 'NY.GDP.MKTP.CD').
        country_codes: List of ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Year range string (e.g., '2017:2023').
        retries: Number of retry attempts on failure.

    Returns:
        List of data point dicts with country, year, and value.
        Null values are filtered out.

    Raises:
        requests.HTTPError: If the API returns a non-200 response after retries.
        ValueError: If the API returns an error message in the response body.
    """
    if country_codes is None:
        country_codes = TARGET_COUNTRIES

    countries = ";".join(country_codes)
    url = f"{BASE_URL}/country/{countries}/indicator/{indicator_code}"

    params = {
        "format": "json",
        "date": date_range,
        "per_page": 1000,
    }

    for attempt in range(retries):
        try:
            logger.info(
                "Fetching %s for %d countries (attempt %d)",
                indicator_code,
                len(country_codes),
                attempt + 1,
            )
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            # World Bank API returns HTTP 200 even for errors.
            # Errors are 1-element arrays: [{"message": [...]}]
            # Success is 2-element: [metadata, data_array]
            if not isinstance(data, list):
                raise ValueError(f"Unexpected response type: {type(data)}")

            if len(data) < 2 or data[1] is None:
                if isinstance(data[0], dict) and "message" in data[0]:
                    raise ValueError(f"API error: {data[0]['message']}")
                logger.warning("No data returned for %s", indicator_code)
                return []

            results = []
            for entry in data[1]:
                if entry.get("value") is not None:
                    results.append({
                        "country_code": entry["country"]["id"].upper(),
                        "country_name": entry["country"]["value"],
                        "country_iso3": entry.get("countryiso3code", ""),
                        "indicator_code": indicator_code,
                        "indicator_name": INDICATORS.get(
                            indicator_code, indicator_code
                        ),
                        "year": int(entry["date"]),
                        "value": float(entry["value"]),
                    })

            logger.info(
                "Retrieved %d data points for %s",
                len(results),
                indicator_code,
            )
            return results

        except requests.RequestException as exc:
            if attempt < retries - 1:
                wait = 2**attempt
                logger.warning(
                    "Retry %d for %s: %s (waiting %ds)",
                    attempt + 1,
                    indicator_code,
                    exc,
                    wait,
                )
                time.sleep(wait)
            else:
                raise

    return []


def fetch_all_indicators(
    country_codes: list[str] | None = None,
    date_range: str = "2017:2023",
) -> dict[str, list[dict[str, Any]]]:
    """Fetch all configured indicators for the target countries.

    Makes one API call per indicator (6 calls total for 15 countries).
    Includes a 0.1s delay between calls to respect the public API.

    Args:
        country_codes: List of ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Year range string.

    Returns:
        Dict mapping indicator_code → list of data point dicts.
    """
    if country_codes is None:
        country_codes = TARGET_COUNTRIES

    all_data: dict[str, list[dict[str, Any]]] = {}

    for indicator_code in INDICATORS:
        all_data[indicator_code] = fetch_indicator(
            indicator_code=indicator_code,
            country_codes=country_codes,
            date_range=date_range,
        )
        time.sleep(0.1)  # Respect the public API

    total_points = sum(len(v) for v in all_data.values())
    logger.info(
        "Fetch complete: %d indicators, %d total data points",
        len(all_data),
        total_points,
    )
    return all_data
