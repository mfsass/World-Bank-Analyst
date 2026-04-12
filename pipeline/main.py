"""Pipeline entry point.

Orchestrates the current bounded slice: fetch → analyse → two-step AI →
repository-backed storage. Local mode keeps deterministic development AI while
live mode uses the provider-backed client.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.ai_client import (  # noqa: E402
    STEP1_NAME,
    STEP1_PROMPT_VERSION,
    STEP2_NAME,
    STEP2_PROMPT_VERSION,
    STEP3_NAME,
    STEP3_PROMPT_VERSION,
    build_input_fingerprint,
    create_client,
)
from pipeline.analyser import compute_changes, prepare_llm_context  # noqa: E402
from pipeline.dev_ai_adapter import create_development_client  # noqa: E402
from pipeline.fetcher import INDICATORS, WorldBankFetchError, fetch_live_data  # noqa: E402
from pipeline.local_data import LOCAL_TARGET_COUNTRY, load_local_data_points  # noqa: E402
from pipeline.storage import RawArchiveStore, get_raw_archive_store, store_slice  # noqa: E402
from shared.country_catalog import MONITORED_COUNTRY_CODES  # noqa: E402
from shared.repository import (  # noqa: E402
    InsightsRepository,
    build_pipeline_steps,
    get_repository,
    is_reusable_ai_record,
)

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


class PipelineStatusTracker:
    """Own durable pipeline status transitions for one run."""

    def __init__(self, repository: InsightsRepository, run_id: str) -> None:
        """Initialise the tracker for one claimed or standalone run."""
        self._repository = repository
        self._run_id = run_id
        self._step_started_at: dict[str, float] = {}

    def ensure_running(self, *, already_claimed: bool) -> None:
        """Ensure the current run has a persisted running status record."""
        if already_claimed:
            current_status = self._repository.get_pipeline_status_record()
            if (
                current_status.get("run_id") == self._run_id
                and current_status.get("status") == "running"
            ):
                return

        self._repository.upsert_pipeline_status(
            {
                "status": "running",
                "run_id": self._run_id,
                "started_at": _utc_now(),
                "steps": build_pipeline_steps(),
            }
        )

    def update_step_status(self, step_name: str, step_status: str) -> None:
        """Update one pipeline step inside the durable status payload."""
        status = self._repository.get_pipeline_status_record()
        for step in status.get("steps", []):
            if step.get("name") != step_name:
                continue
            step["status"] = step_status
            if step_status == "running":
                step["started_at"] = _utc_now()
                self._step_started_at[step_name] = perf_counter()
                step.pop("duration_ms", None)
                step.pop("completed_at", None)
            elif (
                step_status in {"complete", "failed"}
                and step_name in self._step_started_at
            ):
                step["duration_ms"] = int(
                    (perf_counter() - self._step_started_at.pop(step_name)) * 1000
                )
                step["completed_at"] = _utc_now()
            break
        self._repository.upsert_pipeline_status(status)

    def mark_complete(self) -> None:
        """Mark the current run complete and clear stale failure detail."""
        status = self._repository.get_pipeline_status_record()
        status["status"] = "complete"
        status["completed_at"] = _utc_now()
        status.pop("error", None)
        status.pop("failure_summary", None)
        self._repository.upsert_pipeline_status(status)

    def mark_failed(
        self,
        *,
        message: str,
        step_name: str | None,
        country_codes: list[str] | None = None,
        indicator_codes: list[str] | None = None,
    ) -> None:
        """Mark the current run failed with step-aware failure detail."""
        status = self._repository.get_pipeline_status_record()
        self._mark_failed_step(status, step_name)
        status["status"] = "failed"
        status["completed_at"] = _utc_now()
        status["error"] = message
        status["failure_summary"] = {
            "run_id": self._run_id,
            "step": step_name,
            "message": message,
        }
        if country_codes:
            status["failure_summary"]["country_codes"] = country_codes
        if indicator_codes:
            status["failure_summary"]["indicator_codes"] = indicator_codes
        self._repository.upsert_pipeline_status(status)

    def mark_preflight_failure(self, *, step_name: str, message: str) -> None:
        """Persist a failed status when execution cannot start cleanly."""
        timestamp = _utc_now()
        steps = build_pipeline_steps()
        for step in steps:
            if step["name"] == step_name:
                step["status"] = "failed"
                break

        self._repository.upsert_pipeline_status(
            {
                "status": "failed",
                "run_id": self._run_id,
                "started_at": timestamp,
                "completed_at": timestamp,
                "steps": steps,
                "error": message,
                "failure_summary": {
                    "run_id": self._run_id,
                    "step": step_name,
                    "message": message,
                },
            }
        )

    def find_running_step_name(self) -> str | None:
        """Return the step currently marked running, when one exists."""
        status = self._repository.get_pipeline_status_record()
        for step in status.get("steps", []):
            if step.get("status") == "running":
                return step.get("name")
        return None

    def _mark_failed_step(
        self,
        status: dict[str, Any],
        fallback_step_name: str | None,
    ) -> None:
        """Mark the relevant step failed while preserving existing timing data."""
        running_step_marked = False
        for step in status.get("steps", []):
            if step.get("status") != "running":
                continue
            self._apply_failed_step_state(step)
            running_step_marked = True

        if running_step_marked or fallback_step_name is None:
            return

        for step in status.get("steps", []):
            if step.get("name") != fallback_step_name:
                continue
            self._apply_failed_step_state(step)
            break

    def _apply_failed_step_state(self, step: dict[str, Any]) -> None:
        """Apply the failed terminal state to one pipeline step."""
        step_name = step.get("name")
        step["status"] = "failed"
        if step_name in self._step_started_at:
            step["duration_ms"] = int(
                (perf_counter() - self._step_started_at.pop(step_name)) * 1000
            )
        if not step.get("completed_at"):
            step["completed_at"] = _utc_now()


def run_managed_pipeline(
    country_code: str = LOCAL_TARGET_COUNTRY,
    repository: InsightsRepository | None = None,
    run_id: str | None = None,
    raw_archive_store: RawArchiveStore | None = None,
    status_already_claimed: bool = False,
) -> dict[str, Any]:
    """Execute the pipeline while keeping durable status transitions in sync.

    Args:
        country_code: Requested country scope for the pipeline entry point.
        repository: Optional repository override.
        run_id: Optional pre-claimed run identifier.
        raw_archive_store: Optional raw archive store override.
        status_already_claimed: True when another process already persisted the
            running status record for this run.

    Returns:
        Pipeline execution summary dict.
    """
    repo = repository or get_repository()
    configured_country_code = (
        os.environ.get("WORLD_ANALYST_PIPELINE_COUNTRY_CODE", "").strip().upper()
    )
    requested_country_code = configured_country_code or country_code.upper()
    current_run_id = (
        run_id or os.environ.get("WORLD_ANALYST_PIPELINE_RUN_ID") or str(uuid4())
    )
    tracker = PipelineStatusTracker(repository=repo, run_id=current_run_id)
    tracker.ensure_running(already_claimed=status_already_claimed)

    resolved_raw_archive_store = raw_archive_store
    if resolved_raw_archive_store is None:
        try:
            resolved_raw_archive_store = get_raw_archive_store()
        except Exception as exc:
            tracker.mark_preflight_failure(step_name="store", message=str(exc))
            raise

    try:
        summary = run_pipeline(
            country_code=requested_country_code,
            repository=repo,
            step_callback=tracker.update_step_status,
            run_id=current_run_id,
            raw_archive_store=resolved_raw_archive_store,
        )
    except PipelineExecutionError as exc:
        tracker.mark_failed(
            message=str(exc),
            step_name=exc.step_name,
            country_codes=exc.country_codes,
            indicator_codes=exc.indicator_codes,
        )
        raise
    except Exception as exc:
        tracker.mark_failed(
            message=str(exc),
            step_name=tracker.find_running_step_name(),
        )
        raise

    tracker.mark_complete()
    return summary


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
            message=failure_message
            or (
                f"run_id={current_run_id} mode={runtime_mode} returned no usable data "
                f"for {_build_country_scope_label(target_country_codes)}"
            ),
            country_codes=_get_failure_country_codes(fetch_failures)
            or target_country_codes,
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
            country_codes=_get_country_codes_from_records(all_data_points)
            or target_country_codes,
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
    try:
        ai = _create_ai_client(runtime_mode)
        ai_provenance = _resolve_ai_provenance(ai)
    except Exception as exc:
        raise PipelineExecutionError(
            step_name="synthesise",
            message=str(exc),
            country_codes=target_country_codes,
            indicator_codes=list(INDICATORS),
        ) from exc
    ai_provider = (ai_provenance or {}).get("provider")
    ai_model = (ai_provenance or {}).get("model")
    if not ai_provider or not ai_model:
        raise PipelineExecutionError(
            step_name="synthesise",
            message="AI client provenance must include provider and model for reuse lineage.",
            country_codes=target_country_codes,
            indicator_codes=list(INDICATORS),
        )

    # Step 3a: Per-indicator analysis
    for ctx in llm_contexts:
        analysis = _reuse_indicator_analysis(
            repository=repo,
            context=ctx,
            provider=ai_provider,
            model=ai_model,
        )
        if analysis is None:
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
        if analysis.get("ai_provenance"):
            ctx["ai_provenance"] = analysis["ai_provenance"]

    # Step 3b: Macro synthesis per country
    country_groups: dict[str, list[dict]] = {}
    for ctx in llm_contexts:
        # Preserve the two-step contract: all indicator narratives must exist before country synthesis runs.
        country_groups.setdefault(ctx["country_code"], []).append(ctx)

    country_syntheses: dict[str, dict] = {}
    for country_code, indicators in country_groups.items():
        synthesis = _reuse_country_synthesis(
            repository=repo,
            indicators=indicators,
            provider=ai_provider,
            model=ai_model,
        )
        if synthesis is None:
            try:
                synthesis = ai.synthesise_country(indicators)
            except Exception as exc:
                raise PipelineExecutionError(
                    step_name="synthesise",
                    message=str(exc),
                    country_codes=[country_code],
                    indicator_codes=[
                        indicator["indicator_code"] for indicator in indicators
                    ],
                ) from exc
        country_syntheses[country_code] = synthesis
        _log_event(
            logging.INFO,
            "pipeline_country_synthesis_complete",
            run_id=current_run_id,
            country_code=country_code,
            risk_flags=len(synthesis.get("risk_flags", [])),
        )

    overview_input = _build_global_overview_inputs(
        country_syntheses=country_syntheses,
        llm_contexts=llm_contexts,
        repository=repo,
    )
    global_overview = _reuse_global_overview_synthesis(
        repository=repo,
        country_briefings=overview_input,
        provider=ai_provider,
        model=ai_model,
    )
    if global_overview is None:
        try:
            global_overview = ai.synthesise_global_overview(overview_input)
        except Exception as exc:
            raise PipelineExecutionError(
                step_name="synthesise",
                message=str(exc),
                country_codes=sorted(country_syntheses.keys()),
            ) from exc
    _log_event(
        logging.INFO,
        "pipeline_global_overview_complete",
        run_id=current_run_id,
        country_count=len(overview_input),
        risk_flags=len(global_overview.get("risk_flags", [])),
    )
    _notify_step(step_callback, "synthesise", "complete")

    # Step 4: STORE
    _notify_step(step_callback, "store", "running")
    try:
        storage_summary = store_slice(
            insights=llm_contexts,
            country_syntheses=country_syntheses,
            global_overview=global_overview,
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
            country_codes=_get_country_codes_from_records(llm_contexts)
            or target_country_codes,
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
    ai_degradation = _summarize_ai_degradation(
        llm_contexts,
        country_syntheses,
        global_overview,
    )
    if runtime_mode == "live" and fetch_failures:
        incomplete_coverage_message = _build_live_failure_message(
            run_id=current_run_id,
            country_codes=target_country_codes,
            fetch_failures=fetch_failures,
            ai_degradation=ai_degradation,
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
            country_codes=_get_failure_country_codes(fetch_failures)
            or target_country_codes,
            indicator_codes=_get_failure_indicator_codes(fetch_failures),
        )
    if (
        ai_degradation["indicator_count"]
        or ai_degradation["country_count"]
        or ai_degradation["overview_count"]
    ):
        degradation_message = _build_ai_degradation_message(
            run_id=current_run_id,
            ai_degradation=ai_degradation,
        )
        _log_event(
            logging.WARNING,
            "pipeline_ai_degraded",
            run_id=current_run_id,
            indicator_count=ai_degradation["indicator_count"],
            country_count=ai_degradation["country_count"],
            country_codes=ai_degradation["country_codes"],
            indicator_codes=ai_degradation["indicator_codes"],
        )
        raise PipelineExecutionError(
            step_name="synthesise",
            message=degradation_message,
            country_codes=ai_degradation["country_codes"],
            indicator_codes=ai_degradation["indicator_codes"],
        )
    _log_event(
        logging.INFO, "pipeline_run_complete", run_id=current_run_id, summary=summary
    )
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
    # Keep the repo default deterministic for local commands and tests. Cloud Run
    # must opt into the real World Bank fetch path with PIPELINE_MODE=live.
    requested_mode = os.environ.get("PIPELINE_MODE", "local").lower()
    if requested_mode in {"local", "live"}:
        return requested_mode

    _log_event(logging.WARNING, "pipeline_mode_fallback", requested_mode=requested_mode)
    return "local"


def _create_ai_client(runtime_mode: str) -> Any:
    """Return the deterministic or live AI client for the current pipeline mode."""

    if runtime_mode == "live":
        return create_client()
    return create_development_client()


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
        return (
            live_fetch.data_points,
            live_fetch.raw_payloads,
            list(live_fetch.failures),
        )

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


def _get_failure_indicator_codes(
    fetch_failures: list[WorldBankFetchError],
) -> list[str]:
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
    ai_degradation: dict[str, Any] | None = None,
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
    message = (
        f"run_id={run_id} live fetch preserved partial output for {_build_country_scope_label(country_codes)} "
        f"but ended with incomplete coverage for indicators {', '.join(indicator_codes)}: "
        f"{failure_messages}"
    )
    if ai_degradation and (
        ai_degradation.get("indicator_count") or ai_degradation.get("country_count")
    ):
        message = f"{message}. {_build_ai_degradation_clause(ai_degradation)}"
    return message


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


def _reuse_indicator_analysis(
    *,
    repository: InsightsRepository,
    context: dict[str, Any],
    provider: str,
    model: str,
) -> dict[str, Any] | None:
    """Reuse an exact-match Step 1 result from persisted records when available."""
    input_fingerprint = build_input_fingerprint(
        step_name=STEP1_NAME,
        prompt_version=STEP1_PROMPT_VERSION,
        prompt_input=_strip_reuse_private_fields(context),
        provider=provider,
        model=model,
    )
    reusable_record = repository.get_stored_record(
        entity_type="indicator",
        key=f"{str(context['country_code']).upper()}:{context['indicator_code']}",
    )
    if not reusable_record or not is_reusable_ai_record(
        record=reusable_record,
        step_name=STEP1_NAME,
        input_fingerprint=input_fingerprint,
    ):
        return None
    return _build_reused_ai_result(reusable_record)


def _reuse_country_synthesis(
    *,
    repository: InsightsRepository,
    indicators: list[dict[str, Any]],
    provider: str,
    model: str,
) -> dict[str, Any] | None:
    """Reuse an exact-match Step 2 result from persisted records when available."""
    country_code = str(indicators[0]["country_code"]).upper() if indicators else ""
    input_fingerprint = build_input_fingerprint(
        step_name=STEP2_NAME,
        prompt_version=STEP2_PROMPT_VERSION,
        prompt_input=_ordered_reuse_indicator_inputs(indicators),
        provider=provider,
        model=model,
    )
    reusable_record = repository.get_stored_record(
        entity_type="country",
        key=country_code,
    )
    if not reusable_record or not is_reusable_ai_record(
        record=reusable_record,
        step_name=STEP2_NAME,
        input_fingerprint=input_fingerprint,
    ):
        return None
    return _build_reused_ai_result(reusable_record)


def _reuse_global_overview_synthesis(
    *,
    repository: InsightsRepository,
    country_briefings: list[dict[str, Any]],
    provider: str,
    model: str,
) -> dict[str, Any] | None:
    """Reuse an exact-match Step 3 result from persisted records when available."""

    input_fingerprint = build_input_fingerprint(
        step_name=STEP3_NAME,
        prompt_version=STEP3_PROMPT_VERSION,
        prompt_input=_ordered_reuse_country_briefings(country_briefings),
        provider=provider,
        model=model,
    )
    reusable_record = repository.get_stored_record(
        entity_type="global_overview",
        key="current",
    )
    if not reusable_record or not is_reusable_ai_record(
        record=reusable_record,
        step_name=STEP3_NAME,
        input_fingerprint=input_fingerprint,
    ):
        return None
    return _build_reused_ai_result(reusable_record)


def _ordered_reuse_indicator_inputs(
    indicators: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return deterministic Step 2 inputs for exact-match reuse lookups."""
    return [
        _strip_reuse_private_fields(indicator)
        for indicator in sorted(
            indicators,
            key=lambda item: (
                str(item.get("country_code", "")),
                str(item.get("indicator_code", "")),
                int(item.get("data_year", 0) or 0),
            ),
        )
    ]


