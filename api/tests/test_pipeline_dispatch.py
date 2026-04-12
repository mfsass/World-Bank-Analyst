"""Contract tests for explicit Cloud Run Job dispatch configuration."""

from __future__ import annotations

import pytest

from api import pipeline_dispatch


def test_dispatch_mode_defaults_to_local_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repo defaults should keep manual trigger dispatch on the local path."""
    monkeypatch.delenv(pipeline_dispatch.PIPELINE_DISPATCH_MODE_ENV, raising=False)

    assert pipeline_dispatch.get_pipeline_dispatch_mode() == "local"


def test_cloud_dispatch_requires_explicit_job_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud dispatch should fail fast when the Cloud Run Job target is incomplete."""
    monkeypatch.setenv(
        pipeline_dispatch.PIPELINE_JOB_PROJECT_ID_ENV, "world-bank-analyst"
    )
    monkeypatch.delenv(pipeline_dispatch.PIPELINE_JOB_REGION_ENV, raising=False)
    monkeypatch.delenv(pipeline_dispatch.PIPELINE_JOB_NAME_ENV, raising=False)

    with pytest.raises(ValueError, match="WORLD_ANALYST_PIPELINE_JOB_REGION"):
        pipeline_dispatch.ensure_cloud_run_job_configured()


def test_cloud_run_job_request_passes_claimed_run_context() -> None:
    """A dispatched job should receive the claimed run id and requested country code."""
    request_body = pipeline_dispatch._build_run_job_request(
        run_id="run-123",
        country_code="BR",
        container_name="pipeline",
    )

    assert request_body == {
        "overrides": {
            "containerOverrides": [
                {
                    "name": "pipeline",
                    "env": [
                        {"name": "WORLD_ANALYST_PIPELINE_RUN_ID", "value": "run-123"},
                        {"name": "WORLD_ANALYST_PIPELINE_COUNTRY_CODE", "value": "BR"},
                    ],
                }
            ]
        }
    }
