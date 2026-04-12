"""Pipeline trigger and status handlers."""

from datetime import datetime, timezone
import logging
import sys
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    # Keep the local slice runnable without packaging the repo as an installed module.
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.local_data import LOCAL_DEV_COUNTRY  # noqa: E402
from pipeline.storage import RawArchiveStore, get_raw_archive_store  # noqa: E402
from api.pipeline_dispatch import (  # noqa: E402
    dispatch_cloud_run_job,
    ensure_cloud_run_job_configured,
    get_pipeline_dispatch_mode,
)
from shared.repository import (  # noqa: E402
    build_pipeline_steps,
    get_repository,
    project_public_record,
)

logger = logging.getLogger(__name__)


def trigger() -> tuple[dict[str, Any], int]:
    """Trigger manual pipeline execution.

    Starts the data fetch → analysis → storage pipeline.

    Returns:
        Tuple of (pipeline_status, 202) on success.
    """
    logger.info("Pipeline trigger requested")
    run_id = str(uuid4())
    try:
        repository = get_repository()
    except ValueError as exc:
        logger.exception("Pipeline trigger rejected due to repository configuration")
        return _project_public_status(
            _build_preflight_failure_status(run_id, str(exc))
        ), 202

    try:
        dispatch_mode = get_pipeline_dispatch_mode()
    except ValueError as exc:
        logger.exception("Pipeline trigger rejected due to dispatch-mode configuration")
        failed_status = _build_preflight_failure_status(run_id, str(exc))
        repository.upsert_pipeline_status(failed_status)
        return _project_public_status(failed_status), 202

    raw_archive_store: RawArchiveStore | None = None
    try:
        if dispatch_mode == "local":
            raw_archive_store = get_raw_archive_store()
        else:
            ensure_cloud_run_job_configured()
    except ValueError as exc:
        logger.exception("Pipeline trigger rejected during dispatch preflight")
        failed_status = (
            _build_preflight_failure_status(run_id, str(exc))
            if dispatch_mode == "local"
            else _build_dispatch_failure_status(run_id, str(exc))
        )
        repository.upsert_pipeline_status(failed_status)
        return _project_public_status(failed_status), 202

    claimed_status, claimed = repository.claim_pipeline_run(
        _build_running_status(run_id)
    )
    if not claimed:
        return _project_public_status(claimed_status), 409

    if dispatch_mode == "local":
        _start_local_pipeline_thread(
            run_id=run_id,
            raw_archive_store=raw_archive_store,
        )
        return _project_public_status(claimed_status), 202

    try:
        dispatch_cloud_run_job(run_id=run_id, country_code=LOCAL_DEV_COUNTRY)
    except Exception as exc:
        logger.exception("Cloud pipeline dispatch failed")
        failed_status = _build_dispatch_failure_status(run_id, str(exc))
        repository.upsert_pipeline_status(failed_status)
        return _project_public_status(failed_status), 202

    return _project_public_status(claimed_status), 202


def get_status() -> tuple[dict[str, Any], int]:
    """Return current pipeline execution status.

    Returns:
        Tuple of (pipeline_status, 200).
    """
    logger.info("Pipeline status requested")
    try:
        repository = get_repository()
    except ValueError as exc:
        logger.exception("Pipeline status unavailable due to repository configuration")
        return _project_public_status(
            _build_preflight_failure_status(str(uuid4()), str(exc))
        ), 200

    return repository.get_pipeline_status(), 200


def _start_local_pipeline_thread(
    *, run_id: str, raw_archive_store: RawArchiveStore | None
) -> None:
    """Start the deterministic local pipeline on a background thread."""
    thread = Thread(
        target=_execute_local_pipeline,
        kwargs={"run_id": run_id, "raw_archive_store": raw_archive_store},
        daemon=True,
    )
    thread.start()


def _execute_local_pipeline(
    *, run_id: str, raw_archive_store: RawArchiveStore | None
) -> None:
    """Run the local pipeline asynchronously after the trigger returns 202."""
    from pipeline.main import run_managed_pipeline

    try:
        run_managed_pipeline(
            country_code=LOCAL_DEV_COUNTRY,
            repository=get_repository(),
            run_id=run_id,
            raw_archive_store=raw_archive_store,
            status_already_claimed=True,
        )
    except Exception:
        # run_managed_pipeline already writes the terminal status before returning.
        return


def _build_running_status(run_id: str) -> dict[str, Any]:
    """Build the stored running-status payload for a newly claimed run."""
    return {
        "status": "running",
        "run_id": run_id,
        "started_at": _utc_now(),
        "steps": build_pipeline_steps(),
    }


def _build_preflight_failure_status(run_id: str, message: str) -> dict[str, Any]:
    """Build a failed status payload for trigger-time configuration errors.

    Args:
        run_id: UUID v4 run identifier.
        message: Human-readable failure message.

    Returns:
        Failed pipeline status payload.
    """
    timestamp = _utc_now()
    steps = build_pipeline_steps()
    for step in steps:
        if step["name"] == "store":
            step["status"] = "failed"
            break

    return {
        "status": "failed",
        "run_id": run_id,
        "started_at": timestamp,
        "completed_at": timestamp,
        "steps": steps,
        "error": message,
        "failure_summary": {
            "run_id": run_id,
            "step": "store",
            "message": message,
        },
    }


def _build_dispatch_failure_status(run_id: str, message: str) -> dict[str, Any]:
    """Build a failed status payload for job-dispatch errors."""
    timestamp = _utc_now()
    steps = [{"name": "dispatch", "status": "failed"}, *build_pipeline_steps()]

    return {
        "status": "failed",
        "run_id": run_id,
        "started_at": timestamp,
        "completed_at": timestamp,
        "steps": steps,
        "error": message,
        "failure_summary": {
            "run_id": run_id,
            "step": "dispatch",
            "message": message,
        },
    }


def _project_public_status(status_record: dict[str, Any]) -> dict[str, Any]:
    """Project one internal pipeline status record back to the public API shape.

    Args:
        status_record: Internal pipeline status record.

    Returns:
        Public-facing pipeline status payload.
    """
    return project_public_record({"entity_type": "pipeline_status", **status_record})


def _utc_now() -> str:
    """Return the current UTC timestamp as an ISO string.

    Returns:
        ISO-formatted UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat()
