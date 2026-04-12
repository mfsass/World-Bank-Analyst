"""Live AI evaluation harness for the approved monitored-country scope.

The harness intentionally reports to stdout or return values only. It does not
create a new cache tier, mutate stored records, or write evaluation artifacts to
disk. That keeps the evidence path inspectable in review and compatible with the
repo's no-output-files automation constraint.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from statistics import median
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from pipeline.ai_client import IndicatorInsight, MacroSynthesis, create_client
from pipeline.analyser import compute_changes, prepare_llm_context
from pipeline.fetcher import INDICATORS, LiveFetchResult, fetch_live_data
from shared.country_catalog import MONITORED_COUNTRY_CODES

StepEvaluator = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
EVALUATION_GATE_THRESHOLDS = {
    "required_country_count": len(MONITORED_COUNTRY_CODES),
    "required_indicator_count": len(INDICATORS),
    "max_fetch_failures": 0,
    "min_indicator_schema_valid_rate": 1.0,
    "min_synthesis_schema_valid_rate": 1.0,
    "max_indicator_degraded_rate": 0.0,
    "max_synthesis_degraded_rate": 0.0,
    "max_indicator_refusal_rate": 0.0,
    "max_synthesis_refusal_rate": 0.0,
    "min_indicator_groundedness": 0.8,
    "min_synthesis_coherence": 0.8,
    "max_indicator_p95_latency_ms": 8000,
    "max_synthesis_p95_latency_ms": 15000,
    "max_full_run_cost_usd": 5.0,
    "min_overview_groundedness": 0.7,
    "min_overview_cross_regional_coverage": 0.9,
    "min_overview_no_single_country_anchoring": 1.0,
    "min_overview_data_year_citation": 1.0,
    "max_overview_degraded_rate": 0.0,
    "max_overview_p95_latency_ms": 30000,
}
DEFAULT_PRICING_BY_MODEL = {
    "google-genai:gemma-4-31b-it": {
        "prompt_token_count": 0.14,
        "candidates_token_count": 0.40,
        # Gemma 4 currently reports thought tokens through the same usage envelope.
        # Treat them as output-equivalent for a bounded sign-off estimate.
        "thoughts_token_count": 0.40,
    }
}


class EvaluationGateFailure(RuntimeError):
    """Raised when the documented live-AI gate does not pass."""


class IndicatorJudgeResult(BaseModel):
    """Judge output for Step 1 groundedness scoring."""

    groundedness: float = Field(
        ge=0.0,
        le=1.0,
        description="How well the indicator narrative stays grounded in the supplied numeric input.",
    )
    reasoning: str = Field(
        description="Short explanation of the groundedness score."
    )


class SynthesisJudgeResult(BaseModel):
    """Judge output for Step 2 groundedness and coherence scoring."""

    groundedness: float = Field(
        ge=0.0,
        le=1.0,
        description="How well the synthesis stays grounded in the supplied indicator inputs.",
    )
    coherence: float = Field(
        ge=0.0,
        le=1.0,
        description="How coherent and internally consistent the synthesis is across indicators.",
    )
    reasoning: str = Field(
        description="Short explanation of the groundedness and coherence scores."
    )


class GlobalOverviewJudgeResult(BaseModel):
    """Judge output for Step 3 global overview scoring."""

    groundedness: float = Field(
        ge=0.0,
        le=1.0,
        description="Claims in the summary trace to the supplied country briefings.",
    )
    cross_regional_coverage: float = Field(
        ge=0.0,
        le=1.0,
        description="Summary references at least three distinct geographic regions.",
    )
    no_single_country_anchoring: float = Field(
        ge=0.0,
        le=1.0,
        description="Summary does not open with or anchor to a single country.",
    )
    data_year_citation: float = Field(
        ge=0.0,
        le=1.0,
        description="Summary references the data year when citing trends.",
    )
    reasoning: str = Field(
        description="Short explanation of scores."
    )


def create_builtin_evaluation_judge() -> StepEvaluator:
    """Return the deterministic rubric used when no live judge model is configured."""

    def judge(judge_input: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        if "country_briefings" in judge_input:
            return _score_builtin_global_overview(judge_input, result)
        if "summary" in result:
            return _score_builtin_synthesis(judge_input, result)
        return _score_builtin_indicator(judge_input, result)

    setattr(judge, "judge_provider", "builtin-rubric")
    setattr(judge, "judge_model", "v1")
    return judge


def create_google_evaluation_judge(model_name: str) -> StepEvaluator:
    """Return a Google-backed judge for groundedness and coherence scoring.

    Args:
        model_name: Google model identifier used for the evaluation judge.

    Returns:
        Callable judge compatible with `evaluate_live_baseline`.
    """
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def judge(judge_input: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        if "country_briefings" in judge_input:
            response_model: type[BaseModel] = GlobalOverviewJudgeResult
            system_instruction = (
                "You are a strict evaluator for a global economic intelligence summary. "
                "Score on four dimensions, each normalized 0.0 to 1.0. "
                "Groundedness: do the summary and risk flags trace back to the supplied country briefings? "
                "Cross-regional coverage: does the summary reference at least three distinct geographic regions by name? "
                "No single-country anchoring: does the summary avoid opening with or centering on one country's story? "
                "Data year citation: does the summary cite the data year when discussing trends? "
                "Return JSON only."
            )
            contents = _build_global_overview_judge_prompt(judge_input, result)
        elif "summary" in result:
            response_model = SynthesisJudgeResult
            system_instruction = (
                "You are a strict evaluator for World Analyst country syntheses. "
                "Score groundedness and coherence on a normalized 0.0 to 1.0 scale. "
                "Groundedness measures whether claims and risk flags trace back to the supplied indicators. "
                "Coherence measures whether the narrative forms a consistent macro story without contradictions "
                "and acknowledges tensions when the indicator set pulls in different directions. "
                "Return JSON only."
            )
            contents = _build_synthesis_judge_prompt(judge_input, result)
        else:
            response_model = IndicatorJudgeResult
            system_instruction = (
                "You are a strict evaluator for World Analyst indicator narratives. "
                "Score groundedness on a normalized 0.0 to 1.0 scale. "
                "A score of 1.0 means the narrative stays fully anchored to the supplied numeric input and does not "
                "invent drivers or magnitudes. A score near 0.0 means the narrative is materially unsupported or "
                "contradicted by the input. Return JSON only."
            )
            contents = _build_indicator_judge_prompt(judge_input, result)

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "response_json_schema": response_model.model_json_schema(),
                "temperature": 0,
            },
        )
        return response_model.model_validate_json(response.text).model_dump()

    setattr(judge, "judge_provider", "google-genai")
    setattr(judge, "judge_model", model_name)
    return judge


def evaluate_live_baseline(
    *,
    provider: str | None = None,
    country_codes: list[str] | None = None,
    ai_client: Any | None = None,
    live_fetcher: Callable[..., LiveFetchResult] = fetch_live_data,
    judge: StepEvaluator | None = None,
    pricing_by_model: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Run the live AI evaluation harness and return a structured summary.

    Args:
        provider: Optional provider override for `create_client`.
        country_codes: Optional monitored-country subset for controlled evaluations.
        ai_client: Optional injected AI client for tests.
        live_fetcher: Fetch seam used to build the evaluation corpus.
        judge: Optional evaluator for groundedness and coherence scoring. The
            evaluator should return normalized numeric scores in the 0.0-1.0 range.
        pricing_by_model: Optional pricing config keyed by `provider:model`.

    Returns:
        Structured evaluation report suitable for PRD closeout discussion.
    """
    requested_country_codes = [
        country_code.upper()
        for country_code in (country_codes or list(MONITORED_COUNTRY_CODES))
    ]
    approved_scope_complete = _is_full_approved_scope(requested_country_codes)
    current_run_id = str(uuid4())
    fetch_result = live_fetcher(country_codes=requested_country_codes, run_id=current_run_id)
    evaluation_client = ai_client or create_client(provider)

    df = compute_changes(fetch_result.data_points)
    llm_contexts = prepare_llm_context(df)
    indicator_case_results: list[dict[str, Any]] = []
    for context in llm_contexts:
        started_at = perf_counter()
        result = evaluation_client.analyse_indicator(context)
        latency_ms = int((perf_counter() - started_at) * 1000)
        indicator_case_results.append(
            _build_case_result(
                step_name="indicator_analysis",
                scope={
                    "country_code": context["country_code"],
                    "indicator_code": context["indicator_code"],
                },
                result=result,
                response_model=IndicatorInsight,
                latency_ms=latency_ms,
                judge=judge,
                judge_input=context,
            )
        )
        context["ai_analysis"] = result["narrative"]
        context["trend"] = result["trend"]
        context["risk_level"] = result["risk_level"]
        context["confidence"] = result["confidence"]
        if result.get("ai_provenance"):
            context["ai_provenance"] = result["ai_provenance"]

    country_groups: dict[str, list[dict[str, Any]]] = {}
    for context in llm_contexts:
        country_groups.setdefault(context["country_code"], []).append(context)

    global_overview_inputs: list[dict[str, Any]] = []
    synthesis_case_results: list[dict[str, Any]] = []
    for country_code, indicators in country_groups.items():
        started_at = perf_counter()
        result = evaluation_client.synthesise_country(indicators)
        latency_ms = int((perf_counter() - started_at) * 1000)
        synthesis_case_results.append(
            _build_case_result(
                step_name="macro_synthesis",
                scope={"country_code": country_code},
                result=result,
                response_model=MacroSynthesis,
                latency_ms=latency_ms,
                judge=judge,
                judge_input={"indicators": indicators},
            )
        )
        # Accumulate briefings for Step 3 evaluation
        global_overview_inputs.append({
            "code": country_code,
            "name": indicators[0].get("country_name", country_code) if indicators else country_code,
            "region": indicators[0].get("region") if indicators else None,
            "data_year": max((int(ctx.get("data_year", 0) or 0) for ctx in indicators), default=0) or None,
            "summary": result.get("summary"),
            "risk_flags": result.get("risk_flags", []),
            "outlook": result.get("outlook"),
        })

    # Step 3: Global overview evaluation — sleep to let the per-minute quota
    # window reset after the Step 1+2 burst (Gemma 4: 16,000 tokens/min).
    _STEP3_RATE_LIMIT_COOLDOWN_S = 65
    global_overview_case_results: list[dict[str, Any]] = []
    if global_overview_inputs:
        print(
            f"Waiting {_STEP3_RATE_LIMIT_COOLDOWN_S}s before Step 3 to clear rate-limit window…",
            file=sys.stderr,
        )
        time.sleep(_STEP3_RATE_LIMIT_COOLDOWN_S)
        started_at = perf_counter()
        overview_result = evaluation_client.synthesise_global_overview(global_overview_inputs)
        latency_ms = int((perf_counter() - started_at) * 1000)
        global_overview_case_results.append(
            _build_case_result(
                step_name="global_overview",
                scope={},
                result=overview_result,
                response_model=MacroSynthesis,
                latency_ms=latency_ms,
                judge=judge,
                judge_input={"country_briefings": global_overview_inputs},
            )
        )

    indicator_metrics = _aggregate_case_results(indicator_case_results, pricing_by_model)
    synthesis_metrics = _aggregate_case_results(synthesis_case_results, pricing_by_model)
    global_overview_metrics = _aggregate_case_results(global_overview_case_results, pricing_by_model)
    gate = _build_gate_summary(
        fetch_result=fetch_result,
        indicator_metrics=indicator_metrics,
        synthesis_metrics=synthesis_metrics,
        global_overview_metrics=global_overview_metrics,
        judge_enabled=judge is not None,
        approved_scope_complete=approved_scope_complete,
    )

    return {
        "run_id": current_run_id,
        "scope": {
            "requested_country_codes": requested_country_codes,
            "requested_country_count": len(requested_country_codes),
            "indicator_count": len(INDICATORS),
            "approved_scope_complete": approved_scope_complete,
        },
        "fetch": {
            "data_points": len(fetch_result.data_points),
            "raw_payloads": len(fetch_result.raw_payloads),
            "failures": [str(failure) for failure in fetch_result.failures],
        },
        "steps": {
            "indicator_analysis": indicator_metrics,
            "macro_synthesis": synthesis_metrics,
            "global_overview": global_overview_metrics,
        },
        "judge": {
            "enabled": judge is not None,
            "status": "configured" if judge is not None else "not_run",
            "provider": getattr(judge, "judge_provider", None),
            "model": getattr(judge, "judge_model", None),
            "reason": None
            if judge is not None
            else "Groundedness and coherence scoring requires an explicit evaluator.",
        },
        "thresholds": dict(EVALUATION_GATE_THRESHOLDS),
        "gate": gate,
    }


