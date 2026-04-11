"""Business tests for the first local vertical slice."""

from __future__ import annotations

import json
import time

import pipeline.main as pipeline_main
from pipeline.fetcher import INDICATORS, LIVE_DATE_RANGE, WORLD_BANK_SOURCE_ID, WORLD_BANK_SOURCE_NAME, LiveFetchResult, WorldBankFetchError
from pipeline.local_data import load_local_data_points
from handlers import pipeline as pipeline_handler
from shared.repository import get_repository

AUTH_HEADERS = {"X-API-Key": "local-dev"}

EXPECTED_MONITORED_COUNTRY_CODES = [
    "BR",
    "CA",
    "GB",
    "US",
    "BS",
    "CO",
    "SV",
    "GE",
    "HU",
    "MY",
    "NZ",
    "RU",
    "SG",
    "ES",
    "CH",
    "TR",
    "UY",
]


def test_trigger_status_transition_and_country_detail_flow(client) -> None:
    """Triggering the local slice should materialise a ZA country briefing."""
    idle_response = client.get("/api/v1/pipeline/status", headers=AUTH_HEADERS)
    assert idle_response.status_code == 200
    assert idle_response.json()["status"] == "idle"

    trigger_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)
    assert trigger_response.status_code == 202
    assert trigger_response.json()["status"] == "running"

    deadline = time.monotonic() + 2.0
    final_status = None
    while time.monotonic() < deadline:
        status_response = client.get("/api/v1/pipeline/status", headers=AUTH_HEADERS)
        assert status_response.status_code == 200
        final_status = status_response.json()
        if final_status["status"] != "running":
            break
        time.sleep(0.02)

    assert final_status is not None
    assert final_status["status"] == "complete"
    assert any(step["name"] == "store" and step["status"] == "complete" for step in final_status["steps"])
    assert "run_id" not in final_status
    assert "failure_summary" not in final_status

    detail_response = client.get("/api/v1/countries/ZA", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()

    assert detail["code"] == "ZA"
    assert detail["name"] == "South Africa"
    assert len(detail["indicators"]) == 6
    assert detail["macro_synthesis"]
    assert len(detail["risk_flags"]) >= 2
    assert detail["outlook"] in {"cautious", "bearish"}
    assert "run_id" not in detail
    assert "raw_backup_reference" not in detail
    assert all("run_id" not in indicator for indicator in detail["indicators"])
    assert all("source_provenance" not in indicator for indicator in detail["indicators"])


def test_country_detail_returns_not_found_before_trigger(client) -> None:
    """Country detail should not exist before the local slice has run."""
    response = client.get("/api/v1/countries/ZA", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"] == "Not found"


def test_countries_endpoint_returns_monitored_catalog_before_materialisation(client) -> None:
    """The country list should expose the monitored catalog even before briefings exist."""
    list_response = client.get("/api/v1/countries", headers=AUTH_HEADERS)
    missing_detail_response = client.get("/api/v1/countries/BR", headers=AUTH_HEADERS)

    assert list_response.status_code == 200
    countries = list_response.json()
    assert [country["code"] for country in countries] == EXPECTED_MONITORED_COUNTRY_CODES

    assert missing_detail_response.status_code == 404
    assert missing_detail_response.json()["error"] == "Not found"


def test_failed_trigger_keeps_public_status_stable_and_persists_failure_summary(
    client,
    monkeypatch,
) -> None:
    """A failed run should surface a failed public status while keeping private detail internal."""

    def fail_pipeline(*_args, **_kwargs):
        raise pipeline_handler.PipelineExecutionError(
            step_name="synthesise",
            message="Synthetic country synthesis failure.",
            country_codes=["ZA"],
            indicator_codes=["NY.GDP.MKTP.KD.ZG"],
        )

    monkeypatch.setattr(pipeline_handler, "run_pipeline", fail_pipeline)

    trigger_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)
    assert trigger_response.status_code == 202

    deadline = time.monotonic() + 2.0
    final_status = None
    while time.monotonic() < deadline:
        status_response = client.get("/api/v1/pipeline/status", headers=AUTH_HEADERS)
        assert status_response.status_code == 200
        final_status = status_response.json()
        if final_status["status"] == "failed":
            break
        time.sleep(0.02)

    assert final_status is not None
    assert final_status["status"] == "failed"
    assert final_status["error"] == "Synthetic country synthesis failure."
    assert "run_id" not in final_status
    assert "failure_summary" not in final_status

    stored_status = get_repository().get_pipeline_status_record()
    assert stored_status["run_id"]
    assert stored_status["failure_summary"] == {
        "run_id": stored_status["run_id"],
        "step": "synthesise",
        "message": "Synthetic country synthesis failure.",
        "country_codes": ["ZA"],
        "indicator_codes": ["NY.GDP.MKTP.KD.ZG"],
    }


def test_trigger_fails_before_background_run_when_storage_is_misconfigured(
    client,
    monkeypatch,
) -> None:
    """A storage configuration error should fail the run before background execution starts."""
    run_pipeline_called = False

    def unexpected_run(*_args, **_kwargs):
        nonlocal run_pipeline_called
        run_pipeline_called = True

    def raise_storage_error() -> None:
        raise ValueError("Raw archive bucket is required for Firestore mode.")

    monkeypatch.setattr(pipeline_handler, "run_pipeline", unexpected_run)
    monkeypatch.setattr(pipeline_handler, "get_raw_archive_store", raise_storage_error)

    trigger_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert trigger_response.status_code == 202
    assert trigger_response.json()["status"] == "failed"
    assert trigger_response.json()["error"] == "Raw archive bucket is required for Firestore mode."
    assert not run_pipeline_called

    stored_status = get_repository().get_pipeline_status_record()
    assert stored_status["failure_summary"] == {
        "run_id": stored_status["run_id"],
        "step": "store",
        "message": "Raw archive bucket is required for Firestore mode.",
    }
    assert "run_id" not in trigger_response.json()


def test_repository_misconfiguration_returns_failed_status_without_starting_run(
    client,
    monkeypatch,
) -> None:
    """A broken repository configuration should return a failed status immediately."""
    run_pipeline_called = False

    def unexpected_run(*_args, **_kwargs):
        nonlocal run_pipeline_called
        run_pipeline_called = True

    def raise_repository_error() -> None:
        raise ValueError("REPOSITORY_MODE=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID")

    monkeypatch.setattr(pipeline_handler, "run_pipeline", unexpected_run)
    monkeypatch.setattr(pipeline_handler, "get_repository", raise_repository_error)

    trigger_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)
    status_response = client.get("/api/v1/pipeline/status", headers=AUTH_HEADERS)

    assert trigger_response.status_code == 202
    assert trigger_response.json()["status"] == "failed"
    assert (
        trigger_response.json()["error"]
        == "REPOSITORY_MODE=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"
    )
    assert "run_id" not in trigger_response.json()

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "failed"
    assert (
        status_response.json()["error"]
        == "REPOSITORY_MODE=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"
    )
    assert "run_id" not in status_response.json()
    assert not run_pipeline_called


