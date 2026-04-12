"""Pipeline trigger and status handlers.

Provides manual pipeline execution and status polling endpoints.
"""

from datetime import datetime, timezone
import logging
import sys
from pathlib import Path
from threading import Lock, Thread
from time import perf_counter
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    # Keep the local slice runnable without packaging the repo as an installed module.
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.local_data import LOCAL_DEV_COUNTRY  # noqa: E402
from pipeline.main import PipelineExecutionError, run_pipeline  # noqa: E402
from pipeline.storage import get_raw_archive_store  # noqa: E402
from shared.repository import build_pipeline_steps, get_repository, project_public_record  # noqa: E402

logger = logging.getLogger(__name__)

_TRIGGER_LOCK = Lock()
_STEP_STARTED_AT: dict[str, float] = {}


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
        return _project_public_status(_build_preflight_failure_status(run_id, str(exc))), 202

    with _TRIGGER_LOCK:
        current_status = repository.get_pipeline_status()
        if current_status["status"] == "running":
            return current_status, 409

        try:
            get_raw_archive_store()
        except ValueError as exc:
            logger.exception("Pipeline trigger rejected due to storage configuration")
            repository.upsert_pipeline_status(_build_preflight_failure_status(run_id, str(exc)))
            return repository.get_pipeline_status(), 202

        _STEP_STARTED_AT.clear()
        repository.upsert_pipeline_status(
            {
                "status": "running",
                "run_id": run_id,
                "started_at": _utc_now(),
                "steps": build_pipeline_steps(),
            }
        )
        # Return 202 immediately while the background run updates repository-backed status.
        Thread(target=_execute_local_pipeline, args=(run_id,), daemon=True).start()

    return repository.get_pipeline_status(), 202


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
        return _project_public_status(_build_preflight_failure_status(str(uuid4()), str(exc))), 200

    return repository.get_pipeline_status(), 200


def _execute_local_pipeline(run_id: str) -> None:
    """Run the local pipeline asynchronously and update ephemeral status."""
    repository = get_repository()
    try:
        run_pipeline(
            country_code=LOCAL_DEV_COUNTRY,
            repository=repository,
            step_callback=_update_step_status,
            run_id=run_id,
        )
        status = repository.get_pipeline_status_record()
        status["status"] = "complete"
        status["completed_at"] = _utc_now()
        status["error"] = None
        status.pop("failure_summary", None)
        status.pop("error", None)
        repository.upsert_pipeline_status(status)
    except PipelineExecutionError as exc:
        logger.exception("Local pipeline execution failed")
        failed_status = repository.get_pipeline_status_record()
        _mark_failed_step(failed_status, exc.step_name)
        failed_status["status"] = "failed"
        failed_status["completed_at"] = _utc_now()
        failed_status["error"] = str(exc)
        failed_status["failure_summary"] = {
            "run_id": run_id,
            "step": exc.step_name,
            "message": str(exc),
            "country_codes": exc.country_codes,
            "indicator_codes": exc.indicator_codes,
        }
        repository.upsert_pipeline_status(failed_status)
    except Exception as exc:
        logger.exception("Local pipeline execution failed")
        failed_status = repository.get_pipeline_status_record()
        failure_step_name = _find_running_step_name(failed_status)
        _mark_failed_step(failed_status, failure_step_name)
        failed_status["status"] = "failed"
        failed_status["completed_at"] = _utc_now()
        failed_status["error"] = str(exc)
        failed_status["failure_summary"] = {
            "run_id": run_id,
            "step": failure_step_name,
            "message": str(exc),
        }
        repository.upsert_pipeline_status(failed_status)


def _update_step_status(step_name: str, step_status: str) -> None:
    """Update a single step inside the shared pipeline status payload.

    Args:
        step_name: Pipeline step name.
        step_status: New step status.
    """
    repository = get_repository()
    status = repository.get_pipeline_status_record()
    for step in status.get("steps", []):
        if step.get("name") != step_name:
            continue
        step["status"] = step_status
        if step_status == "running":
            step["started_at"] = _utc_now()
            _STEP_STARTED_AT[step_name] = perf_counter()
            step.pop("duration_ms", None)
            step.pop("completed_at", None)
        elif step_status in {"complete", "failed"} and step_name in _STEP_STARTED_AT:
            step["duration_ms"] = int((perf_counter() - _STEP_STARTED_AT.pop(step_name)) * 1000)
            step["completed_at"] = _utc_now()
        break
    repository.upsert_pipeline_status(status)


def _find_running_step_name(status: dict[str, Any]) -> str | None:
    """Return the currently running step name when one exists.

    Args:
        status: Stored pipeline status payload.

    Returns:
        Running step name, else None.
    """
    for step in status.get("steps", []):
        if step.get("status") == "running":
            return step.get("name")
    return None


def _mark_failed_step(status: dict[str, Any], fallback_step_name: str | None) -> None:
    """Mark the most relevant pipeline step as failed.

    Args:
        status: Stored pipeline status payload.
        fallback_step_name: Step name to fail when no step is still running.
    """
    running_step_marked = False
    for step in status.get("steps", []):
        if step.get("status") != "running":
            continue
        _apply_failed_step_state(step)
        running_step_marked = True

    if running_step_marked or fallback_step_name is None:
        return

    for step in status.get("steps", []):
        if step.get("name") != fallback_step_name:
            continue
        _apply_failed_step_state(step)
        break


def _apply_failed_step_state(step: dict[str, Any]) -> None:
    """Set one pipeline step to failed while preserving existing timing data.

    Args:
        step: Mutable pipeline step payload.
    """
    step_name = step.get("name")
    step["status"] = "failed"
    if step_name in _STEP_STARTED_AT:
        step["duration_ms"] = int((perf_counter() - _STEP_STARTED_AT.pop(step_name)) * 1000)
    if not step.get("completed_at"):
        step["completed_at"] = _utc_now()


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
