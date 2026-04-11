"""Assess which countries are feasible for the live World Analyst indicator set.

This utility queries the World Bank API directly, measures year-by-year availability
for the approved indicator set, and scores countries against both freshness and
history-depth rules.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import requests

from pipeline.fetcher import (
    BASE_URL,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    INDICATORS,
    MAX_ALLOWED_DATA_LAG_YEARS,
    PUBLIC_API_DELAY_SECONDS,
    REQUEST_TIMEOUT_ENV_VAR,
    WORLD_BANK_SOURCE_ID,
)
from shared.country_catalog import MONITORED_COUNTRY_CODES

logger = logging.getLogger(__name__)

COUNTRY_LIST_PER_PAGE = 400
DEFAULT_COUNTRY_BATCH_SIZE = 50


@dataclass(frozen=True)
class CountryCandidate:
    """World Bank country metadata used for feasibility scoring."""

    code: str
    iso3: str
    name: str
    region: str
    income_level: str
    is_currently_monitored: bool = False


@dataclass(frozen=True)
class CountryFeasibility:
    """Coverage and freshness summary for one country."""

    candidate: CountryCandidate
    latest_year_by_indicator: dict[str, int | None]
    coverage_by_target_year: dict[int, int]
    consecutive_complete_years_by_target: dict[int, int]


def default_target_end_years(reference_year: int | None = None) -> tuple[int, ...]:
    """Return the default end years to compare for annual-data feasibility.

    Args:
        reference_year: Optional year override for deterministic tests.

    Returns:
        Tuple of descending target end years.
    """
    current_year = reference_year or datetime.now(timezone.utc).year
    return tuple(current_year - offset for offset in range(1, 4))


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the feasibility utility.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Score World Bank countries by live-data feasibility for the approved "
            "World Analyst indicator set."
        )
    )
    parser.add_argument(
        "--start-year",
        type=int,
        help=(
            "Earliest annual observation to request from the World Bank API. When omitted, "
            "the scan requests enough history to evaluate the maximum history threshold."
        ),
    )
    parser.add_argument(
        "--target-end-year",
        dest="target_end_years",
        action="append",
        type=int,
        help=(
            "Target end year to score against. Repeat to compare multiple end years. "
            "Defaults to current_year-1, current_year-2, and current_year-3."
        ),
    )
    parser.add_argument(
        "--minimum-history-years",
        type=int,
        default=5,
        help="Smallest consecutive full-history threshold to report.",
    )
    parser.add_argument(
        "--maximum-history-years",
        type=int,
        default=15,
        help="Largest consecutive full-history threshold to report.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        help=(
            "Optional request timeout override. Defaults to the shared World Bank timeout "
            f"environment variable {REQUEST_TIMEOUT_ENV_VAR} when set, otherwise "
            f"{DEFAULT_REQUEST_TIMEOUT_SECONDS}."
        ),
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of retry attempts for transient HTTP failures.",
    )
    parser.add_argument(
        "--country-batch-size",
        type=int,
        default=DEFAULT_COUNTRY_BATCH_SIZE,
        help="Number of country codes to include in each batched indicator request.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of ranked countries to print in the report.",
    )
    parser.add_argument(
        "--minimum-country-count",
        type=int,
        default=len(MONITORED_COUNTRY_CODES),
        help=(
            "Minimum number of fully covered countries required when identifying the "
            "highest practical target end year."
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        help="Optional path for writing the full feasibility table as CSV.",
    )
    return parser


def fetch_candidate_countries(
    session: requests.Session,
    timeout_seconds: int,
    retries: int,
) -> list[CountryCandidate]:
    """Fetch the World Bank country catalog and keep only real country rows.

    Args:
        session: Requests session used for HTTP calls.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Sorted list of country candidates.
    """
    payload = request_json_with_retries(
        session=session,
        url=f"{BASE_URL}/country",
        params={"format": "json", "per_page": COUNTRY_LIST_PER_PAGE},
        timeout_seconds=timeout_seconds,
        retries=retries,
        request_name="country catalog",
    )
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("World Bank /country response did not contain metadata and rows")
    return parse_country_candidates(payload[1])


def parse_country_candidates(rows: Sequence[dict[str, Any]]) -> list[CountryCandidate]:
    """Parse real-country candidates from the World Bank country catalog rows.

    Aggregates are represented in the catalog but have region id `NA`. Those rows do
    not make sense for a country feasibility shortlist, so they are excluded.

    Args:
        rows: World Bank country catalog rows.

    Returns:
        Sorted list of parsed country candidates.
    """
    candidates: list[CountryCandidate] = []
    monitored_codes = set(MONITORED_COUNTRY_CODES)
    for row in rows:
        region_id = str(row.get("region", {}).get("id", "")).upper()
        code = str(row.get("iso2Code", "")).upper()
        iso3 = str(row.get("id", "")).upper()
        if region_id == "NA" or len(code) != 2 or len(iso3) != 3:
            continue
        candidates.append(
            CountryCandidate(
                code=code,
                iso3=iso3,
                name=str(row.get("name", "")).strip(),
                region=str(row.get("region", {}).get("value", "")).strip(),
                income_level=str(row.get("incomeLevel", {}).get("value", "")).strip(),
                is_currently_monitored=code in monitored_codes,
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.name)


def fetch_latest_years_by_indicator(
    session: requests.Session,
    countries: Sequence[CountryCandidate],
    start_year: int,
    end_year: int,
    retries: int,
    country_batch_size: int = DEFAULT_COUNTRY_BATCH_SIZE,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, dict[str, int | None]]:
    """Fetch the latest non-null year per country for each approved indicator.

    Args:
        session: Requests session used for HTTP calls.
        countries: Country candidates to score.
        start_year: Earliest requested annual year.
        end_year: Latest requested annual year.
        country_batch_size: Number of countries per batched request.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Mapping of indicator code to `{country_code: latest_non_null_year}`.
    """
    latest_years_by_indicator: dict[str, dict[str, int | None]] = {}
    country_codes = [country.code for country in countries]
    for indicator_code in INDICATORS:
        latest_years_by_indicator[indicator_code] = fetch_latest_non_null_years(
            session=session,
            indicator_code=indicator_code,
            country_codes=country_codes,
            start_year=start_year,
            end_year=end_year,
            retries=retries,
            country_batch_size=country_batch_size,
            timeout_seconds=timeout_seconds,
        )
    return latest_years_by_indicator


def fetch_available_years_by_indicator(
    session: requests.Session,
    countries: Sequence[CountryCandidate],
    start_year: int,
    end_year: int,
    retries: int,
    country_batch_size: int = DEFAULT_COUNTRY_BATCH_SIZE,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, dict[str, tuple[int, ...]]]:
    """Fetch all non-null annual years per country for each approved indicator.

    Args:
        session: Requests session used for HTTP calls.
        countries: Country candidates to score.
        start_year: Earliest requested annual year.
        end_year: Latest requested annual year.
        retries: Number of retry attempts for transient HTTP failures.
        country_batch_size: Number of countries per batched request.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Mapping of indicator code to `{country_code: sorted_non_null_years}`.
    """
    available_years_by_indicator: dict[str, dict[str, tuple[int, ...]]] = {}
    country_codes = [country.code for country in countries]
    for indicator_code in INDICATORS:
        available_years_by_indicator[indicator_code] = fetch_available_non_null_years(
            session=session,
            indicator_code=indicator_code,
            country_codes=country_codes,
            start_year=start_year,
            end_year=end_year,
            retries=retries,
            country_batch_size=country_batch_size,
            timeout_seconds=timeout_seconds,
        )
    return available_years_by_indicator


def fetch_latest_non_null_years(
    session: requests.Session,
    indicator_code: str,
    country_codes: Sequence[str],
    start_year: int,
    end_year: int,
    retries: int,
    country_batch_size: int = DEFAULT_COUNTRY_BATCH_SIZE,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, int | None]:
    """Fetch the latest non-null year for one indicator across many countries.

    Args:
        session: Requests session used for HTTP calls.
        indicator_code: World Bank indicator code.
        country_codes: ISO2 country codes to request.
        start_year: Earliest requested annual year.
        end_year: Latest requested annual year.
        country_batch_size: Number of countries per batched request.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Mapping of country code to latest non-null year, or `None` when unavailable.
    """
    latest_years = {country_code: None for country_code in country_codes}
    for batched_country_codes in batched(country_codes, country_batch_size):
        country_scope = ";".join(country_code.lower() for country_code in batched_country_codes)
        payload = request_json_with_retries(
            session=session,
            url=f"{BASE_URL}/country/{country_scope}/indicator/{indicator_code}",
            params={
                "format": "json",
                "date": f"{start_year}:{end_year}",
                "per_page": 1000,
                "source": WORLD_BANK_SOURCE_ID,
            },
            timeout_seconds=timeout_seconds,
            retries=retries,
            request_name=(
                f"indicator {indicator_code} country batch "
                f"{','.join(batched_country_codes)}"
            ),
        )
        metadata, rows = parse_indicator_payload(payload)
        page_count = int(metadata.get("pages", 1))
        if page_count > 1:
            raise ValueError(
                f"Indicator {indicator_code} returned {page_count} pages for batch size "
                f"{country_batch_size}; reduce the batch size."
            )
        for row in rows:
            value = row.get("value")
            if value is None:
                continue
            country_code = str(row.get("country", {}).get("id", "")).upper()
            year = parse_year(row.get("date"))
            if country_code not in latest_years or year is None:
                continue
            if latest_years[country_code] is None or year > int(latest_years[country_code]):
                latest_years[country_code] = year

        # Stay polite with the public API when iterating through the full country set.
        time.sleep(PUBLIC_API_DELAY_SECONDS)
    return latest_years


def fetch_available_non_null_years(
    session: requests.Session,
    indicator_code: str,
    country_codes: Sequence[str],
    start_year: int,
    end_year: int,
    retries: int,
    country_batch_size: int = DEFAULT_COUNTRY_BATCH_SIZE,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, tuple[int, ...]]:
    """Fetch every non-null annual year for one indicator across many countries.

    Args:
        session: Requests session used for HTTP calls.
        indicator_code: World Bank indicator code.
        country_codes: ISO2 country codes to request.
        start_year: Earliest requested annual year.
        end_year: Latest requested annual year.
        retries: Number of retry attempts for transient HTTP failures.
        country_batch_size: Number of countries per batched request.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Mapping of country code to sorted tuple of non-null years.
    """
    available_years = {country_code: set() for country_code in country_codes}
    for batched_country_codes in batched(country_codes, country_batch_size):
        country_scope = ";".join(country_code.lower() for country_code in batched_country_codes)
        payload = request_json_with_retries(
            session=session,
            url=f"{BASE_URL}/country/{country_scope}/indicator/{indicator_code}",
            params={
                "format": "json",
                "date": f"{start_year}:{end_year}",
                "per_page": 1000,
                "source": WORLD_BANK_SOURCE_ID,
            },
            timeout_seconds=timeout_seconds,
            retries=retries,
            request_name=(
                f"indicator {indicator_code} country batch "
                f"{','.join(batched_country_codes)}"
            ),
        )
        metadata, rows = parse_indicator_payload(payload)
        page_count = int(metadata.get("pages", 1))
        if page_count > 1:
            raise ValueError(
                f"Indicator {indicator_code} returned {page_count} pages for batch size "
                f"{country_batch_size}; reduce the batch size."
            )
        for row in rows:
            value = row.get("value")
            if value is None:
                continue
            country_code = str(row.get("country", {}).get("id", "")).upper()
            year = parse_year(row.get("date"))
            if country_code not in available_years or year is None:
                continue
            available_years[country_code].add(year)

        # Stay polite with the public API when iterating through the full country set.
        time.sleep(PUBLIC_API_DELAY_SECONDS)

    return {
        country_code: tuple(sorted(country_years))
        for country_code, country_years in available_years.items()
    }


def request_json_with_retries(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    timeout_seconds: int,
    retries: int,
    request_name: str,
) -> Any:
    """Request one World Bank JSON payload with retry and exponential backoff.

    Args:
        session: Requests session used for HTTP calls.
        url: Absolute request URL.
        params: Query-string parameters.
        timeout_seconds: Request timeout in seconds.
        retries: Number of retry attempts.
        request_name: Human-readable request label for logs and errors.

    Returns:
        Decoded JSON payload.
    """
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = session.get(url, params=params, timeout=timeout_seconds)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            wait_seconds = 2**attempt
            logger.warning(
                "Retrying %s after HTTP failure on attempt %d/%d: %s",
                request_name,
                attempt + 1,
                retries,
                exc,
            )
            time.sleep(wait_seconds)
    raise RuntimeError(
        f"World Bank request failed for {request_name} after {retries} attempts: {last_error}"
    ) from last_error


def resolve_request_timeout_seconds(timeout_override: int | None = None) -> int:
    """Resolve the request timeout for the feasibility scan.

    Args:
        timeout_override: Optional explicit timeout override.

    Returns:
        Positive timeout in seconds.
    """
    if timeout_override is not None:
        if timeout_override <= 0:
            raise ValueError("timeout_override must be positive")
        return timeout_override

    raw_timeout_seconds = os.getenv(REQUEST_TIMEOUT_ENV_VAR)
    if raw_timeout_seconds is None:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS

    try:
        timeout_seconds = int(raw_timeout_seconds)
    except ValueError as exc:
        raise ValueError(
            f"{REQUEST_TIMEOUT_ENV_VAR} must be an integer, got {raw_timeout_seconds!r}"
        ) from exc

    if timeout_seconds <= 0:
        raise ValueError(f"{REQUEST_TIMEOUT_ENV_VAR} must be positive")
    return timeout_seconds


def parse_indicator_payload(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse one indicator payload from the World Bank API.

    Args:
        payload: Decoded World Bank JSON payload.

    Returns:
        Tuple of metadata dict and list of rows.
    """
    if not isinstance(payload, list) or not payload:
        raise ValueError("World Bank indicator payload was empty or not list-shaped")
    if len(payload) == 1 and isinstance(payload[0], dict) and payload[0].get("message"):
        raise ValueError(f"World Bank payload error: {payload[0]['message']}")
    if len(payload) < 2:
        raise ValueError("World Bank indicator payload did not contain metadata and rows")
    metadata = payload[0]
    rows = payload[1]
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        raise ValueError("World Bank indicator payload had an unexpected shape")
    return metadata, rows