def test_partial_live_trigger_preserves_country_detail_and_marks_fetch_failed(
    client,
    monkeypatch,
    tmp_path,
) -> None:
    """A partial live run should keep good ZA output while the public status fails."""
    failing_indicator_code = "GC.DOD.TOTL.GD.ZS"
    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(
        pipeline_main,
        "fetch_live_data",
        lambda country_codes, run_id=None: _build_partial_live_fetch_result(
            run_id=run_id or "api-live-run",
            failing_indicator_code=failing_indicator_code,
        ),
    )

    trigger_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)
    assert trigger_response.status_code == 202

    deadline = time.monotonic() + 2.0
    final_status = None
    while time.monotonic() < deadline:
        status_response = client.get("/api/v1/pipeline/status", headers=AUTH_HEADERS)
        assert status_response.status_code == 200
        final_status = status_response.json()
        if final_status["status"] != "running":
            break
        time.sleep(0.02)

    assert final_status is not None
    assert final_status["status"] == "failed"
    assert "incomplete coverage" in final_status["error"]
    assert any(
        step["name"] == "fetch" and step["status"] == "failed"
        for step in final_status["steps"]
    )

    detail_response = client.get("/api/v1/countries/ZA", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["indicators"]) == len(INDICATORS) - 1
    assert "government debt to n/a" not in detail["macro_synthesis"].lower()
    assert "government debt data is unavailable in the live source" in detail["macro_synthesis"]
    assert any(
        "Government debt data is unavailable in the live source" in flag
        for flag in detail["risk_flags"]
    )
    assert all(
        indicator["indicator_code"] != failing_indicator_code
        for indicator in detail["indicators"]
    )

    stored_status = get_repository().get_pipeline_status_record()
    assert stored_status["failure_summary"]["step"] == "fetch"
    assert stored_status["failure_summary"]["indicator_codes"] == [failing_indicator_code]

    raw_archive_path = (
        tmp_path
        / "raw-archives"
        / "runs"
        / stored_status["run_id"]
        / "raw"
        / "NY.GDP.MKTP.KD.ZG.json"
    )
    archived_payload = json.loads(raw_archive_path.read_text(encoding="utf-8"))
    assert archived_payload["indicator_code"] == "NY.GDP.MKTP.KD.ZG"
    assert archived_payload["request"]["params"]["date"] == LIVE_DATE_RANGE
    assert archived_payload["request"]["params"]["source"] == WORLD_BANK_SOURCE_ID


