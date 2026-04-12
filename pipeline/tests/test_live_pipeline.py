"""Business tests for the live World Bank fetch path and monitored-set orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import pipeline.main as pipeline_main
from pipeline.ai_client import (
    STEP1_NAME,
    STEP1_PROMPT_VERSION,
    STEP2_NAME,
    STEP2_PROMPT_VERSION,
    STEP3_NAME,
    STEP3_PROMPT_VERSION,
    build_input_fingerprint,
)
from pipeline.dev_ai_adapter import create_development_client
from pipeline.fetcher import (
    INDICATORS,
    IndicatorFetchResult,
    LIVE_DATE_RANGE,
    WORLD_BANK_SOURCE_ID,
    WORLD_BANK_SOURCE_NAME,
    LiveFetchResult,
    WorldBankFetchError,
    fetch_indicator_result,
    fetch_live_data,
)
from pipeline.local_data import load_local_data_points
from pipeline.main import PipelineExecutionError
from pipeline.main import run_pipeline
from shared.repository import get_repository


class FakeResponse:
    """Minimal requests-compatible response used by live fetch tests."""

    def __init__(self, payload: Any, url: str, status_code: int = 200) -> None:
        """Initialise the fake response.

        Args:
            payload: JSON payload returned by the response.
            url: Final request URL.
            status_code: HTTP status code.
        """
        self._payload = payload
        self.url = url
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Mirror requests.Response.raise_for_status for successful responses."""

    def json(self) -> Any:
        """Return the configured JSON payload."""
        return self._payload


EXPECTED_MONITORED_COUNTRIES: dict[str, dict[str, str]] = {
    "BR": {"name": "Brazil", "iso3": "BRA"},
    "CA": {"name": "Canada", "iso3": "CAN"},
    "GB": {"name": "United Kingdom", "iso3": "GBR"},
    "US": {"name": "United States", "iso3": "USA"},
    "BS": {"name": "Bahamas, The", "iso3": "BHS"},
    "CO": {"name": "Colombia", "iso3": "COL"},
    "SV": {"name": "El Salvador", "iso3": "SLV"},
    "GE": {"name": "Georgia", "iso3": "GEO"},
    "HU": {"name": "Hungary", "iso3": "HUN"},
    "MY": {"name": "Malaysia", "iso3": "MYS"},
    "NZ": {"name": "New Zealand", "iso3": "NZL"},
    "RU": {"name": "Russian Federation", "iso3": "RUS"},
    "SG": {"name": "Singapore", "iso3": "SGP"},
    "ES": {"name": "Spain", "iso3": "ESP"},
    "CH": {"name": "Switzerland", "iso3": "CHE"},
    "TR": {"name": "Turkiye", "iso3": "TUR"},
    "UY": {"name": "Uruguay", "iso3": "URY"},
}
EXPECTED_MONITORED_COUNTRY_CODES = list(EXPECTED_MONITORED_COUNTRIES)
LIVE_START_YEAR, LIVE_END_YEAR = [int(part) for part in LIVE_DATE_RANGE.split(":")]
EXPECTED_LIVE_YEARS_PER_INDICATOR = LIVE_END_YEAR - LIVE_START_YEAR + 1
EXPECTED_LIVE_ROWS_PER_INDICATOR = EXPECTED_LIVE_YEARS_PER_INDICATOR * len(
    EXPECTED_MONITORED_COUNTRY_CODES
)
EXPECTED_LIVE_DATA_POINTS = EXPECTED_LIVE_ROWS_PER_INDICATOR * len(INDICATORS)


