"""World Bank API data fetcher.

Retrieves economic indicator data from the World Bank Data API (v2).
No authentication required - this is a free, public API.

Reference: .github/skills/world-bank-api/SKILL.md
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from shared.country_catalog import MONITORED_COUNTRY_CODES_LOWER

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2"
LIVE_DATE_RANGE = "2010:2024"
WORLD_BANK_SOURCE_ID = "2"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 45
REQUEST_TIMEOUT_ENV_VAR = "WORLD_ANALYST_WORLD_BANK_TIMEOUT_SECONDS"
MAX_ALLOWED_DATA_LAG_YEARS = 1
PUBLIC_API_DELAY_SECONDS = 0.1
WORLD_BANK_SOURCE_NAME = "world_bank_indicators_api"

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

# Canonical monitored-country scope shared with repository metadata and API listing.
TARGET_COUNTRIES = list(MONITORED_COUNTRY_CODES_LOWER)


class WorldBankFetchError(RuntimeError):
    """Raised when the World Bank API does not provide a usable payload."""

    def __init__(
        self,
        message: str,
        indicator_code: str | None = None,
        country_codes: list[str] | None = None,
        run_id: str | None = None,
    ) -> None:
        """Initialise the fetch error with request scope context.

        Args:
            message: Human-readable failure message.
            indicator_code: Requested World Bank indicator code.
            country_codes: Requested ISO2 country codes.
            run_id: Pipeline run identifier when the fetch is pipeline-backed.
        """
        super().__init__(message)
        self.indicator_code = indicator_code
        self.country_codes = country_codes or []
        self.run_id = run_id


@dataclass(frozen=True)
class IndicatorFetchResult:
    """Normalized rows and raw provenance envelope for one indicator request."""

    indicator_code: str
    data_points: list[dict[str, Any]]
    raw_payload: dict[str, Any]
    stale_country_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LiveFetchResult:
    """Normalized rows and raw payload envelopes for one live fetch run."""

    data_points: list[dict[str, Any]]
    raw_payloads: dict[str, dict[str, Any]]
    failures: tuple[WorldBankFetchError, ...] = ()


def fetch_indicator(
    indicator_code: str,
    country_codes: list[str] | None = None,
    date_range: str = LIVE_DATE_RANGE,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch a single indicator for multiple countries from the World Bank API.

    Uses semicolon-separated country codes for batch requests (one API call).
    Implements exponential backoff on failure.

    Args:
        indicator_code: World Bank indicator code (e.g., 'NY.GDP.MKTP.CD').
        country_codes: List of ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Year range string (e.g., '2010:2024').
        retries: Number of retry attempts on failure.

    Returns:
        List of data point dicts with country, year, and value.
        Null values are filtered out.

    Raises:
        requests.HTTPError: If the API returns a non-200 response after retries.
        ValueError: If the API returns an error message in the response body.
    """
    return fetch_indicator_result(
        indicator_code=indicator_code,
        country_codes=country_codes,
        date_range=date_range,
        retries=retries,
    ).data_points