def parse_year(raw_year: Any) -> int | None:
    """Parse a World Bank year string into an integer.

    Args:
        raw_year: Raw year field from the World Bank payload.

    Returns:
        Parsed year, or `None` when parsing fails.
    """
    try:
        return int(raw_year)
    except (TypeError, ValueError):
        return None


def batched(items: Sequence[str], batch_size: int) -> Iterable[Sequence[str]]:
    """Yield fixed-size slices from a sequence.

    Args:
        items: Sequence to batch.
        batch_size: Maximum batch size.

    Yields:
        Consecutive sequence slices.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    for start_index in range(0, len(items), batch_size):
        yield items[start_index : start_index + batch_size]


def build_country_feasibility_rows(
    countries: Sequence[CountryCandidate],
    available_years_by_indicator: dict[str, dict[str, tuple[int, ...]]],
    target_end_years: Sequence[int],
    start_year: int,
    max_allowed_data_lag_years: int = MAX_ALLOWED_DATA_LAG_YEARS,
) -> list[CountryFeasibility]:
    """Build country feasibility rows from year-by-year availability.

    Args:
        countries: Country candidates to score.
        available_years_by_indicator: Non-null year mapping per indicator.
        target_end_years: End years to evaluate.
        start_year: Earliest requested annual year.
        max_allowed_data_lag_years: Freshness tolerance in years.

    Returns:
        Sorted feasibility rows.
    """
    rows: list[CountryFeasibility] = []
    for country in countries:
        country_years_by_indicator = {
            indicator_code: available_years_by_indicator[indicator_code].get(country.code, ())
            for indicator_code in INDICATORS
        }
        latest_year_by_indicator = {
            indicator_code: max(country_years_by_indicator[indicator_code], default=None)
            for indicator_code in INDICATORS
        }
        coverage_by_target_year = {
            target_end_year: count_fresh_indicators(
                latest_year_by_indicator=latest_year_by_indicator,
                target_end_year=target_end_year,
                max_allowed_data_lag_years=max_allowed_data_lag_years,
            )
            for target_end_year in target_end_years
        }
        consecutive_complete_years_by_target = {
            target_end_year: count_consecutive_complete_years(
                available_years_by_indicator=country_years_by_indicator,
                target_end_year=target_end_year,
                start_year=start_year,
            )
            for target_end_year in target_end_years
        }
        rows.append(
            CountryFeasibility(
                candidate=country,
                latest_year_by_indicator=latest_year_by_indicator,
                coverage_by_target_year=coverage_by_target_year,
                consecutive_complete_years_by_target=consecutive_complete_years_by_target,
            )
        )
    return rank_country_feasibility(rows=rows, target_end_years=target_end_years)


def count_consecutive_complete_years(
    available_years_by_indicator: dict[str, Sequence[int]],
    target_end_year: int,
    start_year: int,
) -> int:
    """Count consecutive fully complete years backward from a target end year.

    A year counts only when all approved indicators have a non-null observation for that
    exact country-year. Counting stops at the first missing year.

    Args:
        available_years_by_indicator: Non-null years per indicator for one country.
        target_end_year: End year being evaluated.
        start_year: Earliest requested annual year.

    Returns:
        Number of consecutive complete years ending at `target_end_year`.
    """
    consecutive_years = 0
    year_sets_by_indicator = {
        indicator_code: set(years)
        for indicator_code, years in available_years_by_indicator.items()
    }
    for year in range(target_end_year, start_year - 1, -1):
        if all(year in year_sets_by_indicator[indicator_code] for indicator_code in INDICATORS):
            consecutive_years += 1
            continue
        break
    return consecutive_years


def count_fresh_indicators(
    latest_year_by_indicator: dict[str, int | None],
    target_end_year: int,
    max_allowed_data_lag_years: int = MAX_ALLOWED_DATA_LAG_YEARS,
) -> int:
    """Count how many indicators are fresh enough for a target end year.

    Args:
        latest_year_by_indicator: Latest non-null year per indicator.
        target_end_year: End year being evaluated.
        max_allowed_data_lag_years: Freshness tolerance in years.

    Returns:
        Number of indicators that pass the freshness rule.
    """
    return sum(
        1
        for latest_year in latest_year_by_indicator.values()
        if is_fresh_for_target(
            latest_year=latest_year,
            target_end_year=target_end_year,
            max_allowed_data_lag_years=max_allowed_data_lag_years,
        )
    )


def is_fresh_for_target(
    latest_year: int | None,
    target_end_year: int,
    max_allowed_data_lag_years: int = MAX_ALLOWED_DATA_LAG_YEARS,
) -> bool:
    """Return whether a latest non-null year is fresh enough for a target end year.

    Args:
        latest_year: Latest non-null year for the series.
        target_end_year: End year being evaluated.
        max_allowed_data_lag_years: Freshness tolerance in years.

    Returns:
        True when the series is recent enough to use.
    """
    if latest_year is None:
        return False
    return latest_year >= (target_end_year - max_allowed_data_lag_years)


def rank_country_feasibility(
    rows: Sequence[CountryFeasibility],
    target_end_years: Sequence[int],
) -> list[CountryFeasibility]:
    """Rank countries by coverage quality for the requested target years.

    Args:
        rows: Country feasibility rows.
        target_end_years: End years in descending importance order.

    Returns:
        Ranked feasibility rows.
    """
    primary_target_end_year = max(target_end_years)

    def sort_key(row: CountryFeasibility) -> tuple[Any, ...]:
        coverage_key = tuple(-row.coverage_by_target_year[target_end_year] for target_end_year in target_end_years)
        history_key = (-row.consecutive_complete_years_by_target[primary_target_end_year],)
        latest_key = tuple(
            -(row.latest_year_by_indicator[indicator_code] or 0)
            for indicator_code in INDICATORS
        )
        monitored_bias = (0 if row.candidate.is_currently_monitored else 1,)
        return coverage_key + history_key + latest_key + monitored_bias + (row.candidate.name,)

    return sorted(rows, key=sort_key)


def build_history_threshold_years(
    minimum_history_years: int,
    maximum_history_years: int,
) -> tuple[int, ...]:
    """Build the inclusive range of history thresholds to evaluate.

    Args:
        minimum_history_years: Smallest requested history threshold.
        maximum_history_years: Largest requested history threshold.

    Returns:
        Inclusive ascending tuple of thresholds.
    """
    if minimum_history_years <= 0:
        raise ValueError("minimum_history_years must be positive")
    if maximum_history_years < minimum_history_years:
        raise ValueError("maximum_history_years must be greater than or equal to minimum_history_years")
    return tuple(range(minimum_history_years, maximum_history_years + 1))


def resolve_start_year(
    start_year_override: int | None,
    target_end_years: Sequence[int],
    history_threshold_years: Sequence[int],
) -> int:
    """Resolve the scan start year.

    When the caller does not provide a start year, request enough annual history to
    evaluate the largest history threshold against the primary target year.

    Args:
        start_year_override: Optional explicit start-year override.
        target_end_years: Target end years being evaluated.
        history_threshold_years: History thresholds being reported.

    Returns:
        Earliest requested annual year.
    """
    if start_year_override is not None:
        return start_year_override
    primary_target_end_year = max(target_end_years)
    largest_history_threshold = max(history_threshold_years)
    return primary_target_end_year - largest_history_threshold + 1


def count_countries_meeting_history_threshold(
    rows: Sequence[CountryFeasibility],
    target_end_year: int,
    history_threshold_year: int,
) -> int:
    """Count countries whose complete-history span meets a threshold.

    Args:
        rows: Feasibility rows to inspect.
        target_end_year: End year whose full-history span should be checked.
        history_threshold_year: Minimum consecutive complete years required.

    Returns:
        Number of countries meeting the threshold.
    """
    return sum(
        1
        for row in rows
        if row.consecutive_complete_years_by_target[target_end_year] >= history_threshold_year
    )


def find_highest_practical_target_year(
    rows: Sequence[CountryFeasibility],
    target_end_years: Sequence[int],
    minimum_country_count: int,
) -> int | None:
    """Find the highest target year with enough fully covered countries.

    Args:
        rows: Feasibility rows to inspect.
        target_end_years: Target end years in descending order.
        minimum_country_count: Required number of complete countries.

    Returns:
        Highest target year that satisfies the requirement, or None.
    """
    required_indicator_count = len(INDICATORS)
    for target_end_year in sorted(target_end_years, reverse=True):
        complete_country_count = sum(
            1
            for row in rows
            if row.coverage_by_target_year[target_end_year] == required_indicator_count
        )
        if complete_country_count >= minimum_country_count:
            return target_end_year
    return None


def write_csv_report(
    rows: Sequence[CountryFeasibility],
    target_end_years: Sequence[int],
    history_threshold_years: Sequence[int],
    output_path: Path,
) -> None:
    """Write the feasibility table to CSV.

    Args:
        rows: Ranked feasibility rows.
        target_end_years: Target end years that were scored.
        output_path: CSV output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "code",
        "iso3",
        "name",
        "region",
        "income_level",
        "is_currently_monitored",
    ] + [
        f"coverage_{target_end_year}"
        for target_end_year in target_end_years
    ] + [
        f"consecutive_complete_years_{target_end_year}"
        for target_end_year in target_end_years
    ] + [
        f"latest_{indicator_code}"
        for indicator_code in INDICATORS
    ] + [
        f"meets_history_threshold_{history_threshold_year}"
        for history_threshold_year in history_threshold_years
    ]

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "code": row.candidate.code,
                    "iso3": row.candidate.iso3,
                    "name": row.candidate.name,
                    "region": row.candidate.region,
                    "income_level": row.candidate.income_level,
                    "is_currently_monitored": row.candidate.is_currently_monitored,
                    **{
                        f"coverage_{target_end_year}": row.coverage_by_target_year[target_end_year]
                        for target_end_year in target_end_years
                    },
                    **{
                        f"consecutive_complete_years_{target_end_year}": row.consecutive_complete_years_by_target[target_end_year]
                        for target_end_year in target_end_years
                    },
                    **{
                        f"latest_{indicator_code}": row.latest_year_by_indicator[indicator_code]
                        for indicator_code in INDICATORS
                    },
                    **{
                        f"meets_history_threshold_{history_threshold_year}": (
                            row.consecutive_complete_years_by_target[max(target_end_years)] >= history_threshold_year
                        )
                        for history_threshold_year in history_threshold_years
                    },
                }
            )


