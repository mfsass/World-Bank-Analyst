"""Business tests for the first local vertical slice."""

from __future__ import annotations

import time

from handlers import pipeline as pipeline_handler
from shared.repository import get_repository

AUTH_HEADERS = {"X-API-Key": "local-dev"}


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
