"""Pipeline entry point.

Orchestrates the current bounded slice: fixture load → analyse → deterministic
AI → repository-backed storage.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.analyser import compute_changes, prepare_llm_context
from pipeline.dev_ai_adapter import create_development_client
from pipeline.local_data import LOCAL_TARGET_COUNTRY, load_local_data_points
from pipeline.storage import store_slice
from shared.repository import InsightsRepository, get_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

StepCallback = Callable[[str, str], None]


def run_pipeline(
    country_code: str = LOCAL_TARGET_COUNTRY,
    repository: InsightsRepository | None = None,
    step_callback: StepCallback | None = None,
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

    if runtime_mode != "local":
        logger.warning(
            "PIPELINE_MODE=%s is not wired for the first slice; falling back to local mode",
            runtime_mode,
        )

    logger.info("=== Pipeline started ===")
    logger.info("Mode: local | Country: %s", normalized_country_code)

    # Step 1: FETCH
    logger.info("--- Step 1: FETCH ---")
    _notify_step(step_callback, "fetch", "running")
    all_data_points = load_local_data_points(normalized_country_code)
    logger.info("Fetched %d total data points", len(all_data_points))
    _notify_step(step_callback, "fetch", "complete")

    # Step 2: ANALYSE
    logger.info("--- Step 2: ANALYSE ---")
    _notify_step(step_callback, "analyse", "running")
    df = compute_changes(all_data_points)
    llm_contexts = prepare_llm_context(df)
    logger.info("Prepared %d contexts for AI analysis", len(llm_contexts))
    _notify_step(step_callback, "analyse", "complete")

    # Step 3: AI (Two-step chain)
    logger.info("--- Step 3: AI ANALYSIS ---")
    _notify_step(step_callback, "synthesise", "running")
    ai = create_development_client()

    # Step 3a: Per-indicator analysis
    for ctx in llm_contexts:
        analysis = ai.analyse_indicator(ctx)
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
        synthesis = ai.synthesise_country(indicators)
        country_syntheses[country_code] = synthesis
        logger.info("Synthesised %s: %d risk flags", country_code, len(synthesis.get("risk_flags", [])))
    _notify_step(step_callback, "synthesise", "complete")

    # Step 4: STORE
    logger.info("--- Step 4: STORE ---")
    _notify_step(step_callback, "store", "running")
    storage_summary = store_slice(llm_contexts, country_syntheses, repo)
    _notify_step(step_callback, "store", "complete")

    summary = {
        "data_points_fetched": len(all_data_points),
        "indicators_analysed": len(llm_contexts),
        "countries_synthesised": len(country_syntheses),
        "anomalies_detected": sum(1 for c in llm_contexts if c.get("is_anomaly")),
        **storage_summary,
    }
    logger.info("=== Pipeline complete: %s ===", summary)
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


if __name__ == "__main__":
    run_pipeline()
