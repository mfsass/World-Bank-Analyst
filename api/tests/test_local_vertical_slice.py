"""Business tests for the first local vertical slice."""

from __future__ import annotations

import time

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

    detail_response = client.get("/api/v1/countries/ZA", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    detail = detail_response.json()

    assert detail["code"] == "ZA"
    assert detail["name"] == "South Africa"
    assert len(detail["indicators"]) == 6
    assert detail["macro_synthesis"]
    assert len(detail["risk_flags"]) >= 2
    assert detail["outlook"] in {"cautious", "bearish"}


def test_country_detail_returns_not_found_before_trigger(client) -> None:
    """Country detail should not exist before the local slice has run."""
    response = client.get("/api/v1/countries/ZA", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"] == "Not found"