def format_report(
    rows: Sequence[CountryFeasibility],
    target_end_years: Sequence[int],
    history_threshold_years: Sequence[int],
    minimum_country_count: int,
    top_n: int,
) -> str:
    """Format the feasibility summary as plain text.

    Args:
        rows: Ranked feasibility rows.
        target_end_years: Target end years that were scored.
        minimum_country_count: Required fully covered country count for the headline.
        top_n: Number of ranked countries to include.

    Returns:
        Multi-line report string.
    """
    lines: list[str] = []
    required_indicator_count = len(INDICATORS)
    primary_target_end_year = max(target_end_years)
    lines.append("World Analyst country feasibility scan")
    lines.append(
        f"Countries scanned: {len(rows)} | Indicators scored: {required_indicator_count} | "
        f"Target end years: {', '.join(str(year) for year in target_end_years)} | "
        f"History thresholds: {history_threshold_years[0]}-{history_threshold_years[-1]} years"
    )

    highest_practical_target_year = find_highest_practical_target_year(
        rows=rows,
        target_end_years=target_end_years,
        minimum_country_count=minimum_country_count,
    )
    if highest_practical_target_year is None:
        lines.append(
            f"Highest practical target year for at least {minimum_country_count} fully covered countries: none"
        )
    else:
        lines.append(
            "Highest practical target year for at least "
            f"{minimum_country_count} fully covered countries: {highest_practical_target_year}"
        )

    lines.append("")
    lines.append("Full-coverage counts by target year")
    for target_end_year in target_end_years:
        full_coverage_count = sum(
            1
            for row in rows
            if row.coverage_by_target_year[target_end_year] == required_indicator_count
        )
        lines.append(
            f"  {target_end_year}: {full_coverage_count} countries with {required_indicator_count}/{required_indicator_count} indicators"
        )

    lines.append("")
    lines.append(
        f"Consecutive fully complete history counts ending at {primary_target_end_year}"
    )
    for history_threshold_year in history_threshold_years:
        qualifying_country_count = count_countries_meeting_history_threshold(
            rows=rows,
            target_end_year=primary_target_end_year,
            history_threshold_year=history_threshold_year,
        )
        lines.append(
            f"  >={history_threshold_year} years: {qualifying_country_count} countries"
        )

    lines.append("")
    lines.append(f"Top {min(top_n, len(rows))} ranked countries")
    lines.append(
        "  code | name                          | "
        + " | ".join(f"{target_end_year}" for target_end_year in target_end_years)
        + f" | hist{primary_target_end_year}"
        + " | debt"
    )
    for row in rows[:top_n]:
        coverage = " | ".join(
            f"{row.coverage_by_target_year[target_end_year]}/{required_indicator_count}"
            for target_end_year in target_end_years
        )
        history_span = row.consecutive_complete_years_by_target[primary_target_end_year]
        debt_latest_year = row.latest_year_by_indicator["GC.DOD.TOTL.GD.ZS"]
        debt_display = str(debt_latest_year) if debt_latest_year is not None else "-"
        monitored_marker = "*" if row.candidate.is_currently_monitored else " "
        lines.append(
            f"{monitored_marker} {row.candidate.code:>2} | {row.candidate.name[:28]:<28} | {coverage} | {history_span:>8} | {debt_display}"
        )

    monitored_rows = [row for row in rows if row.candidate.is_currently_monitored]
    lines.append("")
    lines.append("Current monitored-set coverage")
    for row in sorted(monitored_rows, key=lambda monitored_row: monitored_row.candidate.code):
        coverage = ", ".join(
            f"{target_end_year}={row.coverage_by_target_year[target_end_year]}/{required_indicator_count}"
            for target_end_year in target_end_years
        )
        lines.append(
            f"  {row.candidate.code}: {coverage}, "
            f"hist{primary_target_end_year}={row.consecutive_complete_years_by_target[primary_target_end_year]}"
        )

    return "\n".join(lines)


