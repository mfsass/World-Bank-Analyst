"""Opt-in smoke tests against the real World Bank API."""

from __future__ import annotations

import os
from collections import Counter

import pytest

from pipeline.fetcher import INDICATORS, LIVE_DATE_RANGE, fetch_live_data
from shared.country_catalog import MONITORED_COUNTRY_CODES

RUN_LIVE_WORLD_BANK_TESTS = os.environ.get("WORLD_ANALYST_RUN_LIVE_TESTS") == "1"
START_YEAR, END_YEAR = [int(part) for part in LIVE_DATE_RANGE.split(":")]
EXPECTED_ROWS_PER_INDICATOR = (END_YEAR - START_YEAR + 1) * len(MONITORED_COUNTRY_CODES)

pytestmark = pytest.mark.skipif(
    not RUN_LIVE_WORLD_BANK_TESTS,
    reason="Set WORLD_ANALYST_RUN_LIVE_TESTS=1 to run live World Bank smoke tests.",
)


def test_live_world_bank_monitored_panel_smoke() -> None:
    """The approved monitored panel should still fetch cleanly from the live API."""
    result = fetch_live_data(
        country_codes=list(MONITORED_COUNTRY_CODES),
        run_id="live-world-bank-smoke",
    )

    assert result.failures == ()
    assert set(result.raw_payloads) == set(INDICATORS)
    assert len(result.data_points) == EXPECTED_ROWS_PER_INDICATOR * len(INDICATORS)
    assert {item["country_code"] for item in result.data_points} == set(MONITORED_COUNTRY_CODES)
    assert all(item["source_date_range"] == LIVE_DATE_RANGE for item in result.data_points)

    rows_by_indicator = Counter(item["indicator_code"] for item in result.data_points)
    assert rows_by_indicator == {
        indicator_code: EXPECTED_ROWS_PER_INDICATOR for indicator_code in INDICATORS
    }
