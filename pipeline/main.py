"""Pipeline entry point.

Orchestrates the current bounded slice: fixture load → analyse → deterministic
AI → repository-backed storage.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.analyser import compute_changes, prepare_llm_context  # noqa: E402
from pipeline.dev_ai_adapter import create_development_client  # noqa: E402
from pipeline.local_data import LOCAL_TARGET_COUNTRY, load_local_data_points  # noqa: E402
from pipeline.storage import RawArchiveStore, store_slice  # noqa: E402
from shared.repository import InsightsRepository, get_repository  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

StepCallback = Callable[[str, str], None]


class PipelineExecutionError(RuntimeError):
    """Pipeline error with step and scope context for durable status updates."""

    def __init__(
        self,
        step_name: str,
        message: str,
        country_codes: list[str] | None = None,
        indicator_codes: list[str] | None = None,
    ) -> None:
        """Initialise the pipeline execution error.

        Args:
            step_name: Pipeline step that failed.
            message: Human-readable failure message.
            country_codes: Affected country scope when known.
            indicator_codes: Affected indicator scope when known.
        """
        super().__init__(message)
        self.step_name = step_name
        self.country_codes = country_codes or []
        self.indicator_codes = indicator_codes or []


def run_pipeline(
    country_code: str = LOCAL_TARGET_COUNTRY,
    repository: InsightsRepository | None = None,
    step_callback: StepCallback | None = None,
    run_id: str | None = None,
    raw_archive_store: RawArchiveStore | None = None,
) -> dict[str, Any]:
    """Execute the local first-slice pipeline.

    The current implementation keeps deterministic local data and AI output,
    but writes through the configured repository backend so API reads can move
    from process-local state to Firestore without changing payload shape.

    Returns:
        Pipeline execution summary dict.
    """
    runtime_mode = os.environ.get("PIPELINE_MODE", "local")
    repo = repository or get_repository()
    normalized_country_code = country_code.upper()
    current_run_id = run_id or str(uuid4())

    if runtime_mode != "local":
        _log_event(
            logging.WARNING,
            "pipeline_mode_fallback",
            requested_mode=runtime_mode,
            run_id=current_run_id,
        )

    _log_event(
        logging.INFO,
        "pipeline_run_started",
        run_id=current_run_id,
        mode="local",
        country_code=normalized_country_code,
    )

    # Step 1: FETCH
    _notify_step(step_callback, "fetch", "running")
    try:
        all_data_points = load_local_data_points(normalized_country_code)
    except Exception as exc:
        raise PipelineExecutionError(
            step_name="fetch",
            message=str(exc),
            country_codes=[normalized_country_code],
        ) from exc
    _log_event(
        logging.INFO,
        "pipeline_fetch_complete",
        run_id=current_run_id,
        data_points_fetched=len(all_data_points),
    )
    _notify_step(step_callback, "fetch", "complete")

    # Step 2: ANALYSE
    _notify_step(step_callback, "analyse", "running")
    try:
        df = compute_changes(all_data_points)
        llm_contexts = prepare_llm_context(df)
    except Exception as exc:
        raise PipelineExecutionError(
            step_name="analyse",
            message=str(exc),
            country_codes=[normalized_country_code],
        ) from exc
    _log_event(
        logging.INFO,
        "pipeline_analysis_complete",
        run_id=current_run_id,
        contexts_prepared=len(llm_contexts),
    )
    _notify_step(step_callback, "analyse", "complete")

    # Step 3: AI (Two-step chain)
    _notify_step(step_callback, "synthesise", "running")
    ai = create_development_client()
    ai_provenance = _resolve_ai_provenance(ai)

    # Step 3a: Per-indicator analysis
    for ctx in llm_contexts:
        try:
            analysis = ai.analyse_indicator(ctx)
        except Exception as exc:
            raise PipelineExecutionError(
                step_name="synthesise",
                message=str(exc),
                country_codes=[ctx["country_code"]],
                indicator_codes=[ctx["indicator_code"]],
            ) from exc
        ctx["ai_analysis"] = analysis["narrative"]
        ctx["trend"] = analysis["trend"]
        ctx["risk_level"] = analysis["risk_level"]
        ctx["confidence"] = analysis["confidence"]

    # Step 3b: Macro synthesis per country
    country_groups: dict[str, list[dict]] = {}
    for ctx in llm_contexts:
        # Preserve the two-step contract: all indicator narratives must exist before country synthesis runs.
        country_groups.setdefault(ctx["country_code"], []).append(ctx)

    country_syntheses: dict[str, dict] = {}
    for country_code, indicators in country_groups.items():
        try:
            synthesis = ai.synthesise_country(indicators)
        except Exception as exc:
            raise PipelineExecutionError(
                step_name="synthesise",
                message=str(exc),
                country_codes=[country_code],
                indicator_codes=[indicator["indicator_code"] for indicator in indicators],
            ) from exc
        country_syntheses[country_code] = synthesis
        _log_event(
            logging.INFO,
            "pipeline_country_synthesis_complete",
            run_id=current_run_id,
            country_code=country_code,
            risk_flags=len(synthesis.get("risk_flags", [])),
        )
    _notify_step(step_callback, "synthesise", "complete")

    # Step 4: STORE
    _notify_step(step_callback, "store", "running")
    try:
        storage_summary = store_slice(
            insights=llm_contexts,
            country_syntheses=country_syntheses,
            raw_data_points=all_data_points,
            run_id=current_run_id,
            ai_provenance=ai_provenance,
            repository=repo,
            raw_archive_store=raw_archive_store,
        )
    except Exception as exc:
        raise PipelineExecutionError(
            step_name="store",
            message=str(exc),
            country_codes=[normalized_country_code],
            indicator_codes=[context["indicator_code"] for context in llm_contexts],
        ) from exc
    _notify_step(step_callback, "store", "complete")

    summary = {
        "run_id": current_run_id,
        "data_points_fetched": len(all_data_points),
        "indicators_analysed": len(llm_contexts),
        "countries_synthesised": len(country_syntheses),
        "anomalies_detected": sum(1 for c in llm_contexts if c.get("is_anomaly")),
        **storage_summary,
    }
    _log_event(logging.INFO, "pipeline_run_complete", run_id=current_run_id, summary=summary)
    return summary


def _notify_step(step_callback: StepCallback | None, name: str, status: str) -> None:
    """Call the optional step callback when status changes.

    Args:
        step_callback: Optional callback from the API trigger flow.
        name: Step name.
        status: Step status.
    """
    if step_callback is not None:
        step_callback(name, status)


def _resolve_ai_provenance(ai_client: Any) -> dict[str, Any] | None:
    """Return minimal AI provenance when the client exposes it.

    Args:
        ai_client: AI client instance.

    Returns:
        Provider and model metadata, or None when unavailable.
    """
    provenance_getter = getattr(ai_client, "get_provenance", None)
    if callable(provenance_getter):
        return provenance_getter()
    return None


def _log_event(level: int, event: str, **fields: Any) -> None:
    """Emit a structured JSON log line.

    Args:
        level: Logging level constant.
        event: Event name.
        **fields: Structured event fields.
    """
    logger.log(level, json.dumps({"event": event, **fields}, default=str, sort_keys=True))


if __name__ == "__main__":
    run_pipeline()
