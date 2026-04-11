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
from pipeline.fetcher import INDICATORS, WorldBankFetchError, fetch_live_data  # noqa: E402
from pipeline.local_data import LOCAL_TARGET_COUNTRY, load_local_data_points  # noqa: E402
from pipeline.storage import RawArchiveStore, store_slice  # noqa: E402
from shared.country_catalog import MONITORED_COUNTRY_CODES  # noqa: E402
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
    """Execute the current pipeline slice for local or live data modes.

    Local mode keeps deterministic fixture data for tests and development.
    Live mode fetches the canonical monitored-country set while preserving the
    same downstream analysis and storage contracts.

    Returns:
        Pipeline execution summary dict.
    """
    runtime_mode = _resolve_pipeline_mode()
    repo = repository or get_repository()
    normalized_country_code = country_code.upper()
    current_run_id = run_id or str(uuid4())
    target_country_codes = [normalized_country_code]

    _log_event(
        logging.INFO,
        "pipeline_run_started",
        run_id=current_run_id,
        mode=runtime_mode,
        requested_country_code=normalized_country_code,
    )

    # Step 1: FETCH
    _notify_step(step_callback, "fetch", "running")
    try:
        target_country_codes = _resolve_target_country_codes(
            runtime_mode=runtime_mode,
            requested_country_code=normalized_country_code,
        )
        all_data_points, raw_fetch_payloads, fetch_failures = _fetch_pipeline_data(
            runtime_mode=runtime_mode,
            country_codes=target_country_codes,
            run_id=current_run_id,
        )
    except WorldBankFetchError as exc:
        raise PipelineExecutionError(
            step_name="fetch",
            message=str(exc),
            country_codes=exc.country_codes or target_country_codes,
            indicator_codes=[exc.indicator_code] if exc.indicator_code else None,
        ) from exc
    except Exception as exc:
        raise PipelineExecutionError(
            step_name="fetch",
            message=str(exc),
            country_codes=target_country_codes,
        ) from exc
    if not all_data_points:
        failure_message = _build_live_failure_message(
            run_id=current_run_id,
            country_codes=target_country_codes,
            fetch_failures=fetch_failures,
        )
        raise PipelineExecutionError(
            step_name="fetch",
            message=failure_message or (
                f"run_id={current_run_id} mode={runtime_mode} returned no usable data "
                f"for {_build_country_scope_label(target_country_codes)}"
            ),
            country_codes=_get_failure_country_codes(fetch_failures) or target_country_codes,
            indicator_codes=_get_failure_indicator_codes(fetch_failures),
        )
    _log_event(
        logging.INFO,
        "pipeline_fetch_complete",
        run_id=current_run_id,
        mode=runtime_mode,
        country_codes=target_country_codes,
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
            country_codes=_get_country_codes_from_records(all_data_points) or target_country_codes,
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
            raw_fetch_payloads=raw_fetch_payloads,
            run_id=current_run_id,
            ai_provenance=ai_provenance,
            repository=repo,
            raw_archive_store=raw_archive_store,
        )
    except Exception as exc:
        raise PipelineExecutionError(
            step_name="store",
            message=str(exc),
            country_codes=_get_country_codes_from_records(llm_contexts) or target_country_codes,
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
    if runtime_mode == "live" and fetch_failures:
        incomplete_coverage_message = _build_live_failure_message(
            run_id=current_run_id,
            country_codes=target_country_codes,
            fetch_failures=fetch_failures,
        )
        _log_event(
            logging.WARNING,
            "pipeline_live_fetch_incomplete",
            run_id=current_run_id,
            requested_country_codes=target_country_codes,
            country_codes=_get_failure_country_codes(fetch_failures),
            indicator_codes=_get_failure_indicator_codes(fetch_failures),
            failures=[str(failure) for failure in fetch_failures],
        )
        raise PipelineExecutionError(
            step_name="fetch",
            message=incomplete_coverage_message,
            country_codes=_get_failure_country_codes(fetch_failures) or target_country_codes,
            indicator_codes=_get_failure_indicator_codes(fetch_failures),
        )
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


def _resolve_pipeline_mode() -> str:
    """Resolve the configured pipeline runtime mode.

    Returns:
        Supported runtime mode name.
    """
    # Default to "live" so deployed Cloud Run Jobs run the real fetch path without
    # requiring an explicit env var. Set PIPELINE_MODE=local to use the ZA fixture
    # for local development or deterministic CI runs.
    requested_mode = os.environ.get("PIPELINE_MODE", "live").lower()
    if requested_mode in {"local", "live"}:
        return requested_mode

    _log_event(logging.WARNING, "pipeline_mode_fallback", requested_mode=requested_mode)
    return "live"


def _fetch_pipeline_data(
    runtime_mode: str,
    country_codes: list[str],
    run_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[WorldBankFetchError]]:
    """Load the pipeline input data for the selected runtime mode.

    Args:
        runtime_mode: Selected pipeline mode.
        country_codes: ISO 3166-1 alpha-2 country codes in scope.
        run_id: Pipeline run identifier.

    Returns:
        Normalized data points, optional raw fetch payloads, and live fetch failures.
    """
    if runtime_mode == "live":
        live_fetch = fetch_live_data(country_codes=country_codes, run_id=run_id)
        return live_fetch.data_points, live_fetch.raw_payloads, list(live_fetch.failures)

    return load_local_data_points(country_codes[0]), None, []


def _resolve_target_country_codes(
    runtime_mode: str,
    requested_country_code: str,
) -> list[str]:
    """Return the country scope for the selected runtime mode.

    Live mode always runs the canonical monitored set so the trigger path,
    repository metadata, and country listing stay aligned. Local mode keeps the
    deterministic ZA fixture slice.

    Args:
        runtime_mode: Selected pipeline mode.
        requested_country_code: Country code passed into the pipeline entry point.

    Returns:
        Country codes to fetch for this run.

    Raises:
        ValueError: If an explicit live-mode country code is outside the monitored set.
    """
    if runtime_mode != "live":
        return [requested_country_code]

    if requested_country_code == LOCAL_TARGET_COUNTRY:
        return list(MONITORED_COUNTRY_CODES)

    if requested_country_code not in MONITORED_COUNTRY_CODES:
        raise ValueError(
            "PIPELINE_MODE=live supports only the canonical monitored-country set: "
            f"{', '.join(MONITORED_COUNTRY_CODES)}"
        )

    return list(MONITORED_COUNTRY_CODES)


def _get_failure_indicator_codes(fetch_failures: list[WorldBankFetchError]) -> list[str]:
    """Return the configured indicator codes that failed during live fetch.

    Args:
        fetch_failures: Live fetch failures gathered during the fetch stage.

    Returns:
        Sorted unique indicator codes with live fetch failures.
    """
    return sorted(
        {
            failure.indicator_code
            for failure in fetch_failures
            if failure.indicator_code in INDICATORS
        }
    )


def _get_failure_country_codes(fetch_failures: list[WorldBankFetchError]) -> list[str]:
    """Return the affected country codes gathered during live fetch.

    Args:
        fetch_failures: Live fetch failures gathered during the fetch stage.

    Returns:
        Unique ISO country codes in failure order.
    """
    country_codes: list[str] = []
    for failure in fetch_failures:
        for country_code in failure.country_codes:
            normalized_country_code = country_code.upper()
            if normalized_country_code and normalized_country_code not in country_codes:
                country_codes.append(normalized_country_code)
    return country_codes


def _get_country_codes_from_records(records: list[dict[str, Any]]) -> list[str]:
    """Return unique country codes present in normalized pipeline records.

    Args:
        records: Normalized data points or LLM contexts.

    Returns:
        Unique ISO country codes in record order.
    """
    country_codes: list[str] = []
    for record in records:
        normalized_country_code = str(record.get("country_code", "")).upper()
        if normalized_country_code and normalized_country_code not in country_codes:
            country_codes.append(normalized_country_code)
    return country_codes


def _build_live_failure_message(
    run_id: str,
    country_codes: list[str],
    fetch_failures: list[WorldBankFetchError],
) -> str | None:
    """Summarize live fetch failures for terminal status reporting.

    Args:
        run_id: Pipeline run identifier.
        country_codes: ISO 3166-1 alpha-2 country codes requested for the run.
        fetch_failures: Live fetch failures gathered during the fetch stage.

    Returns:
        Human-readable incomplete-coverage summary, or None when there were no failures.
    """
    indicator_codes = _get_failure_indicator_codes(fetch_failures)
    if not indicator_codes:
        return None

    failure_messages = "; ".join(str(failure) for failure in fetch_failures)
    return (
        f"run_id={run_id} live fetch preserved partial output for {_build_country_scope_label(country_codes)} "
        f"but ended with incomplete coverage for indicators {', '.join(indicator_codes)}: "
        f"{failure_messages}"
    )


def _build_country_scope_label(country_codes: list[str]) -> str:
    """Build a readable label for one pipeline country scope.

    Args:
        country_codes: ISO 3166-1 alpha-2 country codes in scope.

    Returns:
        Human-readable scope label.
    """
    if len(country_codes) == 1:
        return country_codes[0]
    return f"monitored set ({', '.join(country_codes)})"


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