def _ordered_reuse_country_briefings(
    country_briefings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return deterministic Step 3 inputs for exact-match reuse lookups."""

    return [
        _strip_reuse_private_fields(briefing)
        for briefing in sorted(
            country_briefings,
            key=lambda item: (
                str(item.get("code", "")),
                str(item.get("name", "")),
            ),
        )
    ]


def _strip_reuse_private_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove private storage fields from the exact-match reuse input."""
    return {
        key: value
        for key, value in payload.items()
        if key
        not in {"ai_provenance", "source_provenance", "raw_backup_reference", "run_id"}
    }


def _build_reused_ai_result(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Project one stored record back into the live AI client result shape."""
    if not record:
        return None

    structured_output = record.get("ai_structured_output")
    if not isinstance(structured_output, dict) or not structured_output:
        return None

    ai_provenance = record.get("ai_provenance")
    if not isinstance(ai_provenance, dict):
        return None

    reused_provenance = json.loads(json.dumps(ai_provenance, default=str))
    lineage = reused_provenance.setdefault("lineage", {})
    lineage["reused_from"] = {
        "document_id": record.get("document_id"),
        "run_id": record.get("run_id"),
    }
    # Cost and latency for the current run should stay honest: reuse means no new provider bill.
    reused_provenance.pop("usage", None)

    reused_result = json.loads(json.dumps(structured_output, default=str))
    reused_result["ai_provenance"] = reused_provenance
    return reused_result


def _summarize_ai_degradation(
    llm_contexts: list[dict[str, Any]],
    country_syntheses: dict[str, dict[str, Any]],
    global_overview: dict[str, Any] | None,
) -> dict[str, Any]:
    """Summarize degraded AI outputs so terminal run status can stay honest."""
    degraded_indicator_records = [
        context
        for context in llm_contexts
        if bool(context.get("ai_provenance", {}).get("degraded"))
    ]
    degraded_country_records = [
        {"country_code": country_code, **synthesis}
        for country_code, synthesis in country_syntheses.items()
        if bool(synthesis.get("ai_provenance", {}).get("degraded"))
    ]
    overview_degraded = bool(
        global_overview and global_overview.get("ai_provenance", {}).get("degraded")
    )

    country_codes: list[str] = []
    indicator_codes: list[str] = []
    for record in degraded_indicator_records:
        _append_unique(country_codes, str(record.get("country_code", "")).upper())
        _append_unique(indicator_codes, str(record.get("indicator_code", "")))
    for record in degraded_country_records:
        _append_unique(country_codes, str(record.get("country_code", "")).upper())

    return {
        "indicator_count": len(degraded_indicator_records),
        "country_count": len(degraded_country_records),
        "overview_count": 1 if overview_degraded else 0,
        "country_codes": country_codes,
        "indicator_codes": indicator_codes,
    }


def _append_unique(values: list[str], candidate: str) -> None:
    """Append one non-empty value only when it is not already present."""
    if candidate and candidate not in values:
        values.append(candidate)


def _build_ai_degradation_message(
    run_id: str,
    ai_degradation: dict[str, Any],
) -> str:
    """Build the terminal status message for degraded live AI outputs."""
    return (
        f"run_id={run_id} live AI preserved stored output but ended with degraded coverage. "
        f"{_build_ai_degradation_clause(ai_degradation)}"
    )


def _build_ai_degradation_clause(ai_degradation: dict[str, Any]) -> str:
    """Build the human-readable degraded AI summary fragment."""
    fragments: list[str] = []
    if ai_degradation["indicator_count"]:
        fragments.append(
            f"Indicator analyses degraded: {ai_degradation['indicator_count']} "
            f"for {', '.join(ai_degradation['indicator_codes'])}"
        )
    if ai_degradation["country_count"]:
        fragments.append(
            f"Country syntheses degraded: {ai_degradation['country_count']} "
            f"for {', '.join(ai_degradation['country_codes'])}"
        )
    if ai_degradation["overview_count"]:
        fragments.append("Global overview synthesis degraded for the monitored panel")
    return "; ".join(fragments)


def _build_global_overview_inputs(
    *,
    country_syntheses: dict[str, dict[str, Any]],
    llm_contexts: list[dict[str, Any]],
    repository: InsightsRepository,
) -> list[dict[str, Any]]:
    """Build the Step 3 input from materialised country syntheses and metrics."""

    llm_contexts_by_country: dict[str, list[dict[str, Any]]] = {}
    for context in llm_contexts:
        llm_contexts_by_country.setdefault(
            str(context["country_code"]).upper(), []
        ).append(context)

    overview_inputs: list[dict[str, Any]] = []
    for country_code, synthesis in sorted(country_syntheses.items()):
        contexts = llm_contexts_by_country.get(country_code, [])
        metadata = repository.get_country_metadata(country_code) or {
            "code": country_code,
            "name": contexts[0].get("country_name", country_code)
            if contexts
            else country_code,
            "region": None,
            "income_level": None,
        }
        overview_inputs.append(
            {
                "code": metadata.get("code", country_code),
                "name": metadata.get("name", country_code),
                "region": metadata.get("region"),
                "income_level": metadata.get("income_level"),
                "summary": synthesis.get("summary", ""),
                "risk_flags": synthesis.get("risk_flags", []),
                "outlook": synthesis.get("outlook", "cautious"),
                "anomaly_count": sum(
                    1 for context in contexts if context.get("is_anomaly")
                ),
                "data_year": max(
                    (int(ctx.get("data_year", 0) or 0) for ctx in contexts),
                    default=0,
                ) or None,
            }
        )
    return overview_inputs


def _log_event(level: int, event: str, **fields: Any) -> None:
    """Emit a structured JSON log line.

    Args:
        level: Logging level constant.
        event: Event name.
        **fields: Structured event fields.
    """
    logger.log(
        level, json.dumps({"event": event, **fields}, default=str, sort_keys=True)
    )


def _utc_now() -> str:
    """Return the current UTC timestamp as an ISO string."""
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    run_managed_pipeline(
        status_already_claimed=bool(os.environ.get("WORLD_ANALYST_PIPELINE_RUN_ID"))
    )
