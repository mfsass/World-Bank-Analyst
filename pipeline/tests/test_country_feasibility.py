"""Business tests for country-feasibility scoring over live World Bank coverage."""

from __future__ import annotations

import pytest
import requests

from pipeline.country_feasibility import (
    CountryCandidate,
    build_history_threshold_years,
    build_country_feasibility_rows,
    count_countries_meeting_history_threshold,
    find_highest_practical_target_year,
    parse_country_candidates,
    request_json_with_retries,
)


class FakeResponse:
    """Minimal response stub for retry-path tests."""

    def __init__(self, payload: object) -> None:
        """Store the payload that json() should return.

        Args:
            payload: Decoded JSON payload to return.
        """
        self._payload = payload

    def raise_for_status(self) -> None:
        """Pretend the response was successful."""

    def json(self) -> object:
        """Return the configured JSON payload."""
        return self._payload


class FlakySession:
    """Requests-like session stub that fails once before succeeding."""

    def __init__(self) -> None:
        """Track the number of times get() is called."""
        self.calls = 0

    def get(self, url: str, params: dict[str, object], timeout: int) -> FakeResponse:
        """Raise once, then return a successful response.

        Args:
            url: Request URL.
            params: Query params.
            timeout: Request timeout.

        Returns:
            Fake successful response after the initial failure.
        """
        self.calls += 1
        assert url == "https://example.test"
        assert params == {"format": "json"}
        assert timeout == 12
        if self.calls == 1:
            raise requests.ConnectionError("temporary connection reset")
        return FakeResponse({"ok": True})


def test_parse_country_candidates_excludes_aggregates_and_marks_monitored_scope() -> None:
    """Country parsing should keep real countries only and flag the current monitored set."""
    rows = [
        {
            "id": "BRA",
            "iso2Code": "BR",
            "name": "Brazil",
            "region": {"id": "LCN", "value": "Latin America & Caribbean"},
            "incomeLevel": {"id": "UMC", "value": "Upper middle income"},
        },
        {
            "id": "1W",
            "iso2Code": "1W",
            "name": "World",
            "region": {"id": "NA", "value": "Aggregates"},
            "incomeLevel": {"id": "NA", "value": "Aggregates"},
        },
    ]

    candidates = parse_country_candidates(rows)

    assert len(candidates) == 1
    assert candidates[0].code == "BR"
    assert candidates[0].name == "Brazil"
    assert candidates[0].is_currently_monitored is True


def test_country_feasibility_scoring_identifies_highest_practical_target_year() -> None:
    """Scoring should show when a slightly older target year unlocks a usable shortlist."""
    countries = [
        CountryCandidate("ZA", "ZAF", "South Africa", "Sub-Saharan Africa", "Upper middle income", True),
        CountryCandidate("AU", "AUS", "Australia", "East Asia & Pacific", "High income", True),
        CountryCandidate("BR", "BRA", "Brazil", "Latin America & Caribbean", "Upper middle income", False),
    ]
    available_years_by_indicator = {
        "NY.GDP.MKTP.CD": {
            "ZA": (2022, 2023, 2024),
            "AU": (2021, 2022, 2023, 2024),
            "BR": (2021, 2022, 2023),
        },
        "NY.GDP.MKTP.KD.ZG": {
            "ZA": (2022, 2023, 2024),
            "AU": (2021, 2022, 2023, 2024),
            "BR": (2021, 2022, 2023),
        },
        "FP.CPI.TOTL.ZG": {
            "ZA": (2022, 2023, 2024),
            "AU": (2021, 2022, 2023, 2024),
            "BR": (2021, 2022, 2023),
        },
        "SL.UEM.TOTL.ZS": {
            "ZA": (2022, 2023, 2024, 2025),
            "AU": (2021, 2022, 2023, 2024, 2025),
            "BR": (2021, 2022, 2023, 2024),
        },
        "BN.CAB.XOKA.GD.ZS": {
            "ZA": (2022, 2023, 2024),
            "AU": (2021, 2022, 2023, 2024),
            "BR": (2021, 2022, 2023),
        },
        "GC.DOD.TOTL.GD.ZS": {
            "ZA": (2022, 2023),
            "AU": (2021, 2022, 2023),
            "BR": (2021, 2022, 2023),
        },
    }
    target_end_years = (2025, 2024, 2023)

    rows = build_country_feasibility_rows(
        countries=countries,
        available_years_by_indicator=available_years_by_indicator,
        target_end_years=target_end_years,
        start_year=2021,
    )

    row_by_code = {row.candidate.code: row for row in rows}
    assert row_by_code["ZA"].coverage_by_target_year == {2025: 5, 2024: 6, 2023: 6}
    assert row_by_code["AU"].coverage_by_target_year == {2025: 5, 2024: 6, 2023: 6}
    assert row_by_code["BR"].coverage_by_target_year == {2025: 1, 2024: 6, 2023: 6}
    assert row_by_code["ZA"].consecutive_complete_years_by_target == {2025: 0, 2024: 0, 2023: 2}
    assert row_by_code["AU"].consecutive_complete_years_by_target == {2025: 0, 2024: 0, 2023: 3}
    assert row_by_code["BR"].consecutive_complete_years_by_target == {2025: 0, 2024: 0, 2023: 3}

    assert find_highest_practical_target_year(rows, target_end_years, minimum_country_count=2) == 2024


def test_history_threshold_counts_measure_country_count_vs_complete_window_length() -> None:
    """History-threshold counts should expose how shortlist size changes with window depth."""
    countries = [
        CountryCandidate("US", "USA", "United States", "North America", "High income", True),
        CountryCandidate("MX", "MEX", "Mexico", "Latin America & Caribbean", "Upper middle income", False),
        CountryCandidate("ZA", "ZAF", "South Africa", "Sub-Saharan Africa", "Upper middle income", True),
    ]
    available_years_by_indicator = {
        indicator_code: {
            "US": tuple(range(2011, 2026)),
            "MX": tuple(range(2016, 2026)),
            "ZA": tuple(range(2022, 2025)),
        }
        for indicator_code in (
            "NY.GDP.MKTP.CD",
            "NY.GDP.MKTP.KD.ZG",
            "FP.CPI.TOTL.ZG",
            "SL.UEM.TOTL.ZS",
            "BN.CAB.XOKA.GD.ZS",
            "GC.DOD.TOTL.GD.ZS",
        )
    }
    rows = build_country_feasibility_rows(
        countries=countries,
        available_years_by_indicator=available_years_by_indicator,
        target_end_years=(2025, 2024, 2023),
        start_year=2011,
    )
    history_threshold_years = build_history_threshold_years(5, 15)

    assert history_threshold_years[0] == 5
    assert history_threshold_years[-1] == 15
    assert count_countries_meeting_history_threshold(rows, 2025, 5) == 2
    assert count_countries_meeting_history_threshold(rows, 2025, 10) == 2
    assert count_countries_meeting_history_threshold(rows, 2025, 11) == 1
    assert count_countries_meeting_history_threshold(rows, 2025, 15) == 1


def test_request_json_with_retries_recovers_from_transient_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The feasibility scan should retry transient HTTP failures before giving up."""
    flaky_session = FlakySession()
    monkeypatch.setattr("pipeline.country_feasibility.time.sleep", lambda *_args, **_kwargs: None)

    payload = request_json_with_retries(
        session=flaky_session,
        url="https://example.test",
        params={"format": "json"},
        timeout_seconds=12,
        retries=3,
        request_name="example request",
    )

    assert payload == {"ok": True}
    assert flaky_session.calls == 2