def enforce_evaluation_gate(report: dict[str, Any]) -> None:
    """Raise when an evaluation report does not satisfy the documented gate.

    Args:
        report: Structured report returned by `evaluate_live_baseline`.

    Raises:
        EvaluationGateFailure: If the gate did not pass.
    """
    gate = report.get("gate", {})
    if gate.get("passes"):
        return

    failures = gate.get("failures", [])
    failure_summary = "; ".join(str(failure) for failure in failures) or "Unknown gate failure."
    raise EvaluationGateFailure(f"Live AI evaluation gate failed: {failure_summary}")


def _build_case_result(
    *,
    step_name: str,
    scope: dict[str, Any],
    result: dict[str, Any],
    response_model: type[Any],
    latency_ms: int,
    judge: StepEvaluator | None,
    judge_input: dict[str, Any],
) -> dict[str, Any]:
    """Build one step-level evaluation case result."""
    validation_payload = {
        key: value for key, value in result.items() if key != "ai_provenance"
    }
    response_model.model_validate(validation_payload)

    ai_provenance = result.get("ai_provenance", {})
    degraded_reason = str(ai_provenance.get("degraded_reason", ""))
    judge_result = judge(judge_input, validation_payload) if judge is not None else None
    return {
        "step_name": step_name,
        **scope,
        "latency_ms": latency_ms,
        "schema_valid": True,
        "degraded": bool(ai_provenance.get("degraded")),
        "refusal": "refusal" in degraded_reason.lower(),
        "reused": ai_provenance.get("lineage", {}).get("reused_from") is not None,
        "provider": ai_provenance.get("provider"),
        "model": ai_provenance.get("model"),
        "usage": ai_provenance.get("usage") or {},
        "judge": judge_result,
    }


