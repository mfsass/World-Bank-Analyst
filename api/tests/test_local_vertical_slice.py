"""Business tests for the first local vertical slice."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pipeline.main as pipeline_main
from pipeline.dev_ai_adapter import create_development_client
from pipeline.fetcher import (
    INDICATORS,
    LIVE_DATE_RANGE,
    WORLD_BANK_SOURCE_ID,
    WORLD_BANK_SOURCE_NAME,
    LiveFetchResult,
    WorldBankFetchError,
)
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


class StubLiveAIClient:
    """Deterministic test double for live AI wiring in API trigger tests."""

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
        return result

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        result = self._delegate.synthesise_country(indicators)
        result["ai_provenance"].update(
            {
                "provider": "stub-live-provider",
                "model": "stub-live-model",
            }
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
        return result

    def get_provenance(self) -> dict[str, str]:
        return {
            "provider": "stub-live-provider",
            "model": "stub-live-model",
        }


class DegradingStubLiveAIClient(StubLiveAIClient):
    """Return one explicit degraded fallback so public status honesty can be tested."""

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


def test_trigger_status_transition_and_country_detail_flow(client) -> None:
    """Triggering the local slice should materialise a BR country briefing."""
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
    assert any(
        step["name"] == "store" and step["status"] == "complete"
        for step in final_status["steps"]
    )
    assert "run_id" not in final_status
    assert "failure_summary" not in final_status

    detail_response = client.get("/api/v1/countries/BR", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()

    assert detail["code"] == "BR"
    assert detail["name"] == "Brazil"
    assert len(detail["indicators"]) == 6
    assert detail["macro_synthesis"]
    assert len(detail["risk_flags"]) >= 2
    assert detail["outlook"] in {"cautious", "bearish", "neutral", "bullish"}
    assert detail["regime_label"] in {
        "recovery",
        "expansion",
        "overheating",
        "contraction",
        "stagnation",
    }
    assert detail["source_date_range"] == "2017:2023"
    assert all(indicator["time_series"] for indicator in detail["indicators"])
    assert all(indicator["time_series"][0]["year"] == 2017 for indicator in detail["indicators"])
    assert all(indicator["time_series"][-1]["year"] == 2023 for indicator in detail["indicators"])
    assert all("change_value" in indicator for indicator in detail["indicators"])
    assert all("change_basis" in indicator for indicator in detail["indicators"])
    assert all("signal_polarity" in indicator for indicator in detail["indicators"])
    assert all(
        "change_value" in indicator["time_series"][-1]
        for indicator in detail["indicators"]
    )
    assert all(
        "change_basis" in indicator["time_series"][-1]
        for indicator in detail["indicators"]
    )
    assert "run_id" not in detail
    assert "raw_backup_reference" not in detail
    assert all("run_id" not in indicator for indicator in detail["indicators"])
    assert all(
        "source_provenance" not in indicator for indicator in detail["indicators"]
    )

    overview_response = client.get("/api/v1/overview", headers=AUTH_HEADERS)
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["summary"]
    assert overview["country_count"] == 1
    assert overview["country_codes"] == ["BR"]
    assert overview["source_date_range"] == "2017:2023"
    assert "run_id" not in overview
    assert "raw_backup_reference" not in overview


def test_country_detail_returns_not_found_before_trigger(client) -> None:
    """Country detail should not exist before the local slice has run."""
    response = client.get("/api/v1/countries/BR", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"] == "Not found"


def test_overview_returns_not_found_before_trigger(client) -> None:
    """The monitored-set overview should not exist before the local slice has run."""
    response = client.get("/api/v1/overview", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"] == "Not found"


def test_countries_endpoint_returns_monitored_catalog_before_materialisation(
    client,
) -> None:
    """The country list should expose the monitored catalog even before briefings exist."""
    list_response = client.get("/api/v1/countries", headers=AUTH_HEADERS)
    missing_detail_response = client.get("/api/v1/countries/BR", headers=AUTH_HEADERS)

    assert list_response.status_code == 200
    countries = list_response.json()
    assert [
        country["code"] for country in countries
    ] == EXPECTED_MONITORED_COUNTRY_CODES

    assert missing_detail_response.status_code == 404
    assert missing_detail_response.json()["error"] == "Not found"


def test_failed_trigger_keeps_public_status_stable_and_persists_failure_summary(
    client,
    monkeypatch,
) -> None:
    """A failed run should surface a failed public status while keeping private detail internal."""

    def fail_pipeline(*_args, **_kwargs):
        raise pipeline_main.PipelineExecutionError(
            step_name="synthesise",
            message="Synthetic country synthesis failure.",
            country_codes=["ZA"],
            indicator_codes=["NY.GDP.MKTP.KD.ZG"],
        )

    # The trigger now calls run_managed_pipeline, which owns durable status writes
    # while delegating the business execution path to run_pipeline.
    monkeypatch.setattr(pipeline_main, "run_pipeline", fail_pipeline)

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
    local_thread_started = False

    def unexpected_start(*_args, **_kwargs):
        nonlocal local_thread_started
        local_thread_started = True

    def raise_storage_error() -> None:
        raise ValueError("Raw archive bucket is required for Firestore mode.")

    monkeypatch.setattr(
        pipeline_handler, "_start_local_pipeline_thread", unexpected_start
    )
    monkeypatch.setattr(pipeline_handler, "get_raw_archive_store", raise_storage_error)

    trigger_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert trigger_response.status_code == 202
    assert trigger_response.json()["status"] == "failed"
    assert (
        trigger_response.json()["error"]
        == "Raw archive bucket is required for Firestore mode."
    )
    assert not local_thread_started

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
    local_thread_started = False

    def unexpected_start(*_args, **_kwargs):
        nonlocal local_thread_started
        local_thread_started = True

    def raise_repository_error() -> None:
        raise ValueError(
            "REPOSITORY_MODE=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"
        )

    monkeypatch.setattr(
        pipeline_handler, "_start_local_pipeline_thread", unexpected_start
    )
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
    assert not local_thread_started


def test_cloud_dispatch_mode_claims_running_status_before_dispatch(
    client, monkeypatch
) -> None:
    """Cloud dispatch should keep the public contract while claiming one durable run."""
    dispatched: dict[str, str] = {}
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_DISPATCH_MODE", "cloud")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID", "world-bank-analyst")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_REGION", "europe-west1")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_NAME", "world-analyst-pipeline")

    def fake_dispatch_cloud_run_job(
        *, run_id: str, country_code: str
    ) -> dict[str, str]:
        dispatched["run_id"] = run_id
        dispatched["country_code"] = country_code
        return {"name": "operations/dispatch-123"}

    monkeypatch.setattr(
        pipeline_handler,
        "dispatch_cloud_run_job",
        fake_dispatch_cloud_run_job,
    )

    response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert "run_id" not in response.json()
    assert dispatched["country_code"] == "ZA"
    stored_status = get_repository().get_pipeline_status_record()
    assert stored_status["status"] == "running"
    assert stored_status["run_id"] == dispatched["run_id"]


def test_cloud_dispatch_mode_refuses_duplicate_manual_run(client, monkeypatch) -> None:
    """A second cloud trigger should refuse to dispatch while a run is already active."""
    dispatch_called = False
    repository = get_repository()
    repository.upsert_pipeline_status(
        {
            "status": "running",
            "run_id": "existing-cloud-run",
            "started_at": "2026-04-12T12:00:00+00:00",
            "steps": [{"name": "fetch", "status": "running"}],
        }
    )
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_DISPATCH_MODE", "cloud")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID", "world-bank-analyst")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_REGION", "europe-west1")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_NAME", "world-analyst-pipeline")

    def unexpected_dispatch(**_kwargs) -> None:
        nonlocal dispatch_called
        dispatch_called = True

    monkeypatch.setattr(pipeline_handler, "dispatch_cloud_run_job", unexpected_dispatch)

    response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert response.status_code == 409
    assert response.json()["status"] == "running"
    assert "run_id" not in response.json()
    assert not dispatch_called


def test_trigger_returns_429_when_last_completed_run_is_within_cooldown(
    client, monkeypatch
) -> None:
    """A recently completed run should publish a retry window instead of starting again."""
    repository = get_repository()
    completed_at = datetime.now(timezone.utc) - timedelta(seconds=120)
    repository.upsert_pipeline_status(
        {
            "status": "complete",
            "started_at": (completed_at - timedelta(minutes=5)).isoformat(),
            "completed_at": completed_at.isoformat(),
            "steps": [{"name": "store", "status": "complete"}],
        }
    )
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_COOLDOWN_SECONDS", "600")

    local_thread_started = False

    def unexpected_start(*_args, **_kwargs) -> None:
        nonlocal local_thread_started
        local_thread_started = True

    monkeypatch.setattr(
        pipeline_handler, "_start_local_pipeline_thread", unexpected_start
    )

    response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert response.status_code == 429
    response_body = response.json()
    assert response.headers["Retry-After"] == str(response_body["retry_after_seconds"])
    assert response_body["error"] == (
        "Pipeline run too recent. "
        f"Last run completed at {completed_at.isoformat()}."
    )
    assert 1 <= response_body["retry_after_seconds"] <= 480
    assert not local_thread_started
    assert repository.get_pipeline_status_record()["status"] == "complete"


def test_trigger_starts_when_last_completed_run_is_outside_cooldown(
    client, monkeypatch
) -> None:
    """A cooled-down completed run should allow a fresh manual trigger."""
    repository = get_repository()
    completed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    repository.upsert_pipeline_status(
        {
            "status": "complete",
            "started_at": (completed_at - timedelta(minutes=5)).isoformat(),
            "completed_at": completed_at.isoformat(),
            "steps": [{"name": "store", "status": "complete"}],
        }
    )
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_COOLDOWN_SECONDS", "600")

    started_run: dict[str, str] = {}

    def fake_start_local_pipeline_thread(
        *, run_id: str, raw_archive_store: Any | None
    ) -> None:
        started_run["run_id"] = run_id
        started_run["raw_archive_store"] = "configured" if raw_archive_store else "missing"

    monkeypatch.setattr(
        pipeline_handler,
        "_start_local_pipeline_thread",
        fake_start_local_pipeline_thread,
    )

    response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert "run_id" not in response.json()
    assert started_run["run_id"]
    assert started_run["raw_archive_store"] == "configured"
    assert repository.get_pipeline_status_record()["status"] == "running"


def test_cloud_dispatch_preflight_failure_returns_failed_status(
    client, monkeypatch
) -> None:
    """Cloud dispatch should fail fast when explicit job config is incomplete."""
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_DISPATCH_MODE", "cloud")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID", "world-bank-analyst")
    monkeypatch.delenv("WORLD_ANALYST_PIPELINE_JOB_REGION", raising=False)
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_NAME", "world-analyst-pipeline")

    response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert "WORLD_ANALYST_PIPELINE_JOB_REGION" in response.json()["error"]
    assert "run_id" not in response.json()


def test_cloud_dispatch_failure_after_claim_releases_the_trigger_slot(
    client, monkeypatch
) -> None:
    """A failed Cloud Run dispatch should publish failure and allow a later retry."""
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_DISPATCH_MODE", "cloud")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID", "world-bank-analyst")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_REGION", "europe-west1")
    monkeypatch.setenv("WORLD_ANALYST_PIPELINE_JOB_NAME", "world-analyst-pipeline")

    def fail_dispatch(**_kwargs) -> None:
        raise RuntimeError("Synthetic Cloud Run dispatch failure.")

    monkeypatch.setattr(pipeline_handler, "dispatch_cloud_run_job", fail_dispatch)

    failed_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert failed_response.status_code == 202
    assert failed_response.json()["status"] == "failed"
    assert failed_response.json()["error"] == "Synthetic Cloud Run dispatch failure."
    stored_status = get_repository().get_pipeline_status_record()
    assert stored_status["failure_summary"] == {
        "run_id": stored_status["run_id"],
        "step": "dispatch",
        "message": "Synthetic Cloud Run dispatch failure.",
    }

    monkeypatch.setattr(
        pipeline_handler,
        "dispatch_cloud_run_job",
        lambda **_kwargs: {"name": "operations/retry-123"},
    )

    retry_response = client.post("/api/v1/pipeline/trigger", headers=AUTH_HEADERS)

    assert retry_response.status_code == 202
    assert retry_response.json()["status"] == "running"


def test_partial_live_trigger_preserves_country_detail_and_marks_fetch_failed(
    client,
    monkeypatch,
    tmp_path,
) -> None:
    """A partial live run should keep good BR output while the public status fails."""
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
    monkeypatch.setattr(
        pipeline_main, "create_client", lambda provider=None: StubLiveAIClient()
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

    detail_response = client.get("/api/v1/countries/BR", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["indicators"]) == len(INDICATORS) - 1
    assert "government debt to n/a" not in detail["macro_synthesis"].lower()
    assert (
        "government debt data is unavailable in the live source"
        in detail["macro_synthesis"]
    )
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
    assert stored_status["failure_summary"]["indicator_codes"] == [
        failing_indicator_code
    ]

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


def test_live_trigger_preserves_outputs_but_fails_status_when_ai_degrades(
    client,
    monkeypatch,
) -> None:
    """A degraded live AI fallback should keep output while the public run status stays failed."""
    degraded_indicator_code = "NY.GDP.MKTP.KD.ZG"
    live_points, raw_payloads = _build_live_points_and_payloads()
    monkeypatch.setenv("PIPELINE_MODE", "live")
    monkeypatch.setattr(
        pipeline_main,
        "fetch_live_data",
        lambda country_codes, run_id=None: LiveFetchResult(
            data_points=live_points,
            raw_payloads=raw_payloads,
            failures=(),
        ),
    )
    monkeypatch.setattr(
        pipeline_main,
        "create_client",
        lambda provider=None: DegradingStubLiveAIClient(degraded_indicator_code),
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
    assert "degraded coverage" in final_status["error"]
    assert any(
        step["name"] == "synthesise" and step["status"] == "failed"
        for step in final_status["steps"]
    )
    assert any(
        step["name"] == "store" and step["status"] == "complete"
        for step in final_status["steps"]
    )

    detail_response = client.get("/api/v1/countries/BR", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    stored_status = get_repository().get_pipeline_status_record()
    assert stored_status["failure_summary"]["step"] == "synthesise"
    assert (
        degraded_indicator_code in stored_status["failure_summary"]["indicator_codes"]
    )


def _build_partial_live_fetch_result(
    run_id: str, failing_indicator_code: str
) -> LiveFetchResult:
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
                    f"run_id={run_id} indicator_code={failing_indicator_code} country_codes=BR: "
                    "World Bank returned no usable rows for the configured live indicator"
                ),
                indicator_code=failing_indicator_code,
                country_codes=["BR"],
                run_id=run_id,
            ),
        ),
    )


def _build_live_points_and_payloads() -> (
    tuple[list[dict[str, object]], dict[str, dict[str, object]]]
):
    """Build deterministic live-like BR payloads from the local fixture slice."""
    local_points = load_local_data_points("BR")
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
            "country_codes": ["BR"],
            "request": {
                "url": (
                    f"https://api.worldbank.org/v2/country/br/indicator/{indicator_code}"
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
                [
                    _build_world_bank_row(point, indicator_name)
                    for point in indicator_points
                ],
            ],
        }

    return live_points, raw_payloads


def _build_world_bank_row(
    point: dict[str, object], indicator_name: str
) -> dict[str, object]:
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