class StubLiveAIClient:
    """Use deterministic narratives while exercising the live AI wiring path."""

    def __init__(self) -> None:
        self._delegate = create_development_client()

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        result = self._delegate.analyse_indicator(context)
        result["ai_provenance"].update(
            {
                "provider": "stub-live-provider",
                "model": "stub-live-model",
            }
        )
        result["ai_provenance"]["lineage"]["input_fingerprint"] = (
            build_input_fingerprint(
                step_name=STEP1_NAME,
                prompt_version=STEP1_PROMPT_VERSION,
                prompt_input=_strip_private_fields(context),
                provider="stub-live-provider",
                model="stub-live-model",
            )
        )
        return result

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        result = self._delegate.synthesise_country(indicators)
        result["ai_provenance"].update(
            {
                "provider": "stub-live-provider",
                "model": "stub-live-model",
            }
        )
        result["ai_provenance"]["lineage"]["input_fingerprint"] = (
            build_input_fingerprint(
                step_name=STEP2_NAME,
                prompt_version=STEP2_PROMPT_VERSION,
                prompt_input=_ordered_indicator_inputs(indicators),
                provider="stub-live-provider",
                model="stub-live-model",
            )
        )
        return result

    def synthesise_global_overview(
        self, country_briefings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        result = self._delegate.synthesise_global_overview(country_briefings)
        result["ai_provenance"].update(
            {
                "provider": "stub-live-provider",
                "model": "stub-live-model",
            }
        )
        result["ai_provenance"]["lineage"]["input_fingerprint"] = (
            build_input_fingerprint(
                step_name=STEP3_NAME,
                prompt_version=STEP3_PROMPT_VERSION,
                prompt_input=_ordered_country_briefings(country_briefings),
                provider="stub-live-provider",
                model="stub-live-model",
            )
        )
        return result

    def get_provenance(self) -> dict[str, str]:
        return {
            "provider": "stub-live-provider",
            "model": "stub-live-model",
        }


class CountingStubLiveAIClient(StubLiveAIClient):
    """Count provider calls so exact-match reuse can be verified at business level."""

    def __init__(self) -> None:
        super().__init__()
        self.indicator_calls = 0
        self.country_calls = 0
        self.overview_calls = 0

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        self.indicator_calls += 1
        return super().analyse_indicator(context)

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        self.country_calls += 1
        return super().synthesise_country(indicators)

    def synthesise_global_overview(
        self, country_briefings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.overview_calls += 1
        return super().synthesise_global_overview(country_briefings)


class DegradingStubLiveAIClient(StubLiveAIClient):
    """Return one explicit degraded fallback so terminal status honesty can be tested."""

    def __init__(self, degraded_indicator_code: str) -> None:
        super().__init__()
        self._degraded_indicator_code = degraded_indicator_code

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        result = super().analyse_indicator(context)
        if context["indicator_code"] != self._degraded_indicator_code:
            return result

        result["narrative"] = (
            "Live AI analysis degraded after structured-output retries. "
            f"{context['indicator_name']} should be reviewed directly."
        )
        result["confidence"] = "low"
        result["ai_provenance"]["degraded"] = True
        result["ai_provenance"]["degraded_reason"] = (
            "Synthetic structured-output failure."
        )
        return result


def test_live_fetch_normalizes_rows_and_filters_null_or_unusable_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live fetch should keep only usable World Bank rows and preserve raw provenance."""
    monkeypatch.setenv("WORLD_ANALYST_WORLD_BANK_TIMEOUT_SECONDS", "42")
    payload = [
        {
            "page": 1,
            "pages": 1,
            "per_page": 1000,
            "total": 4,
            "sourceid": "2",
            "lastupdated": "2026-03-31",
        },
        [
            {
                "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                "country": {"id": "ZA", "value": "South Africa"},
                "countryiso3code": "ZAF",
                "date": "2023",
                "value": 377781197441.0,
            },
            {
                "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                "country": {"id": "ZA", "value": "South Africa"},
                "countryiso3code": "ZAF",
                "date": "2022",
                "value": None,
            },
            {
                "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                "country": {"id": "ZA", "value": "South Africa"},
                "countryiso3code": "ZAF",
                "date": "bad-year",
                "value": 405869505982.0,
            },
            {
                "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                "country": {"id": "ZA", "value": "South Africa"},
                "countryiso3code": "ZAF",
                "date": "2021",
                "value": "NaN",
            },
        ],
    ]

    def fake_get(url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        assert params == {
            "format": "json",
            "date": LIVE_DATE_RANGE,
            "per_page": 1000,
            "source": WORLD_BANK_SOURCE_ID,
        }
        assert timeout == 42
        return FakeResponse(
            payload=payload,
            url=(
                f"{url}?format=json&date={params['date']}&per_page={params['per_page']}"
                f"&source={params['source']}"
            ),
        )

    monkeypatch.setattr("pipeline.fetcher.requests.get", fake_get)

    result = fetch_indicator_result(
        indicator_code="NY.GDP.MKTP.CD",
        country_codes=["za"],
        run_id="live-run-001",
    )

    assert len(result.data_points) == 1
    assert result.data_points[0] == {
        "country_code": "ZA",
        "country_name": "South Africa",
        "country_iso3": "ZAF",
        "indicator_code": "NY.GDP.MKTP.CD",
        "indicator_name": "GDP (current US$)",
        "year": 2023,
        "value": 377781197441.0,
        "source_name": WORLD_BANK_SOURCE_NAME,
        "source_date_range": LIVE_DATE_RANGE,
        "source_last_updated": "2026-03-31",
        "source_id": "2",
    }
    assert result.raw_payload["country_codes"] == ["ZA"]
    assert result.raw_payload["request"]["params"] == {
        "format": "json",
        "date": LIVE_DATE_RANGE,
        "per_page": 1000,
        "source": WORLD_BANK_SOURCE_ID,
    }
    assert result.raw_payload["response_body"] == payload
    assert result.raw_payload["source_last_updated"] == "2026-03-31"


def test_live_fetch_surfaces_payload_level_api_errors_with_run_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """World Bank payload errors inside HTTP 200 should fail with run and indicator scope."""
    payload = [
        {
            "message": [
                {
                    "id": "120",
                    "key": "Invalid value",
                    "value": "The provided parameter value is not valid",
                }
            ]
        }
    ]

    def fake_get(url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        assert params["source"] == WORLD_BANK_SOURCE_ID
        return FakeResponse(
            payload=payload,
            url=(
                f"{url}?format=json&date={params['date']}&per_page={params['per_page']}"
                f"&source={params['source']}"
            ),
        )

    monkeypatch.setattr("pipeline.fetcher.requests.get", fake_get)

    with pytest.raises(
        WorldBankFetchError,
        match=(
            r"run_id=live-run-002 indicator_code=NY.GDP.MKTP.CD country_codes=ZA: "
            r"World Bank API payload error: Invalid value: The provided parameter value is not valid"
        ),
    ):
        fetch_indicator_result(
            indicator_code="NY.GDP.MKTP.CD",
            country_codes=["ZA"],
            run_id="live-run-002",
        )


def test_live_fetch_fails_loudly_when_indicator_payload_spans_multiple_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live fetch should fail explicitly instead of truncating multi-page indicator data."""
    payload = [
        {
            "page": 1,
            "pages": "2",
            "per_page": 1000,
            "total": 1001,
            "sourceid": "2",
            "lastupdated": "2026-03-31",
        },
        [
            {
                "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                "country": {"id": "ZA", "value": "South Africa"},
                "countryiso3code": "ZAF",
                "date": "2023",
                "value": 377781197441.0,
            }
        ],
    ]

    def fake_get(url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        assert params["source"] == WORLD_BANK_SOURCE_ID
        return FakeResponse(
            payload=payload,
            url=(
                f"{url}?format=json&date={params['date']}&per_page={params['per_page']}"
                f"&source={params['source']}"
            ),
        )

    monkeypatch.setattr("pipeline.fetcher.requests.get", fake_get)

    with pytest.raises(
        WorldBankFetchError,
        match=(
            r"run_id=live-run-002b indicator_code=NY.GDP.MKTP.CD country_codes=ZA: "
            r"World Bank response spanned 2 pages"
        ),
    ):
        fetch_indicator_result(
            indicator_code="NY.GDP.MKTP.CD",
            country_codes=["ZA"],
            run_id="live-run-002b",
        )


def test_live_fetch_drops_stale_country_series_from_indicator_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live fetch should treat stale annual tails as unavailable coverage."""
    payload = [
        {
            "page": 1,
            "pages": 1,
            "per_page": 1000,
            "total": 3,
            "sourceid": "2",
            "lastupdated": "2026-03-31",
        },
        [
            {
                "indicator": {
                    "id": "GC.DOD.TOTL.GD.ZS",
                    "value": "Central government debt, total (% of GDP)",
                },
                "country": {"id": "ZA", "value": "South Africa"},
                "countryiso3code": "ZAF",
                "date": "2023",
                "value": 79.4,
            },
            {
                "indicator": {
                    "id": "GC.DOD.TOTL.GD.ZS",
                    "value": "Central government debt, total (% of GDP)",
                },
                "country": {"id": "AU", "value": "Australia"},
                "countryiso3code": "AUS",
                "date": "2023",
                "value": 57.9,
            },
            {
                "indicator": {
                    "id": "GC.DOD.TOTL.GD.ZS",
                    "value": "Central government debt, total (% of GDP)",
                },
                "country": {"id": "IN", "value": "India"},
                "countryiso3code": "IND",
                "date": "2021",
                "value": 46.5,
            },
        ],
    ]

    def fake_get(url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        assert params["source"] == WORLD_BANK_SOURCE_ID
        return FakeResponse(
            payload=payload,
            url=(
                f"{url}?format=json&date={params['date']}&per_page={params['per_page']}"
                f"&source={params['source']}"
            ),
        )

    monkeypatch.setattr("pipeline.fetcher.requests.get", fake_get)

    result = fetch_indicator_result(
        indicator_code="GC.DOD.TOTL.GD.ZS",
        country_codes=["ZA", "AU", "IN"],
        run_id="live-run-002c",
    )

    assert {data_point["country_code"] for data_point in result.data_points} == {
        "ZA",
        "AU",
    }
    assert result.stale_country_codes == ("IN",)


def test_live_fetch_records_missing_country_coverage_inside_successful_indicator_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live fetch should fail honestly when one requested country has no usable rows."""
    requested_country_codes = ["BR", "CO", "UY"]
    failing_indicator_code = "GC.DOD.TOTL.GD.ZS"

    def fake_fetch_indicator_result(
        indicator_code: str,
        country_codes: list[str] | None = None,
        date_range: str = LIVE_DATE_RANGE,
        retries: int = 3,
        run_id: str | None = None,
    ) -> IndicatorFetchResult:
        assert country_codes == requested_country_codes
        assert date_range == LIVE_DATE_RANGE
        assert retries == 3
        missing_country_codes = (
            ["UY"] if indicator_code == failing_indicator_code else []
        )
        return _build_indicator_fetch_result(
            indicator_code=indicator_code,
            country_codes=country_codes or requested_country_codes,
            missing_country_codes=missing_country_codes,
        )

    monkeypatch.setattr(
        "pipeline.fetcher.fetch_indicator_result", fake_fetch_indicator_result
    )
    monkeypatch.setattr("pipeline.fetcher.time.sleep", lambda *_args, **_kwargs: None)

    result = fetch_live_data(
        country_codes=requested_country_codes, run_id="live-run-003"
    )

    assert len(result.failures) == 1
    assert len(result.raw_payloads) == len(INDICATORS)
    failure = result.failures[0]
    assert failure.indicator_code == failing_indicator_code
    assert failure.country_codes == ["UY"]
    assert "missing countries: UY" in str(failure)
    assert (
        result.raw_payloads[failing_indicator_code]["country_codes"]
        == requested_country_codes
    )
    assert {
        point["country_code"]
        for point in result.data_points
        if point["indicator_code"] == failing_indicator_code
    } == {"BR", "CO"}


def test_live_pipeline_treats_stale_indicator_series_as_incomplete_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale live series should be excluded from synthesis and reported as incomplete."""
    repository = get_repository()
    run_id = "5b3f7af0-c98c-4d7c-9308-bfd2a913fa6d"
    failing_indicator_code = "GC.DOD.TOTL.GD.ZS"
    stale_country_code = "CO"
    live_fetch_result = _build_live_fetch_result(run_id=run_id)
    debt_payload = live_fetch_result.raw_payloads[failing_indicator_code]

    filtered_data_points = [
        data_point
        for data_point in live_fetch_result.data_points
        if not (
            data_point["indicator_code"] == failing_indicator_code
            and data_point["country_code"] == stale_country_code
        )
    ]

    def fake_live_fetch(
        country_codes: list[str], run_id: str | None = None
    ) -> LiveFetchResult:
        assert country_codes == EXPECTED_MONITORED_COUNTRY_CODES
        assert run_id == "5b3f7af0-c98c-4d7c-9308-bfd2a913fa6d"
        return LiveFetchResult(
            data_points=filtered_data_points,
            raw_payloads=live_fetch_result.raw_payloads,
            failures=(
                WorldBankFetchError(
                    message=(
                        f"run_id={run_id} indicator_code={failing_indicator_code} country_codes={stale_country_code}: "
                        "World Bank returned usable rows for 16 of 17 requested countries; "
                        f"stale countries: {stale_country_code}"
                    ),
                    indicator_code=failing_indicator_code,
                    country_codes=[stale_country_code],
                    run_id=run_id,
                ),
            ),
        )

    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(pipeline_main, "fetch_live_data", fake_live_fetch)
    monkeypatch.setattr(
        pipeline_main, "create_client", lambda provider=None: StubLiveAIClient()
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        run_pipeline(repository=repository, run_id=run_id)

    assert "stale countries: CO" in str(exc_info.value)
    assert exc_info.value.country_codes == [stale_country_code]
    assert exc_info.value.indicator_codes == [failing_indicator_code]

    colombia_detail = repository.get_country_detail("CO")
    assert colombia_detail is not None
    assert len(colombia_detail["indicators"]) == len(INDICATORS) - 1
    assert (
        "government debt data is unavailable in the live source"
        in colombia_detail["macro_synthesis"]
    )
    assert any(
        "Government debt data is unavailable in the live source" in flag
        for flag in colombia_detail["risk_flags"]
    )
    assert debt_payload["response_metadata"]["sourceid"] == "2"


def test_live_pipeline_uses_world_bank_fetch_and_archives_raw_request_envelopes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A live monitored-set run should persist multi-country records and raw WB envelopes."""
    repository = get_repository()
    run_id = "7b39d3ae-5cf2-4ff8-bf24-2f761935f9fb"
    live_fetch_result = _build_live_fetch_result(run_id=run_id)

    def fake_live_fetch(
        country_codes: list[str], run_id: str | None = None
    ) -> LiveFetchResult:
        assert country_codes == EXPECTED_MONITORED_COUNTRY_CODES
        assert run_id == "7b39d3ae-5cf2-4ff8-bf24-2f761935f9fb"
        return live_fetch_result

    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(pipeline_main, "fetch_live_data", fake_live_fetch)
    monkeypatch.setattr(
        pipeline_main, "create_client", lambda provider=None: StubLiveAIClient()
    )

    summary = run_pipeline(repository=repository, run_id=run_id)

    assert summary["data_points_fetched"] == EXPECTED_LIVE_DATA_POINTS
    assert summary["indicators_analysed"] == len(INDICATORS) * len(
        EXPECTED_MONITORED_COUNTRY_CODES
    )
    assert summary["countries_synthesised"] == len(EXPECTED_MONITORED_COUNTRY_CODES)
    assert summary["indicator_records"] == len(INDICATORS) * len(
        EXPECTED_MONITORED_COUNTRY_CODES
    )
    assert summary["country_records"] == len(EXPECTED_MONITORED_COUNTRY_CODES)
    assert summary["global_overview_records"] == 1
    assert summary["raw_archives_written"] == 7

    indicator_record = repository._records["indicator:BR:NY.GDP.MKTP.KD.ZG"]
    country_record = repository._records["country:BR"]
    overview_record = repository._records["global_overview:current"]
    assert indicator_record["source_provenance"] == {
        "source_name": WORLD_BANK_SOURCE_NAME,
        "source_date_range": LIVE_DATE_RANGE,
        "source_last_updated": "2026-03-31",
        "source_id": "2",
    }
    assert country_record["source_provenance"]["source_name"] == WORLD_BANK_SOURCE_NAME
    assert country_record["source_provenance"]["indicator_codes"] == sorted(
        list(INDICATORS)
    )
    assert indicator_record["ai_provenance"]["provider"] == "stub-live-provider"
    assert indicator_record["ai_provenance"]["prompt_version"] == "step1.v1.0.0"
    assert indicator_record["ai_provenance"]["degraded"] is False
    assert country_record["ai_provenance"]["provider"] == "stub-live-provider"
    assert country_record["ai_provenance"]["prompt_version"] == "step2.v1.0.0"
    assert country_record["ai_provenance"]["degraded"] is False
    assert overview_record["ai_provenance"]["provider"] == "stub-live-provider"
    assert overview_record["ai_provenance"]["prompt_version"] == STEP3_PROMPT_VERSION
    assert overview_record["ai_provenance"]["degraded"] is False
    assert overview_record["country_count"] == len(EXPECTED_MONITORED_COUNTRY_CODES)

    brazil_detail = repository.get_country_detail("BR")
    uruguay_detail = repository.get_country_detail("UY")
    global_overview = repository.get_global_overview()
    assert brazil_detail is not None
    assert uruguay_detail is not None
    assert global_overview is not None
    assert brazil_detail["code"] == "BR"
    assert brazil_detail["name"] == "Brazil"
    assert len(brazil_detail["indicators"]) == len(INDICATORS)
    assert uruguay_detail["code"] == "UY"
    assert len(uruguay_detail["indicators"]) == len(INDICATORS)
    assert global_overview["country_count"] == len(EXPECTED_MONITORED_COUNTRY_CODES)
    assert global_overview["summary"]

    raw_archive_path = (
        tmp_path / "raw-archives" / "runs" / run_id / "raw" / "NY.GDP.MKTP.KD.ZG.json"
    )
    archived_payload = json.loads(raw_archive_path.read_text(encoding="utf-8"))

    assert archived_payload["indicator_code"] == "NY.GDP.MKTP.KD.ZG"
    assert archived_payload["country_codes"] == EXPECTED_MONITORED_COUNTRY_CODES
    assert archived_payload["request"]["params"]["date"] == LIVE_DATE_RANGE
    assert (
        archived_payload["response_metadata"]["total"]
        == EXPECTED_LIVE_ROWS_PER_INDICATOR
    )
    assert archived_payload["response_metadata"]["lastupdated"] == "2026-03-31"
    assert len(archived_payload["response_body"][1]) == EXPECTED_LIVE_ROWS_PER_INDICATOR
    assert (
        archived_payload["response_body"][1][0]["indicator"]["id"]
        == "NY.GDP.MKTP.KD.ZG"
    )


def test_live_pipeline_uses_the_live_ai_factory_instead_of_the_local_development_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live mode should route AI calls through the provider-backed factory seam."""

    repository = get_repository()
    run_id = "d27611eb-77c0-4ad8-8fa5-c6096853e609"
    live_fetch_result = _build_live_fetch_result(run_id=run_id)
    stub_live_ai = StubLiveAIClient()
    live_factory_calls = {"count": 0}

    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(
        pipeline_main,
        "fetch_live_data",
        lambda country_codes, run_id=None: live_fetch_result,
    )

    def create_stub_live_client(provider: str | None = None) -> StubLiveAIClient:
        assert provider is None
        live_factory_calls["count"] += 1
        return stub_live_ai

    monkeypatch.setattr(pipeline_main, "create_client", create_stub_live_client)
    monkeypatch.setattr(
        pipeline_main,
        "create_development_client",
        lambda: (_ for _ in ()).throw(
            AssertionError("Live mode should not use the development AI adapter.")
        ),
    )

    summary = run_pipeline(repository=repository, run_id=run_id)

    assert summary["countries_synthesised"] == len(EXPECTED_MONITORED_COUNTRY_CODES)
    assert live_factory_calls["count"] == 1


def test_live_pipeline_reuses_exact_match_ai_results_from_persisted_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A repeated live run should skip duplicate provider calls for exact AI input matches."""
    repository = get_repository()
    live_ai = CountingStubLiveAIClient()
    first_run_id = "2f1db276-09c2-4431-a02e-ef356fe8d9ef"
    second_run_id = "22d52ed0-bd0f-4219-b510-c2d254aa53a8"
    live_fetch_result = _build_live_fetch_result(run_id=first_run_id)

    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(
        pipeline_main,
        "fetch_live_data",
        lambda country_codes, run_id=None: live_fetch_result,
    )
    monkeypatch.setattr(
        pipeline_main,
        "create_client",
        lambda provider=None: live_ai,
    )

    first_summary = run_pipeline(repository=repository, run_id=first_run_id)

    assert first_summary["indicators_analysed"] == len(INDICATORS) * len(
        EXPECTED_MONITORED_COUNTRY_CODES
    )
    assert first_summary["countries_synthesised"] == len(
        EXPECTED_MONITORED_COUNTRY_CODES
    )
    assert live_ai.indicator_calls == len(INDICATORS) * len(
        EXPECTED_MONITORED_COUNTRY_CODES
    )
    assert live_ai.country_calls == len(EXPECTED_MONITORED_COUNTRY_CODES)
    assert live_ai.overview_calls == 1

    second_summary = run_pipeline(repository=repository, run_id=second_run_id)

    assert second_summary["indicators_analysed"] == first_summary["indicators_analysed"]
    assert (
        second_summary["countries_synthesised"]
        == first_summary["countries_synthesised"]
    )
    assert live_ai.indicator_calls == len(INDICATORS) * len(
        EXPECTED_MONITORED_COUNTRY_CODES
    )
    assert live_ai.country_calls == len(EXPECTED_MONITORED_COUNTRY_CODES)
    assert live_ai.overview_calls == 1

    reused_indicator_record = repository._records["indicator:BR:NY.GDP.MKTP.KD.ZG"]
    reused_country_record = repository._records["country:BR"]
    reused_overview_record = repository._records["global_overview:current"]
    assert reused_indicator_record["run_id"] == second_run_id
    assert reused_indicator_record["ai_provenance"]["lineage"]["reused_from"] == {
        "document_id": "indicator:BR:NY.GDP.MKTP.KD.ZG",
        "run_id": first_run_id,
    }
    assert reused_country_record["ai_provenance"]["lineage"]["reused_from"] == {
        "document_id": "country:BR",
        "run_id": first_run_id,
    }
    assert reused_overview_record["ai_provenance"]["lineage"]["reused_from"] == {
        "document_id": "global_overview:current",
        "run_id": first_run_id,
    }
    assert "usage" not in reused_indicator_record["ai_provenance"]


def test_live_pipeline_marks_terminal_status_failed_when_ai_falls_back_to_degraded_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A degraded live AI fallback should keep stored output but fail the terminal run honestly."""
    repository = get_repository()
    run_id = "0dd8b6ef-93c9-45bd-90ab-196e4a569ce5"
    degraded_indicator_code = "NY.GDP.MKTP.KD.ZG"
    live_fetch_result = _build_live_fetch_result(run_id=run_id)

    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(
        pipeline_main,
        "fetch_live_data",
        lambda country_codes, run_id=None: live_fetch_result,
    )
    monkeypatch.setattr(
        pipeline_main,
        "create_client",
        lambda provider=None: DegradingStubLiveAIClient(degraded_indicator_code),
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        run_pipeline(repository=repository, run_id=run_id)

    assert exc_info.value.step_name == "synthesise"
    assert "degraded coverage" in str(exc_info.value)
    assert degraded_indicator_code in str(exc_info.value)

    brazil_detail = repository.get_country_detail("BR")
    assert brazil_detail is not None
    assert brazil_detail["macro_synthesis"]
    indicator_record = repository._records[f"indicator:BR:{degraded_indicator_code}"]
    assert indicator_record["ai_provenance"]["degraded"] is True
    assert (
        indicator_record["ai_provenance"]["degraded_reason"]
        == "Synthetic structured-output failure."
    )


def test_live_pipeline_preserves_successful_outputs_when_indicator_coverage_is_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial live run should store good monitored-set output but still fail terminally."""
    repository = get_repository()
    run_id = "41057c18-5d94-45c9-a8eb-d95f63d6d948"
    failing_indicator_code = "GC.DOD.TOTL.GD.ZS"
    missing_country_code = "UY"
    live_fetch_result = _build_live_fetch_result(
        run_id=run_id,
        missing_country_codes_by_indicator={
            failing_indicator_code: [missing_country_code],
        },
    )

    def fake_live_fetch(
        country_codes: list[str], run_id: str | None = None
    ) -> LiveFetchResult:
        assert country_codes == EXPECTED_MONITORED_COUNTRY_CODES
        assert run_id == "41057c18-5d94-45c9-a8eb-d95f63d6d948"
        return live_fetch_result

    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(pipeline_main, "fetch_live_data", fake_live_fetch)
    monkeypatch.setattr(
        pipeline_main, "create_client", lambda provider=None: StubLiveAIClient()
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        run_pipeline(repository=repository, run_id=run_id)

    assert "incomplete coverage" in str(exc_info.value)
    assert exc_info.value.country_codes == [missing_country_code]
    assert exc_info.value.indicator_codes == [failing_indicator_code]

    uruguay_detail = repository.get_country_detail("UY")
    brazil_detail = repository.get_country_detail("BR")
    assert uruguay_detail is not None
    assert brazil_detail is not None
    assert uruguay_detail["code"] == "UY"
    assert uruguay_detail["macro_synthesis"]
    assert "government debt to n/a" not in uruguay_detail["macro_synthesis"].lower()
    assert (
        "government debt data is unavailable in the live source"
        in uruguay_detail["macro_synthesis"]
    )
    assert any(
        "Government debt data is unavailable in the live source" in flag
        for flag in uruguay_detail["risk_flags"]
    )
    assert len(uruguay_detail["indicators"]) == len(INDICATORS) - 1
    assert len(brazil_detail["indicators"]) == len(INDICATORS)
    assert "government debt to " in brazil_detail["macro_synthesis"]
    assert "unavailable in the live source" not in brazil_detail["macro_synthesis"]
    assert all(
        indicator["indicator_code"] != failing_indicator_code
        for indicator in uruguay_detail["indicators"]
    )


def _build_live_fetch_result(
    run_id: str | None = None,
    country_codes: list[str] | None = None,
    missing_country_codes_by_indicator: dict[str, list[str]] | None = None,
) -> LiveFetchResult:
    """Build a deterministic live fetch fixture for the monitored country set."""
    current_run_id = run_id or "live-fetch-fixture"
    requested_country_codes = [
        country_code.upper()
        for country_code in (country_codes or EXPECTED_MONITORED_COUNTRY_CODES)
    ]
    missing_country_codes_by_indicator = {
        indicator_code: [country_code.upper() for country_code in missing_country_codes]
        for indicator_code, missing_country_codes in (
            missing_country_codes_by_indicator or {}
        ).items()
    }

    live_points: list[dict[str, Any]] = []
    raw_payloads: dict[str, dict[str, Any]] = {}
    failures: list[WorldBankFetchError] = []
    for indicator_code in INDICATORS:
        missing_country_codes = missing_country_codes_by_indicator.get(
            indicator_code, []
        )
        indicator_result = _build_indicator_fetch_result(
            indicator_code=indicator_code,
            country_codes=requested_country_codes,
            missing_country_codes=missing_country_codes,
        )
        live_points.extend(indicator_result.data_points)
        raw_payloads[indicator_code] = indicator_result.raw_payload
        if missing_country_codes:
            failures.append(
                WorldBankFetchError(
                    message=(
                        f"run_id={current_run_id} indicator_code={indicator_code} "
                        f"country_codes={','.join(missing_country_codes)}: "
                        "World Bank returned usable rows for "
                        f"{len(requested_country_codes) - len(missing_country_codes)} of "
                        f"{len(requested_country_codes)} requested countries; "
                        f"missing countries: {', '.join(missing_country_codes)}"
                    ),
                    indicator_code=indicator_code,
                    country_codes=missing_country_codes,
                    run_id=current_run_id,
                )
            )

    return LiveFetchResult(
        data_points=live_points,
        raw_payloads=raw_payloads,
        failures=tuple(failures),
    )


def _ordered_indicator_inputs(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mirror the runtime's deterministic Step 2 ordering for test doubles."""
    return [
        _strip_private_fields(indicator)
        for indicator in sorted(
            indicators,
            key=lambda item: (
                str(item.get("country_code", "")),
                str(item.get("indicator_code", "")),
                int(item.get("data_year", 0) or 0),
            ),
        )
    ]


def _ordered_country_briefings(
    country_briefings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mirror the runtime's deterministic Step 3 ordering for test doubles."""

    return [
        _strip_private_fields(briefing)
        for briefing in sorted(
            country_briefings,
            key=lambda item: (
                str(item.get("code", "")),
                str(item.get("name", "")),
            ),
        )
    ]


def _strip_private_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove private fields before test fingerprint calculation."""
    return {
        key: value
        for key, value in payload.items()
        if key
        not in {"ai_provenance", "source_provenance", "raw_backup_reference", "run_id"}
    }


def _build_indicator_fetch_result(
    indicator_code: str,
    country_codes: list[str],
    missing_country_codes: list[str] | None = None,
) -> IndicatorFetchResult:
    """Build one deterministic indicator result for the requested country scope."""
    indicator_name = INDICATORS[indicator_code]
    requested_country_codes = [country_code.upper() for country_code in country_codes]
    missing_country_code_set = {
        country_code.upper() for country_code in (missing_country_codes or [])
    }

    indicator_points: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    for country_code in requested_country_codes:
        if country_code in missing_country_code_set:
            continue
        cloned_points = _clone_local_indicator_points(
            indicator_code=indicator_code,
            country_code=country_code,
        )
        indicator_points.extend(cloned_points)
        raw_rows.extend(
            _build_world_bank_row(point, indicator_name) for point in cloned_points
        )

    metadata = {
        "page": 1,
        "pages": 1,
        "per_page": 1000,
        "total": len(raw_rows),
        "sourceid": "2",
        "lastupdated": "2026-03-31",
    }
    country_path = ";".join(
        country_code.lower() for country_code in requested_country_codes
    )
    return IndicatorFetchResult(
        indicator_code=indicator_code,
        data_points=indicator_points,
        raw_payload={
            "source_name": WORLD_BANK_SOURCE_NAME,
            "source_date_range": LIVE_DATE_RANGE,
            "source_last_updated": "2026-03-31",
            "source_id": "2",
            "indicator_code": indicator_code,
            "indicator_name": indicator_name,
            "country_codes": requested_country_codes,
            "request": {
                "url": (
                    f"https://api.worldbank.org/v2/country/{country_path}/indicator/{indicator_code}"
                    f"?format=json&date={LIVE_DATE_RANGE}&per_page=1000&source={WORLD_BANK_SOURCE_ID}"
                ),
                "params": {
                    "format": "json",
                    "date": LIVE_DATE_RANGE,
                    "per_page": 1000,
                    "source": WORLD_BANK_SOURCE_ID,
                },
            },
            "http_status": 200,
            "fetched_at": "2026-04-11T12:00:00+00:00",
            "response_metadata": metadata,
            "response_body": [metadata, raw_rows],
        },
    )


def _clone_local_indicator_points(
    indicator_code: str, country_code: str
) -> list[dict[str, Any]]:
    """Expand the ZA fixture into one deterministic 2010:2024 live-country series."""
    country_fixture = EXPECTED_MONITORED_COUNTRIES[country_code]
    return [
        {
            **point,
            "country_code": country_code,
            "country_name": country_fixture["name"],
            "country_iso3": country_fixture["iso3"],
            "source_name": WORLD_BANK_SOURCE_NAME,
            "source_date_range": LIVE_DATE_RANGE,
            "source_last_updated": "2026-03-31",
            "source_id": "2",
        }
        for point in _build_synthetic_live_indicator_points(indicator_code)
    ]


def _build_synthetic_live_indicator_points(indicator_code: str) -> list[dict[str, Any]]:
    """Extend the local ZA history so live tests cover the full runtime window."""
    base_points = sorted(
        (
            point
            for point in load_local_data_points("ZA")
            if point["indicator_code"] == indicator_code
        ),
        key=lambda point: int(point["year"]),
    )
    base_points_by_year = {int(point["year"]): point for point in base_points}
    first_year = int(base_points[0]["year"])
    last_year = int(base_points[-1]["year"])
    first_value = float(base_points[0]["value"])
    last_value = float(base_points[-1]["value"])
    annual_delta = 0.0
    if last_year > first_year:
        annual_delta = (last_value - first_value) / (last_year - first_year)

    synthetic_points: list[dict[str, Any]] = []
    for year in range(LIVE_START_YEAR, LIVE_END_YEAR + 1):
        template_year = min(max(year, first_year), last_year)
        synthetic_point = dict(base_points_by_year[template_year])
        synthetic_point["year"] = year
        synthetic_point["value"] = _synthetic_indicator_value(
            year=year,
            base_points_by_year=base_points_by_year,
            first_year=first_year,
            last_year=last_year,
            annual_delta=annual_delta,
        )
        synthetic_points.append(synthetic_point)

    return synthetic_points


def _synthetic_indicator_value(
    year: int,
    base_points_by_year: dict[int, dict[str, Any]],
    first_year: int,
    last_year: int,
    annual_delta: float,
) -> float:
    """Return one deterministic synthetic value for a requested live-test year."""
    if year in base_points_by_year:
        return float(base_points_by_year[year]["value"])
    if year < first_year:
        return float(base_points_by_year[first_year]["value"]) - annual_delta * (
            first_year - year
        )
    return float(base_points_by_year[last_year]["value"]) + annual_delta * (
        year - last_year
    )


def _build_world_bank_row(point: dict[str, Any], indicator_name: str) -> dict[str, Any]:
    """Convert one normalized point into a World Bank-like raw payload row."""
    return {
        "indicator": {
            "id": point["indicator_code"],
            "value": indicator_name,
        },
        "country": {
            "id": point["country_code"],
            "value": point["country_name"],
        },
        "countryiso3code": point["country_iso3"],
        "date": str(point["year"]),
        "value": point["value"],
        "unit": "",
        "obs_status": "",
        "decimal": 0,
    }