def _aggregate_case_results(
    case_results: list[dict[str, Any]],
    pricing_by_model: dict[str, dict[str, float]] | None,
) -> dict[str, Any]:
    """Aggregate one step's evaluation cases into PRD-friendly metrics."""
    latencies = [case["latency_ms"] for case in case_results]
    degraded_cases = [case for case in case_results if case["degraded"]]
    refusal_cases = [case for case in case_results if case["refusal"]]
    usage_totals = _aggregate_usage(case_results)
    pricing_table = pricing_by_model or _load_pricing_table()
    return {
        "cases_total": len(case_results),
        "schema_valid_cases": sum(1 for case in case_results if case["schema_valid"]),
        "schema_valid_rate": _rate(
            sum(1 for case in case_results if case["schema_valid"]),
            len(case_results),
        ),
        "provider_success_cases": sum(1 for case in case_results if not case["degraded"]),
        "degraded_cases": len(degraded_cases),
        "degraded_rate": _rate(len(degraded_cases), len(case_results)),
        "refusal_cases": len(refusal_cases),
        "refusal_rate": _rate(len(refusal_cases), len(case_results)),
        "reused_cases": sum(1 for case in case_results if case["reused"]),
        "latency_ms": _summarize_latencies(latencies),
        "usage_totals": usage_totals,
        "estimated_cost_usd": _estimate_cost(case_results, usage_totals, pricing_table),
        "providers": sorted(
            {
                f"{case['provider']}:{case['model']}"
                for case in case_results
                if case.get("provider") and case.get("model")
            }
        ),
        "judge_scores": _aggregate_judge_scores(case_results),
    }


