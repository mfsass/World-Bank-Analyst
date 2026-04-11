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

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    # Keep the local slice runnable without packaging the repo as an installed module.
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.main import run_pipeline
from shared.repository import build_pipeline_steps, get_repository

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
    repository = get_repository()

    with _TRIGGER_LOCK:
        current_status = repository.get_pipeline_status()
        if current_status["status"] == "running":
            return current_status, 409

        _STEP_STARTED_AT.clear()
        repository.upsert_pipeline_status(
            {
                "status": "running",
                "started_at": _utc_now(),
                "steps": build_pipeline_steps(),
            }
        )
        # Return 202 immediately while the background run updates repository-backed status.
        Thread(target=_execute_local_pipeline, daemon=True).start()

    return repository.get_pipeline_status(), 202


def get_status() -> tuple[dict[str, Any], int]:
    """Return current pipeline execution status.

    Returns:
        Tuple of (pipeline_status, 200).
    """
    logger.info("Pipeline status requested")
    repository = get_repository()
    return repository.get_pipeline_status(), 200


def _execute_local_pipeline() -> None:
    """Run the local pipeline asynchronously and update ephemeral status."""
    repository = get_repository()
    try:
        run_pipeline(repository=repository, step_callback=_update_step_status)
        status = repository.get_pipeline_status()
        status["status"] = "complete"
        status["completed_at"] = _utc_now()
        status.pop("error", None)
        repository.upsert_pipeline_status(status)
    except Exception as exc:
        logger.exception("Local pipeline execution failed")
        failed_status = repository.get_pipeline_status()
        for step in failed_status.get("steps", []):
            if step.get("status") == "running":
                step["status"] = "failed"
        failed_status["status"] = "failed"
        failed_status["completed_at"] = _utc_now()
        failed_status["error"] = str(exc)
        repository.upsert_pipeline_status(failed_status)


def _update_step_status(step_name: str, step_status: str) -> None:
    """Update a single step inside the shared pipeline status payload.

    Args:
        step_name: Pipeline step name.
        step_status: New step status.
    """
    repository = get_repository()
    status = repository.get_pipeline_status()
    for step in status.get("steps", []):
        if step.get("name") != step_name:
            continue
        step["status"] = step_status
        if step_status == "running":
            _STEP_STARTED_AT[step_name] = perf_counter()
            step.pop("duration_ms", None)
        elif step_status in {"complete", "failed"} and step_name in _STEP_STARTED_AT:
            step["duration_ms"] = int((perf_counter() - _STEP_STARTED_AT.pop(step_name)) * 1000)
        break
    repository.upsert_pipeline_status(status)


def _utc_now() -> str:
    """Return the current UTC timestamp as an ISO string.

    Returns:
        ISO-formatted UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat()