def fetch_indicator_result(
    indicator_code: str,
    country_codes: list[str] | None = None,
    date_range: str = LIVE_DATE_RANGE,
    retries: int = 3,
    run_id: str | None = None,
) -> IndicatorFetchResult:
    """Fetch one indicator and preserve the raw API payload for archival.

    Args:
        indicator_code: World Bank indicator code.
        country_codes: ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Inclusive year range used for the request.
        retries: Number of retry attempts for transport failures.
        run_id: Pipeline run identifier when called from the pipeline.

    Returns:
        Normalized data points and the raw request-response envelope.

    Raises:
        WorldBankFetchError: If the API request fails or returns a payload-level error.
    """
    normalized_country_codes = _normalize_country_codes(country_codes)
    countries = ";".join(country_code.lower() for country_code in normalized_country_codes)
    url = f"{BASE_URL}/country/{countries}/indicator/{indicator_code}"
    request_timeout_seconds = _resolve_request_timeout_seconds()

    # Pin monitored runtime fetches to WDI so indicator lookups stay deterministic across sources.
    params = {
        "format": "json",
        "date": date_range,
        "per_page": 1000,
        "source": WORLD_BANK_SOURCE_ID,
    }

    for attempt in range(retries):
        try:
            logger.info(
                "Fetching %s for %d countries (attempt %d)",
                indicator_code,
                len(normalized_country_codes),
                attempt + 1,
            )
            response = requests.get(url, params=params, timeout=request_timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            metadata, entries = _parse_indicator_payload(
                payload=payload,
                indicator_code=indicator_code,
                country_codes=normalized_country_codes,
                run_id=run_id,
            )
            data_points = _normalize_indicator_entries(
                entries=entries,
                indicator_code=indicator_code,
                date_range=date_range,
                metadata=metadata,
            )
            data_points, stale_country_codes = _filter_stale_country_series(
                data_points=data_points,
                indicator_code=indicator_code,
                date_range=date_range,
            )
            logger.info(
                "Retrieved %d usable data points for %s",
                len(data_points),
                indicator_code,
            )
            return IndicatorFetchResult(
                indicator_code=indicator_code,
                data_points=data_points,
                raw_payload=_build_raw_payload_envelope(
                    response=response,
                    payload=payload,
                    params=params,
                    metadata=metadata,
                    indicator_code=indicator_code,
                    country_codes=normalized_country_codes,
                    date_range=date_range,
                ),
                stale_country_codes=tuple(stale_country_codes),
            )
        except WorldBankFetchError:
            raise
        except requests.RequestException as exc:
            if attempt < retries - 1:
                wait_seconds = 2**attempt
                logger.warning(
                    "Retry %d for %s: %s (waiting %ds)",
                    attempt + 1,
                    indicator_code,
                    exc,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue
            raise _build_fetch_error(
                message=f"World Bank request failed after {retries} attempts: {exc}",
                indicator_code=indicator_code,
                country_codes=normalized_country_codes,
                run_id=run_id,
            ) from exc
        except ValueError as exc:
            raise _build_fetch_error(
                message=f"World Bank returned a non-JSON payload: {exc}",
                indicator_code=indicator_code,
                country_codes=normalized_country_codes,
                run_id=run_id,
            ) from exc

    raise AssertionError("fetch_indicator_result exhausted retries without returning")


def fetch_all_indicator_results(
    country_codes: list[str] | None = None,
    date_range: str = LIVE_DATE_RANGE,
    run_id: str | None = None,
) -> dict[str, IndicatorFetchResult]:
    """Fetch all configured indicators and retain raw payload envelopes.

    Args:
        country_codes: List of ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Inclusive year range used for every request.
        run_id: Pipeline run identifier when called from the pipeline.

    Returns:
        Dict mapping indicator code to normalized rows and raw envelope.
    """
    if country_codes is None:
        country_codes = TARGET_COUNTRIES

    indicator_results: dict[str, IndicatorFetchResult] = {}
    for indicator_code in INDICATORS:
        indicator_results[indicator_code] = fetch_indicator_result(
            indicator_code=indicator_code,
            country_codes=country_codes,
            date_range=date_range,
            run_id=run_id,
        )
        time.sleep(PUBLIC_API_DELAY_SECONDS)

    return indicator_results


def fetch_all_indicators(
    country_codes: list[str] | None = None,
    date_range: str = LIVE_DATE_RANGE,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch all configured indicators for the target countries.

    Makes one API call per indicator across the monitored live panel.
    Includes a 0.1s delay between calls to respect the public API.

    Args:
        country_codes: List of ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Year range string.

    Returns:
        Dict mapping indicator_code → list of data point dicts.
    """
    indicator_results = fetch_all_indicator_results(
        country_codes=country_codes,
        date_range=date_range,
    )
    all_data = {
        indicator_code: result.data_points
        for indicator_code, result in indicator_results.items()
    }

    total_points = sum(len(v) for v in all_data.values())
    logger.info(
        "Fetch complete: %d indicators, %d total data points",
        len(all_data),
        total_points,
    )
    return all_data


def fetch_live_data(
    country_codes: list[str] | None = None,
    date_range: str = LIVE_DATE_RANGE,
    run_id: str | None = None,
) -> LiveFetchResult:
    """Fetch the live World Bank slice used by the pipeline.

    Args:
        country_codes: ISO2 country codes. Defaults to TARGET_COUNTRIES.
        date_range: Inclusive year range used for every request.
        run_id: Pipeline run identifier when called from the pipeline.

    Returns:
        Flattened normalized rows and run-scoped raw payload envelopes.
    """
    raw_payloads: dict[str, dict[str, Any]] = {}
    data_points: list[dict[str, Any]] = []
    failures: list[WorldBankFetchError] = []
    normalized_country_codes = _normalize_country_codes(country_codes)
    for indicator_code in INDICATORS:
        try:
            result = fetch_indicator_result(
                indicator_code=indicator_code,
                country_codes=normalized_country_codes,
                date_range=date_range,
                run_id=run_id,
            )
            raw_payloads[indicator_code] = result.raw_payload
            data_points.extend(result.data_points)
            if not result.data_points:
                failures.append(
                    _build_fetch_error(
                        message="World Bank returned no usable rows for the configured live indicator",
                        indicator_code=indicator_code,
                        country_codes=normalized_country_codes,
                        run_id=run_id,
                    )
                )
            else:
                missing_country_codes = _find_missing_country_codes(
                    data_points=result.data_points,
                    requested_country_codes=normalized_country_codes,
                )
                stale_country_codes = _order_country_codes(
                    requested_country_codes=normalized_country_codes,
                    scoped_country_codes=list(result.stale_country_codes),
                )
                missing_only_country_codes = [
                    country_code
                    for country_code in missing_country_codes
                    if country_code not in stale_country_codes
                ]
                if missing_only_country_codes or stale_country_codes:
                    failures.append(
                        _build_fetch_error(
                            message=_build_indicator_coverage_gap_message(
                                requested_country_codes=normalized_country_codes,
                                missing_country_codes=missing_only_country_codes,
                                stale_country_codes=stale_country_codes,
                            ),
                            indicator_code=indicator_code,
                            country_codes=missing_only_country_codes + stale_country_codes,
                            run_id=run_id,
                        )
                    )
        except WorldBankFetchError as exc:
            failures.append(exc)
        finally:
            time.sleep(PUBLIC_API_DELAY_SECONDS)

    logger.info(
        "Live fetch complete: %d indicators, %d total usable data points, %d failures",
        len(raw_payloads),
        len(data_points),
        len(failures),
    )
    return LiveFetchResult(
        data_points=data_points,
        raw_payloads=raw_payloads,
        failures=tuple(failures),
    )


def _normalize_country_codes(country_codes: list[str] | None) -> list[str]:
    """Normalize one requested country-code list to uppercase unique ISO2 codes.

    Args:
        country_codes: Optional requested ISO2 country codes.

    Returns:
        Uppercase ISO2 country codes in request order.
    """
    requested_country_codes = country_codes or TARGET_COUNTRIES
    normalized_country_codes: list[str] = []
    for country_code in requested_country_codes:
        normalized_country_code = country_code.upper()
        if normalized_country_code not in normalized_country_codes:
            normalized_country_codes.append(normalized_country_code)
    return normalized_country_codes


def _find_missing_country_codes(
    data_points: list[dict[str, Any]],
    requested_country_codes: list[str],
) -> list[str]:
    """Return requested countries that produced no usable rows for one indicator.

    Args:
        data_points: Normalized usable rows for one indicator request.
        requested_country_codes: Country codes requested from the World Bank API.

    Returns:
        Requested country codes missing from the usable result set.
    """
    returned_country_codes = {
        str(data_point.get("country_code", "")).upper()
        for data_point in data_points
        if data_point.get("country_code")
    }
    return [
        country_code
        for country_code in requested_country_codes
        if country_code not in returned_country_codes
    ]


def _order_country_codes(
    requested_country_codes: list[str],
    scoped_country_codes: list[str],
) -> list[str]:
    """Return one scoped country list in the original request order."""
    scoped_country_code_set = {country_code.upper() for country_code in scoped_country_codes}
    return [
        country_code
        for country_code in requested_country_codes
        if country_code in scoped_country_code_set
    ]


def _build_indicator_coverage_gap_message(
    requested_country_codes: list[str],
    missing_country_codes: list[str],
    stale_country_codes: list[str],
) -> str:
    """Describe one incomplete live indicator response with missing and stale scope."""
    usable_country_count = (
        len(requested_country_codes) - len(missing_country_codes) - len(stale_country_codes)
    )
    message_parts = [
        "World Bank returned usable rows for "
        f"{usable_country_count} of {len(requested_country_codes)} requested countries"
    ]
    if missing_country_codes:
        message_parts.append(f"missing countries: {', '.join(missing_country_codes)}")
    if stale_country_codes:
        message_parts.append(f"stale countries: {', '.join(stale_country_codes)}")
    return "; ".join(message_parts)


def _parse_indicator_payload(
    payload: Any,
    indicator_code: str,
    country_codes: list[str],
    run_id: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate the World Bank payload structure for one indicator request.

    Args:
        payload: Decoded JSON payload.
        indicator_code: World Bank indicator code.
        country_codes: ISO2 country codes in scope.
        run_id: Pipeline run identifier when available.

    Returns:
        Metadata dict and raw row list.

    Raises:
        WorldBankFetchError: If the payload shape is invalid or contains an API error.
    """
    if not isinstance(payload, list) or not payload:
        raise _build_fetch_error(
            message=f"Unexpected World Bank response shape: {type(payload)}",
            indicator_code=indicator_code,
            country_codes=country_codes,
            run_id=run_id,
        )

    payload_error = _extract_payload_error(payload)
    if payload_error:
        raise _build_fetch_error(
            message=f"World Bank API payload error: {payload_error}",
            indicator_code=indicator_code,
            country_codes=country_codes,
            run_id=run_id,
        )

    metadata = payload[0] if isinstance(payload[0], dict) else {}
    metadata_source_id = metadata.get("sourceid")
    if metadata_source_id is not None and str(metadata_source_id) != WORLD_BANK_SOURCE_ID:
        raise _build_fetch_error(
            message=(
                "World Bank returned an unexpected data source "
                f"sourceid={metadata_source_id}; expected sourceid={WORLD_BANK_SOURCE_ID}"
            ),
            indicator_code=indicator_code,
            country_codes=country_codes,
            run_id=run_id,
        )

    total_pages = _coerce_metadata_int(metadata.get("pages"))
    # The monitored live scope should fit into one page at per_page=1000. Fail loudly if that changes.
    if total_pages is not None and total_pages > 1:
        raise _build_fetch_error(
            message=(
                f"World Bank response spanned {total_pages} pages; "
                "the current live fetcher fails loudly rather than truncating multi-page "
                "indicator payloads"
            ),
            indicator_code=indicator_code,
            country_codes=country_codes,
            run_id=run_id,
        )

    if len(payload) < 2 or payload[1] is None:
        logger.warning("No raw data rows returned for %s", indicator_code)
        return metadata, []

    if not isinstance(payload[1], list):
        raise _build_fetch_error(
            message=f"Unexpected World Bank data element type: {type(payload[1])}",
            indicator_code=indicator_code,
            country_codes=country_codes,
            run_id=run_id,
        )

    return metadata, payload[1]


def _normalize_indicator_entries(
    entries: list[dict[str, Any]],
    indicator_code: str,
    date_range: str,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """Normalize usable World Bank rows into the stable pipeline shape.

    Args:
        entries: Raw World Bank entries for one indicator request.
        indicator_code: World Bank indicator code.
        date_range: Inclusive year range used for the request.
        metadata: Response metadata from the World Bank API.

    Returns:
        Normalized data points with unusable rows removed.
    """
    normalized_entries: list[dict[str, Any]] = []
    skipped_rows = 0
    for entry in entries:
        normalized_entry = _normalize_indicator_entry(
            entry=entry,
            indicator_code=indicator_code,
            date_range=date_range,
            metadata=metadata,
        )
        if normalized_entry is None:
            skipped_rows += 1
            continue
        normalized_entries.append(normalized_entry)

    if skipped_rows:
        logger.info("Skipped %d null or unusable rows for %s", skipped_rows, indicator_code)

    normalized_entries.sort(key=lambda item: (item["country_code"], item["year"]))
    return normalized_entries


def _filter_stale_country_series(
    data_points: list[dict[str, Any]],
    indicator_code: str,
    date_range: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Remove stale country-indicator series from one live indicator result.

    Annual live series can lag the requested end year by one year. Older tails are
    treated as unavailable coverage and excluded before downstream analysis.
    """
    minimum_usable_year = _resolve_minimum_usable_year(date_range)
    if minimum_usable_year is None:
        return data_points, []

    latest_year_by_country: dict[str, int] = {}
    for data_point in data_points:
        country_code = data_point["country_code"]
        latest_year_by_country[country_code] = max(
            data_point["year"],
            latest_year_by_country.get(country_code, data_point["year"]),
        )

    stale_country_codes = sorted(
        country_code
        for country_code, latest_year in latest_year_by_country.items()
        if latest_year < minimum_usable_year
    )
    if not stale_country_codes:
        return data_points, []

    logger.warning(
        "Dropped stale %s series for %s because their latest usable year was older than %d: %s",
        len(stale_country_codes),
        indicator_code,
        minimum_usable_year,
        ", ".join(stale_country_codes),
    )
    stale_country_code_set = set(stale_country_codes)
    return [
        data_point
        for data_point in data_points
        if data_point["country_code"] not in stale_country_code_set
    ], stale_country_codes


def _normalize_indicator_entry(
    entry: dict[str, Any],
    indicator_code: str,
    date_range: str,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    """Convert one raw World Bank entry into the pipeline data shape.

    Args:
        entry: Raw World Bank row.
        indicator_code: World Bank indicator code.
        date_range: Inclusive year range used for the request.
        metadata: Response metadata from the World Bank API.

    Returns:
        Normalized row or None when the source row is unusable.
    """
    raw_value = entry.get("value")
    if raw_value is None:
        return None

    country = entry.get("country")
    if not isinstance(country, dict):
        return None

    country_code = str(country.get("id", "")).upper()
    country_name = str(country.get("value", "")).strip()
    if not country_code or not country_name:
        return None

    try:
        year = int(entry["date"])
        numeric_value = float(raw_value)
    except (KeyError, TypeError, ValueError):
        return None

    if not math.isfinite(numeric_value):
        return None

    return {
        "country_code": country_code,
        "country_name": country_name,
        "country_iso3": entry.get("countryiso3code", ""),
        "indicator_code": indicator_code,
        "indicator_name": INDICATORS.get(indicator_code, indicator_code),
        "year": year,
        "value": numeric_value,
        "source_name": WORLD_BANK_SOURCE_NAME,
        "source_date_range": date_range,
        "source_last_updated": metadata.get("lastupdated"),
        "source_id": metadata.get("sourceid"),
    }


def _build_raw_payload_envelope(
    response: requests.Response,
    payload: Any,
    params: dict[str, Any],
    metadata: dict[str, Any],
    indicator_code: str,
    country_codes: list[str],
    date_range: str,
) -> dict[str, Any]:
    """Build the archival envelope for one live World Bank request.

    Args:
        response: HTTP response object.
        payload: Decoded JSON payload.
        params: Query params used for the request.
        metadata: Response metadata from the World Bank API.
        indicator_code: World Bank indicator code.
        country_codes: ISO2 country codes in scope.
        date_range: Inclusive year range used for the request.

    Returns:
        JSON-serialisable request-response envelope.
    """
    return {
        "source_name": WORLD_BANK_SOURCE_NAME,
        "source_date_range": date_range,
        "source_last_updated": metadata.get("lastupdated"),
        "source_id": metadata.get("sourceid"),
        "indicator_code": indicator_code,
        "indicator_name": INDICATORS.get(indicator_code, indicator_code),
        "country_codes": list(country_codes),
        "request": {
            "url": response.url,
            "params": dict(params),
        },
        "http_status": response.status_code,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "response_metadata": metadata,
        "response_body": payload,
    }


def _extract_payload_error(payload: list[Any]) -> str | None:
    """Extract the World Bank logical API error from an HTTP 200 payload.

    Args:
        payload: Decoded JSON response payload.

    Returns:
        Human-readable error message when present.
    """
    first_item = payload[0] if payload else None
    if not isinstance(first_item, dict) or "message" not in first_item:
        return None

    messages = first_item["message"]
    if not isinstance(messages, list):
        return str(messages)

    parts: list[str] = []
    for message in messages:
        if isinstance(message, dict):
            key = message.get("key")
            value = message.get("value")
            if key and value:
                parts.append(f"{key}: {value}")
            elif value:
                parts.append(str(value))
            elif key:
                parts.append(str(key))
            else:
                parts.append(str(message))
            continue
        parts.append(str(message))
    return "; ".join(parts)


def _build_fetch_error(
    message: str,
    indicator_code: str,
    country_codes: list[str],
    run_id: str | None,
) -> WorldBankFetchError:
    """Construct a scoped fetch error with run and request context.

    Args:
        message: Human-readable failure message.
        indicator_code: World Bank indicator code.
        country_codes: ISO2 country codes in scope.
        run_id: Pipeline run identifier when available.

    Returns:
        Scoped fetch error ready to raise.
    """
    scope_parts = []
    if run_id:
        scope_parts.append(f"run_id={run_id}")
    scope_parts.append(f"indicator_code={indicator_code}")
    if country_codes:
        scope_parts.append(f"country_codes={','.join(country_codes)}")
    scoped_message = f"{' '.join(scope_parts)}: {message}"
    return WorldBankFetchError(
        message=scoped_message,
        indicator_code=indicator_code,
        country_codes=country_codes,
        run_id=run_id,
    )


def _resolve_request_timeout_seconds() -> int:
    """Resolve the configured World Bank request timeout.

    Returns:
        Positive timeout in seconds.
    """
    configured_timeout = os.environ.get(REQUEST_TIMEOUT_ENV_VAR, "").strip()
    if not configured_timeout:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS

    try:
        timeout_seconds = int(configured_timeout)
    except ValueError:
        logger.warning(
            "%s=%r is invalid; falling back to %ds",
            REQUEST_TIMEOUT_ENV_VAR,
            configured_timeout,
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        )
        return DEFAULT_REQUEST_TIMEOUT_SECONDS

    if timeout_seconds <= 0:
        logger.warning(
            "%s=%r must be positive; falling back to %ds",
            REQUEST_TIMEOUT_ENV_VAR,
            configured_timeout,
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        )
        return DEFAULT_REQUEST_TIMEOUT_SECONDS

    return timeout_seconds


def _resolve_minimum_usable_year(date_range: str) -> int | None:
    """Resolve the minimum acceptable latest year for one annual live series."""
    raw_end_year = date_range.split(":")[-1].strip()
    if not raw_end_year:
        return None

    try:
        return int(raw_end_year) - MAX_ALLOWED_DATA_LAG_YEARS
    except ValueError:
        logger.warning("Could not parse a usable end year from date_range=%r", date_range)
        return None


def _coerce_metadata_int(value: Any) -> int | None:
    """Convert one World Bank metadata field to an integer when possible.

    Args:
        value: Metadata field value from the World Bank response.

    Returns:
        Parsed integer, or None when the value is absent or invalid.
    """
    if value in {None, ""}:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