def run_feasibility_scan(
    start_year: int | None,
    target_end_years: Sequence[int],
    history_threshold_years: Sequence[int],
    retries: int,
    country_batch_size: int,
    minimum_country_count: int,
    top_n: int,
    timeout_seconds: int | None = None,
    output_csv: Path | None = None,
) -> tuple[str, list[CountryFeasibility]]:
    """Run the end-to-end country feasibility scan.

    Args:
        start_year: Earliest requested annual year when explicitly provided.
        target_end_years: Target end years to score.
        history_threshold_years: Consecutive complete-history thresholds to report.
        country_batch_size: Number of countries per batched indicator request.
        minimum_country_count: Minimum complete-country count for the headline.
        top_n: Number of ranked countries to print.
        output_csv: Optional CSV output path.

    Returns:
        Tuple of formatted report string and ranked feasibility rows.
    """
    session = requests.Session()
    resolved_timeout_seconds = resolve_request_timeout_seconds(timeout_seconds)
    resolved_start_year = resolve_start_year(
        start_year_override=start_year,
        target_end_years=target_end_years,
        history_threshold_years=history_threshold_years,
    )
    countries = fetch_candidate_countries(
        session=session,
        timeout_seconds=resolved_timeout_seconds,
        retries=retries,
    )
    available_years_by_indicator = fetch_available_years_by_indicator(
        session=session,
        countries=countries,
        start_year=resolved_start_year,
        end_year=max(target_end_years),
        retries=retries,
        country_batch_size=country_batch_size,
        timeout_seconds=resolved_timeout_seconds,
    )
    rows = build_country_feasibility_rows(
        countries=countries,
        available_years_by_indicator=available_years_by_indicator,
        target_end_years=target_end_years,
        start_year=resolved_start_year,
    )
    if output_csv is not None:
        write_csv_report(
            rows=rows,
            target_end_years=target_end_years,
            history_threshold_years=history_threshold_years,
            output_path=output_csv,
        )
    report = format_report(
        rows=rows,
        target_end_years=target_end_years,
        history_threshold_years=history_threshold_years,
        minimum_country_count=minimum_country_count,
        top_n=top_n,
    )
    return report, rows


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entry point.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    target_end_years = tuple(
        sorted(
            set(args.target_end_years or default_target_end_years()),
            reverse=True,
        )
    )
    history_threshold_years = build_history_threshold_years(
        minimum_history_years=args.minimum_history_years,
        maximum_history_years=args.maximum_history_years,
    )
    report, _rows = run_feasibility_scan(
        start_year=args.start_year,
        target_end_years=target_end_years,
        history_threshold_years=history_threshold_years,
        retries=args.retries,
        country_batch_size=args.country_batch_size,
        minimum_country_count=args.minimum_country_count,
        top_n=args.top_n,
        timeout_seconds=args.timeout_seconds,
        output_csv=args.output_csv,
    )
    sys.stdout.write(f"{report}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())