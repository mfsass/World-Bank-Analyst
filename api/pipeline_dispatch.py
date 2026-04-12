"""Dispatch helpers for manual pipeline trigger execution."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession

logger = logging.getLogger(__name__)

PIPELINE_DISPATCH_MODE_ENV = "WORLD_ANALYST_PIPELINE_DISPATCH_MODE"
PIPELINE_JOB_PROJECT_ID_ENV = "WORLD_ANALYST_PIPELINE_JOB_PROJECT_ID"
PIPELINE_JOB_REGION_ENV = "WORLD_ANALYST_PIPELINE_JOB_REGION"
PIPELINE_JOB_NAME_ENV = "WORLD_ANALYST_PIPELINE_JOB_NAME"
PIPELINE_JOB_CONTAINER_NAME_ENV = "WORLD_ANALYST_PIPELINE_JOB_CONTAINER_NAME"


@dataclass(frozen=True)
class CloudRunJobDispatchConfig:
    """Explicit Cloud Run Job dispatch configuration."""

    project_id: str
    region: str
    job_name: str
    container_name: str | None = None


def get_pipeline_dispatch_mode() -> str:
    """Resolve the configured trigger dispatch mode.

    Returns:
        Normalized dispatch mode name.

    Raises:
        ValueError: If the configured mode is unsupported.
    """
    requested_mode = os.environ.get(PIPELINE_DISPATCH_MODE_ENV, "local").strip().lower()
    if requested_mode in {"local", "cloud"}:
        return requested_mode

    raise ValueError(
        f"{PIPELINE_DISPATCH_MODE_ENV} must be 'local' or 'cloud', got '{requested_mode}'."
    )


def dispatch_cloud_run_job(*, run_id: str, country_code: str) -> dict[str, Any]:
    """Dispatch one Cloud Run Job execution for the pipeline.

    Args:
        run_id: Claimed pipeline run identifier.
        country_code: Requested country code for the pipeline entry point.

    Returns:
        Parsed long-running operation payload from the Jobs API.
    """
    config = _load_cloud_run_job_config()
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    url = (
        "https://run.googleapis.com/v2/projects/"
        f"{config.project_id}/locations/{config.region}/jobs/{config.job_name}:run"
    )
    response = session.post(
        url,
        json=_build_run_job_request(
            run_id=run_id,
            country_code=country_code,
            container_name=config.container_name,
        ),
        timeout=30,
    )
    response.raise_for_status()
    operation = response.json()
    logger.info(
        "Dispatched Cloud Run Job %s in %s for run %s (operation=%s)",
        config.job_name,
        config.region,
        run_id,
        operation.get("name"),
    )
    return operation


def ensure_cloud_run_job_configured() -> None:
    """Validate that cloud dispatch has the explicit job config it needs."""
    _load_cloud_run_job_config()


def _load_cloud_run_job_config() -> CloudRunJobDispatchConfig:
    """Load the explicit Cloud Run Job dispatch configuration."""
    project_id = os.environ.get(PIPELINE_JOB_PROJECT_ID_ENV, "").strip()
    region = os.environ.get(PIPELINE_JOB_REGION_ENV, "").strip()
    job_name = os.environ.get(PIPELINE_JOB_NAME_ENV, "").strip()
    container_name = os.environ.get(PIPELINE_JOB_CONTAINER_NAME_ENV, "").strip() or None

    missing = [
        env_name
        for env_name, value in (
            (PIPELINE_JOB_PROJECT_ID_ENV, project_id),
            (PIPELINE_JOB_REGION_ENV, region),
            (PIPELINE_JOB_NAME_ENV, job_name),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            "Cloud dispatch requires explicit job configuration: "
            f"{', '.join(missing)}."
        )

    return CloudRunJobDispatchConfig(
        project_id=project_id,
        region=region,
        job_name=job_name,
        container_name=container_name,
    )


def _build_run_job_request(
    *,
    run_id: str,
    country_code: str,
    container_name: str | None,
) -> dict[str, Any]:
    """Build the Cloud Run Jobs API run request body."""
    container_override: dict[str, Any] = {
        "env": [
            {"name": "WORLD_ANALYST_PIPELINE_RUN_ID", "value": run_id},
            {"name": "WORLD_ANALYST_PIPELINE_COUNTRY_CODE", "value": country_code},
        ]
    }
    if container_name:
        container_override["name"] = container_name

    return {"overrides": {"containerOverrides": [container_override]}}