def _build_partial_live_fetch_result(run_id: str, failing_indicator_code: str) -> LiveFetchResult:
    """Build a partial live fetch fixture for trigger/status regression tests."""
    live_points, raw_payloads = _build_live_points_and_payloads()
    return LiveFetchResult(
        data_points=[
            point
            for point in live_points
            if point["indicator_code"] != failing_indicator_code
        ],
        raw_payloads={
            indicator_code: payload
            for indicator_code, payload in raw_payloads.items()
            if indicator_code != failing_indicator_code
        },
        failures=(
            WorldBankFetchError(
                message=(
                    f"run_id={run_id} indicator_code={failing_indicator_code} country_codes=ZA: "
                    "World Bank returned no usable rows for the configured live indicator"
                ),
                indicator_code=failing_indicator_code,
                country_codes=["ZA"],
                run_id=run_id,
            ),
        ),
    )


def _build_live_points_and_payloads() -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    """Build deterministic live-like ZA payloads from the local fixture slice."""
    local_points = load_local_data_points("ZA")
    metadata = {
        "page": 1,
        "pages": 1,
        "per_page": 1000,
        "total": 7,
        "sourceid": "2",
        "lastupdated": "2026-03-31",
    }

    live_points: list[dict[str, object]] = []
    raw_payloads: dict[str, dict[str, object]] = {}
    for indicator_code, indicator_name in INDICATORS.items():
        indicator_points = [
            {
                **point,
                "source_name": WORLD_BANK_SOURCE_NAME,
                "source_date_range": LIVE_DATE_RANGE,
                "source_last_updated": "2026-03-31",
                "source_id": "2",
            }
            for point in local_points
            if point["indicator_code"] == indicator_code
        ]
        live_points.extend(indicator_points)
        raw_payloads[indicator_code] = {
            "source_name": WORLD_BANK_SOURCE_NAME,
            "source_date_range": LIVE_DATE_RANGE,
            "source_last_updated": "2026-03-31",
            "source_id": "2",
            "indicator_code": indicator_code,
            "indicator_name": indicator_name,
            "country_codes": ["ZA"],
            "request": {
                "url": (
                    f"https://api.worldbank.org/v2/country/za/indicator/{indicator_code}"
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
            "response_body": [
                metadata,
                [_build_world_bank_row(point, indicator_name) for point in indicator_points],
            ],
        }

    return live_points, raw_payloads


def _build_world_bank_row(point: dict[str, object], indicator_name: str) -> dict[str, object]:
    """Convert one normalized ZA fixture row into a World Bank-like raw row."""
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