def _aggregate_usage(case_results: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate numeric usage metadata across evaluation cases."""
    totals: dict[str, int] = {}
    for case in case_results:
        for key, value in case.get("usage", {}).items():
            if isinstance(value, (int, float)):
                totals[key] = totals.get(key, 0) + int(value)
    return totals


def _estimate_cost(
    case_results: list[dict[str, Any]],
    usage_totals: dict[str, int],
    pricing_by_model: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Estimate cost when model pricing was configured for the harness run."""
    providers = {
        f"{case['provider']}:{case['model']}"
        for case in case_results
        if case.get("provider") and case.get("model")
    }
    if len(providers) != 1:
        return {"configured": False, "reason": "Mixed or missing provider/model usage."}

    provider_key = next(iter(providers), None)
    if provider_key not in pricing_by_model:
        return {"configured": False, "reason": f"No pricing configured for {provider_key}."}

    pricing = pricing_by_model[provider_key]
    total_cost = 0.0
    for usage_key, total_tokens in usage_totals.items():
        rate = pricing.get(usage_key)
        if rate is None:
            continue
        total_cost += (total_tokens / 1_000_000) * rate
    return {"configured": True, "provider_model": provider_key, "total_cost_usd": round(total_cost, 6)}


def _load_pricing_table() -> dict[str, dict[str, float]]:
    """Load optional pricing metadata from the environment."""
    pricing_table = {
        provider_model: dict(pricing)
        for provider_model, pricing in DEFAULT_PRICING_BY_MODEL.items()
    }
    pricing_json = os.environ.get("WORLD_ANALYST_EVAL_PRICING_JSON")
    if not pricing_json:
        return pricing_table
    loaded = json.loads(pricing_json)
    for provider_model, pricing in loaded.items():
        pricing_table[str(provider_model)] = {
            str(key): float(value) for key, value in pricing.items()
        }
    return pricing_table


def _aggregate_judge_scores(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate optional judge scores when a groundedness/coherence evaluator ran."""
    judge_results = [case["judge"] for case in case_results if isinstance(case.get("judge"), dict)]
    if not judge_results:
        return {"enabled": False}

    aggregated: dict[str, float] = {}
    for judge_result in judge_results:
        for key, value in judge_result.items():
            if isinstance(value, (int, float)):
                aggregated[key] = aggregated.get(key, 0.0) + float(value)
    return {
        "enabled": True,
        **{
            key: round(total / len(judge_results), 3)
            for key, total in aggregated.items()
        },
    }


def _rate(numerator: int, denominator: int) -> float:
    """Return a rounded rate while keeping empty denominators safe."""
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _summarize_latencies(latencies: list[int]) -> dict[str, int]:
    """Return basic latency distribution metrics for one evaluation step."""
    if not latencies:
        return {"min": 0, "p50": 0, "p95": 0, "max": 0}

    sorted_latencies = sorted(latencies)
    return {
        "min": sorted_latencies[0],
        "p50": int(median(sorted_latencies)),
        "p95": sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))],
        "max": sorted_latencies[-1],
    }


def _build_gate_summary(
    *,
    fetch_result: LiveFetchResult,
    approved_scope_complete: bool,
    indicator_metrics: dict[str, Any],
    synthesis_metrics: dict[str, Any],
    global_overview_metrics: dict[str, Any],
    judge_enabled: bool,
) -> dict[str, Any]:
    """Build an honest gate summary for PRD sign-off discussion."""
    failures: list[str] = []
    if not approved_scope_complete:
        failures.append(
            "Evaluation did not run the full approved 17-country scope."
        )
    if fetch_result.failures:
        failures.append("Live fetch had incomplete coverage, so the baseline evidence is partial.")
    if (
        indicator_metrics["schema_valid_rate"]
        < EVALUATION_GATE_THRESHOLDS["min_indicator_schema_valid_rate"]
    ):
        failures.append("Indicator structured-output validity missed the 100% threshold.")
    if (
        synthesis_metrics["schema_valid_rate"]
        < EVALUATION_GATE_THRESHOLDS["min_synthesis_schema_valid_rate"]
    ):
        failures.append("Synthesis structured-output validity missed the 100% threshold.")
    if (
        indicator_metrics["degraded_rate"]
        > EVALUATION_GATE_THRESHOLDS["max_indicator_degraded_rate"]
    ):
        failures.append("Indicator degraded-fallback rate exceeded 0%.")
    if (
        synthesis_metrics["degraded_rate"]
        > EVALUATION_GATE_THRESHOLDS["max_synthesis_degraded_rate"]
    ):
        failures.append("Synthesis degraded-fallback rate exceeded 0%.")
    if (
        indicator_metrics["refusal_rate"]
        > EVALUATION_GATE_THRESHOLDS["max_indicator_refusal_rate"]
    ):
        failures.append("Indicator refusal rate exceeded 0%.")
    if (
        synthesis_metrics["refusal_rate"]
        > EVALUATION_GATE_THRESHOLDS["max_synthesis_refusal_rate"]
    ):
        failures.append("Synthesis refusal rate exceeded 0%.")
    if (
        indicator_metrics["latency_ms"]["p95"]
        > EVALUATION_GATE_THRESHOLDS["max_indicator_p95_latency_ms"]
    ):
        failures.append("Indicator p95 latency exceeded the 8s threshold.")
    if (
        synthesis_metrics["latency_ms"]["p95"]
        > EVALUATION_GATE_THRESHOLDS["max_synthesis_p95_latency_ms"]
    ):
        failures.append("Synthesis p95 latency exceeded the 15s threshold.")
    # Step 3 global overview gate checks
    if (
        global_overview_metrics["degraded_rate"]
        > EVALUATION_GATE_THRESHOLDS["max_overview_degraded_rate"]
    ):
        failures.append("Global overview degraded-fallback rate exceeded 0%.")
    if (
        global_overview_metrics["latency_ms"]["p95"]
        > EVALUATION_GATE_THRESHOLDS["max_overview_p95_latency_ms"]
    ):
        failures.append("Global overview p95 latency exceeded the 30s threshold.")
    if not judge_enabled:
        failures.append("Groundedness and coherence scoring was not configured for this run.")
    else:
        if (
            indicator_metrics["judge_scores"].get("groundedness", 0.0)
            < EVALUATION_GATE_THRESHOLDS["min_indicator_groundedness"]
        ):
            failures.append("Indicator groundedness missed the 0.80 threshold.")
        if (
            synthesis_metrics["judge_scores"].get("coherence", 0.0)
            < EVALUATION_GATE_THRESHOLDS["min_synthesis_coherence"]
        ):
            failures.append("Synthesis coherence missed the 0.80 threshold.")
        # Step 3 judge score checks
        if (
            global_overview_metrics["judge_scores"].get("groundedness", 0.0)
            < EVALUATION_GATE_THRESHOLDS["min_overview_groundedness"]
        ):
            failures.append("Global overview groundedness missed the 0.70 threshold.")
        if (
            global_overview_metrics["judge_scores"].get("cross_regional_coverage", 0.0)
            < EVALUATION_GATE_THRESHOLDS["min_overview_cross_regional_coverage"]
        ):
            failures.append("Global overview cross-regional coverage missed the 0.90 threshold.")
        if (
            global_overview_metrics["judge_scores"].get("no_single_country_anchoring", 0.0)
            < EVALUATION_GATE_THRESHOLDS["min_overview_no_single_country_anchoring"]
        ):
            failures.append("Global overview anchored on a single country.")
        if (
            global_overview_metrics["judge_scores"].get("data_year_citation", 0.0)
            < EVALUATION_GATE_THRESHOLDS["min_overview_data_year_citation"]
        ):
            failures.append("Global overview did not cite the data year.")

    full_run_cost = _combine_estimated_costs(
        indicator_metrics["estimated_cost_usd"],
        synthesis_metrics["estimated_cost_usd"],
        global_overview_metrics["estimated_cost_usd"],
    )
    if not full_run_cost["configured"]:
        failures.append("Estimated full-run cost was not configured.")
    elif full_run_cost["total_cost_usd"] > EVALUATION_GATE_THRESHOLDS["max_full_run_cost_usd"]:
        failures.append("Estimated full-run cost exceeded the $5.00 threshold.")

    return {
        "passes": not failures,
        "failures": failures,
        "estimated_full_run_cost_usd": full_run_cost,
        "required_dimensions": {
            "structured_output_validity": not any(
                "structured-output validity" in failure for failure in failures
            ),
            "latency": not any("latency" in failure for failure in failures),
            "usage_and_cost_inputs": full_run_cost.get("configured", False),
            "groundedness_and_coherence": judge_enabled
            and not any(
                "groundedness" in failure or "coherence" in failure for failure in failures
            ),
        },
    }


def _combine_estimated_costs(
    indicator_cost: dict[str, Any],
    synthesis_cost: dict[str, Any],
    global_overview_cost: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine step-level estimated costs into one full-run estimate."""
    costs = [indicator_cost, synthesis_cost]
    if global_overview_cost is not None:
        costs.append(global_overview_cost)

    if not all(cost.get("configured") for cost in costs):
        return {"configured": False, "reason": "One or more step cost estimates were unavailable."}

    total_cost_usd = round(
        sum(float(cost["total_cost_usd"]) for cost in costs),
        6,
    )
    provider_models = [cost.get("provider_model") for cost in costs]
    return {
        "configured": True,
        "total_cost_usd": total_cost_usd,
        "provider_models": provider_models,
    }


def _score_builtin_indicator(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Score Step 1 groundedness with a deterministic rubric."""
    groundedness = 0.0
    reasoning: list[str] = []
    narrative = str(result.get("narrative", "")).lower()
    if _contains_numeric_reference(
        narrative,
        [
            judge_input.get("latest_value"),
            judge_input.get("previous_value"),
            judge_input.get("percent_change"),
            judge_input.get("z_score"),
        ],
    ):
        groundedness += 0.40
        reasoning.append("narrative referenced a numeric input value")
    if _direction_signal_matches(judge_input, result):
        groundedness += 0.25
        reasoning.append("direction of travel matched the supplied move")
    if str(judge_input.get("data_year", "")) in narrative:
        groundedness += 0.15
        reasoning.append("narrative referenced the data year")
    if any(keyword in narrative for keyword in _indicator_keywords(judge_input)):
        groundedness += 0.10
        reasoning.append("narrative stayed specific to the indicator theme")
    if _missing_data_language_is_honest(narrative, [judge_input]):
        groundedness += 0.10
        reasoning.append("missing-data language stayed aligned with the input")

    return {
        "groundedness": round(min(1.0, groundedness), 3),
        "reasoning": "; ".join(reasoning) or "rubric found no strong grounding signals",
    }


def _score_builtin_synthesis(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Score Step 2 groundedness and coherence with a deterministic rubric."""
    indicators = judge_input.get("indicators", [])
    combined_text = " ".join(
        [
            str(result.get("summary", "")),
            " ".join(str(flag) for flag in result.get("risk_flags", [])),
        ]
    ).lower()
    groundedness = 0.0
    coherence = 0.0
    reasoning: list[str] = []
    mentioned_indicator_count = _count_indicator_mentions(combined_text, indicators)

    if _contains_numeric_reference(
        combined_text,
        [
            indicator.get("latest_value")
            for indicator in indicators
        ]
        + [indicator.get("percent_change") for indicator in indicators],
    ):
        groundedness += 0.30
        reasoning.append("summary or flags referenced numeric indicator values")
    if mentioned_indicator_count >= 2:
        groundedness += 0.35
        coherence += 0.25
        reasoning.append("output referenced multiple indicator themes")
    if _missing_data_language_is_honest(combined_text, indicators):
        groundedness += 0.15
        reasoning.append("missing-data language stayed aligned with the indicator set")

    risk_flags = result.get("risk_flags", [])
    if 2 <= len(risk_flags) <= 3:
        coherence += 0.25
        reasoning.append("risk flag count stayed within the intended 2-3 range")
    summary_word_count = len(str(result.get("summary", "")).split())
    if 0 < summary_word_count <= 200:
        coherence += 0.20
        reasoning.append("summary stayed within the 200-word brief")

    high_risk_count = sum(
        1
        for indicator in indicators
        if indicator.get("risk_level") == "high" or indicator.get("is_anomaly")
    )
    if _outlook_is_plausible(result.get("outlook"), high_risk_count):
        groundedness += 0.20
        coherence += 0.30
        reasoning.append("outlook stayed plausible for the high-risk signal mix")

    return {
        "groundedness": round(min(1.0, groundedness), 3),
        "coherence": round(min(1.0, coherence), 3),
        "reasoning": "; ".join(reasoning) or "rubric found no strong synthesis signals",
    }


def _score_builtin_global_overview(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Score Step 3 global overview with a deterministic rubric."""
    briefings = judge_input.get("country_briefings", [])
    summary = str(result.get("summary", "")).lower()
    risk_flags_text = " ".join(str(f) for f in result.get("risk_flags", [])).lower()
    combined_text = f"{summary} {risk_flags_text}"
    reasoning: list[str] = []

    # Groundedness: risk flags cite country codes or country names from briefings
    country_codes = {str(b.get("code", "")).lower() for b in briefings}
    country_names = {str(b.get("name", "")).lower() for b in briefings}
    cited = sum(1 for code in country_codes if code and code in combined_text)
    cited += sum(1 for name in country_names if len(name) > 3 and name in combined_text)
    groundedness = min(1.0, cited / max(1, len(briefings)) * 3)  # normalised
    if cited >= 2:
        reasoning.append(f"output referenced {cited} country identifiers from the briefings")

    # Cross-regional coverage: at least 3 distinct region keywords
    region_keywords = [
        ("europe", "european"),
        ("asia", "pacific", "asian"),
        ("latin america", "south america", "caribbean"),
        ("africa", "african"),
        ("north america", "united states", "canada"),
        ("middle east", "mena"),
        ("south asia", "india", "pakistan"),
    ]
    regions_covered = sum(
        1 for keywords in region_keywords
        if any(kw in combined_text for kw in keywords)
    )
    cross_regional = min(1.0, regions_covered / 3)
    if regions_covered >= 3:
        reasoning.append(f"summary covered {regions_covered} distinct regions")

    # No single-country anchoring: first 80 chars should not open with a country name or
    # ISO2 code as a standalone token. Use word-boundary matching to avoid false positives
    # on common English prefixes that share letters with ISO codes (e.g. "br" in "broadly").
    first_words = summary[:80]
    anchor_tokens = [
        "brazil", "united states", "usa", "china",
        r"\bus\b", r"\bbr\b", r"\bcn\b",
    ]
    anchored = any(re.search(pattern, first_words) for pattern in anchor_tokens)
    no_anchoring = 0.0 if anchored else 1.0
    if not anchored:
        reasoning.append("summary did not open with a single-country anchor")

    # Data year citation: any 4-digit year in the range 2020-2026
    years_cited = re.findall(r"\b20(2[0-6])\b", combined_text)
    data_year_citation = 1.0 if years_cited else 0.0
    if years_cited:
        reasoning.append(f"summary cited year 20{years_cited[0]}")

    return {
        "groundedness": round(groundedness, 3),
        "cross_regional_coverage": round(cross_regional, 3),
        "no_single_country_anchoring": round(no_anchoring, 3),
        "data_year_citation": round(data_year_citation, 3),
        "reasoning": "; ".join(reasoning) or "rubric found no strong global overview signals",
    }


def _classify_expected_trend(percent_change: float | None) -> str:
    """Return the expected trend label for the repo's public Step 1 contract."""
    if percent_change is None:
        return "stable"
    if percent_change > 1.0:
        return "improving"
    if percent_change < -1.0:
        return "declining"
    return "stable"


def _direction_signal_matches(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    """Return whether the indicator output communicates the right direction of change."""
    expected_trend = _classify_expected_trend(judge_input.get("percent_change"))
    if result.get("trend") == expected_trend:
        return True

    narrative = str(result.get("narrative", "")).lower()
    positive_signals = ("increase", "increased", "rose", "rising", "grew", "growth", "accelerated", "improved", "narrowed")
    negative_signals = ("decrease", "decreased", "fell", "falling", "declined", "declining", "contracted", "weakened", "widened")
    stable_signals = ("stable", "stabilized", "stabilising", "stabilizing", "flat", "unchanged")
    if expected_trend == "improving":
        return any(signal in narrative for signal in positive_signals)
    if expected_trend == "declining":
        return any(signal in narrative for signal in negative_signals)
    return any(signal in narrative for signal in stable_signals)


def _contains_numeric_reference(text: str, values: list[Any]) -> bool:
    """Return whether a text block references one of the supplied numeric values."""
    normalized_text = text.lower()
    for value in values:
        for token in _numeric_tokens(value):
            if token in normalized_text:
                return True
    return False


def _numeric_tokens(value: Any) -> list[str]:
    """Return candidate string tokens for one numeric value."""
    if value is None or value == "":
        return []
    if isinstance(value, int):
        return [str(value), f"{value:,}".replace(",", "")]
    if isinstance(value, float):
        rounded = round(value, 1)
        return [
            f"{rounded:.1f}",
            f"{rounded:.1f}%".replace("+-", "-"),
            str(int(round(value))),
        ]
    return [str(value).lower()]


def _count_indicator_mentions(text: str, indicators: list[dict[str, Any]]) -> int:
    """Count how many distinct indicator themes are mentioned in a synthesis."""
    mentioned_themes = 0
    for indicator in indicators:
        if any(keyword in text for keyword in _indicator_keywords(indicator)):
            mentioned_themes += 1
    return mentioned_themes


def _indicator_keywords(indicator: dict[str, Any]) -> tuple[str, ...]:
    """Return simple keyword anchors for one indicator."""
    indicator_code = str(indicator.get("indicator_code", ""))
    if indicator_code == "NY.GDP.MKTP.KD.ZG":
        return ("gdp", "growth")
    if indicator_code == "FP.CPI.TOTL.ZG":
        return ("inflation", "cpi", "prices")
    if indicator_code == "SL.UEM.TOTL.ZS":
        return ("unemployment", "labour", "labor", "jobs")
    if indicator_code == "GC.DOD.TOTL.GD.ZS":
        return ("debt", "fiscal", "government debt")
    if indicator_code == "BN.CAB.XOKA.GD.ZS":
        return ("current account", "external", "balance")
    if indicator_code == "FM.LBL.BMNY.GD.ZS":
        return ("money", "liquidity", "broad money")
    indicator_name = str(indicator.get("indicator_name", "")).lower()
    return tuple(token for token in indicator_name.replace("(", " ").replace(")", " ").split() if len(token) > 3)


def _missing_data_language_is_honest(text: str, indicators: list[dict[str, Any]]) -> bool:
    """Return whether missing-data wording matches the supplied synthesis inputs."""
    text_mentions_missing = any(
        keyword in text for keyword in ("unavailable", "missing data", "data is unavailable")
    )
    any_missing_inputs = any(indicator.get("latest_value") is None for indicator in indicators)
    if any_missing_inputs:
        return text_mentions_missing
    return not text_mentions_missing


def _outlook_is_plausible(outlook: Any, high_risk_count: int) -> bool:
    """Return whether the outlook is plausible for the observed high-risk count."""
    normalized_outlook = str(outlook or "").lower()
    if high_risk_count >= 3:
        return normalized_outlook in {"bearish", "cautious"}
    if high_risk_count == 0:
        return normalized_outlook in {"bullish", "cautious"}
    return normalized_outlook in {"cautious", "bearish"}


def _build_indicator_judge_prompt(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> str:
    """Return the Step 1 evaluation prompt."""
    return (
        "<indicator_input>\n"
        f"{json.dumps(judge_input, indent=2, sort_keys=True, default=str)}\n"
        "</indicator_input>\n\n"
        "<model_output>\n"
        f"{json.dumps(result, indent=2, sort_keys=True, default=str)}\n"
        "</model_output>\n\n"
        "Evaluate whether the model output stays grounded in the supplied indicator input."
    )


def _build_synthesis_judge_prompt(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> str:
    """Return the Step 2 evaluation prompt."""
    return (
        "<indicator_set>\n"
        f"{json.dumps(judge_input, indent=2, sort_keys=True, default=str)}\n"
        "</indicator_set>\n\n"
        "<model_output>\n"
        f"{json.dumps(result, indent=2, sort_keys=True, default=str)}\n"
        "</model_output>\n\n"
        "Evaluate whether the country synthesis is grounded in the supplied indicators and whether the "
        "macro narrative is coherent."
    )


def _build_global_overview_judge_prompt(
    judge_input: dict[str, Any],
    result: dict[str, Any],
) -> str:
    """Return the Step 3 evaluation prompt."""
    return (
        "<country_briefings>\n"
        f"{json.dumps(judge_input.get('country_briefings', []), indent=2, sort_keys=True, default=str)}\n"
        "</country_briefings>\n\n"
        "<model_output>\n"
        f"{json.dumps(result, indent=2, sort_keys=True, default=str)}\n"
        "</model_output>\n\n"
        "Evaluate whether the global overview is grounded in the supplied country briefings, "
        "covers multiple regions, avoids single-country anchoring, and cites the data year."
    )


def _is_full_approved_scope(requested_country_codes: list[str]) -> bool:
    """Return whether the requested evaluation scope matches the approved full panel."""
    unique_requested_country_codes = sorted(set(requested_country_codes))
    return (
        len(requested_country_codes)
        == EVALUATION_GATE_THRESHOLDS["required_country_count"]
        and unique_requested_country_codes == sorted(MONITORED_COUNTRY_CODES)
    )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the evaluation harness."""
    parser = argparse.ArgumentParser(description="Run the World Analyst live AI evaluation harness.")
    parser.add_argument(
        "--provider",
        default=None,
        help="Optional live AI provider override.",
    )
    parser.add_argument(
        "--countries",
        default=",".join(MONITORED_COUNTRY_CODES),
        help="Comma-separated monitored-country codes to evaluate.",
    )
    parser.add_argument(
        "--judge-model",
        default=os.environ.get("WORLD_ANALYST_EVAL_JUDGE_MODEL"),
        help="Optional Google judge model used for groundedness and coherence scoring.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the evaluation harness and print the structured report to stdout."""
    args = _parse_args()
    judge = (
        create_google_evaluation_judge(args.judge_model)
        if args.judge_model
        else create_builtin_evaluation_judge()
    )
    report = evaluate_live_baseline(
        provider=args.provider,
        country_codes=[country_code.strip().upper() for country_code in args.countries.split(",") if country_code.strip()],
        judge=judge,
    )
    sys.stdout.write(f"{json.dumps(report, indent=2, sort_keys=True)}\n")
    try:
        enforce_evaluation_gate(report)
    except EvaluationGateFailure:
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
