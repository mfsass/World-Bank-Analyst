"""Business tests for the live AI evaluation harness."""

from __future__ import annotations

from typing import Any

from pipeline.dev_ai_adapter import create_development_client
from pipeline.evaluation import (
    EVALUATION_GATE_THRESHOLDS,
    EvaluationGateFailure,
    create_builtin_evaluation_judge,
    enforce_evaluation_gate,
    evaluate_live_baseline,
)
from pipeline.fetcher import INDICATORS, LiveFetchResult
from pipeline.local_data import load_local_data_points


def test_evaluation_harness_aggregates_reliability_latency_and_usage_inputs() -> None:
    """The evaluation harness should return a structured report for PRD closeout review."""

    def fake_live_fetcher(
        country_codes: list[str],
        run_id: str | None = None,
    ) -> LiveFetchResult:
        del run_id
        assert country_codes == ["BR"]
        data_points = load_local_data_points("BR")
        raw_payloads = {
            indicator_code: {"indicator_code": indicator_code}
            for indicator_code in INDICATORS
        }
        return LiveFetchResult(
            data_points=data_points,
            raw_payloads=raw_payloads,
            failures=(),
        )

    report = evaluate_live_baseline(
        ai_client=create_development_client(),
        country_codes=["BR"],
        live_fetcher=fake_live_fetcher,
    )

    assert report["scope"]["requested_country_codes"] == ["BR"]
    assert report["fetch"]["failures"] == []
    assert report["steps"]["indicator_analysis"]["cases_total"] == len(INDICATORS)
    assert report["steps"]["indicator_analysis"]["schema_valid_cases"] == len(INDICATORS)
    assert report["steps"]["indicator_analysis"]["degraded_cases"] == 0
    assert report["steps"]["macro_synthesis"]["cases_total"] == 1
    assert report["steps"]["macro_synthesis"]["providers"] == [
        "deterministic-development:local-fixture-v1"
    ]
    assert report["steps"]["indicator_analysis"]["usage_totals"] == {}
    assert report["thresholds"]["max_full_run_cost_usd"] == EVALUATION_GATE_THRESHOLDS["max_full_run_cost_usd"]
    assert report["gate"]["passes"] is False
    assert "Groundedness and coherence scoring was not configured" in report["gate"]["failures"][0] or (
        "Groundedness and coherence scoring was not configured" in " ".join(report["gate"]["failures"])
    )


class EvaluatedStubAIClient:
    """AI test double that emits usage metadata for a passing gate scenario."""

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        delegate = create_development_client().analyse_indicator(context)
        delegate["ai_provenance"].update(
            {
                "provider": "stub-provider",
                "model": "stub-model",
                "usage": {
                    "prompt_token_count": 1_000,
                    "candidates_token_count": 500,
                },
            }
        )
        return delegate

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        delegate = create_development_client().synthesise_country(indicators)
        delegate["ai_provenance"].update(
            {
                "provider": "stub-provider",
                "model": "stub-model",
                "usage": {
                    "prompt_token_count": 2_000,
                    "candidates_token_count": 1_000,
                },
            }
        )
        return delegate


def test_evaluation_harness_applies_documented_gate_thresholds() -> None:
    """The evaluation gate should pass only when the documented thresholds are satisfied."""

    def fake_live_fetcher(
        country_codes: list[str],
        run_id: str | None = None,
    ) -> LiveFetchResult:
        del run_id
        base_points = load_local_data_points("BR")
        data_points: list[dict[str, Any]] = []
        for country_code in country_codes:
            data_points.extend(
                [{**point, "country_code": country_code} for point in base_points]
            )
        raw_payloads = {
            indicator_code: {"indicator_code": indicator_code}
            for indicator_code in INDICATORS
        }
        return LiveFetchResult(
            data_points=data_points,
            raw_payloads=raw_payloads,
            failures=(),
        )

    def judge(_judge_input: dict[str, Any], _result: dict[str, Any]) -> dict[str, Any]:
        return {"groundedness": 0.9, "coherence": 0.92}

    report = evaluate_live_baseline(
        ai_client=EvaluatedStubAIClient(),
        country_codes=[
            "BR", "CA", "GB", "US", "BS", "CO", "SV", "GE", "HU",
            "MY", "NZ", "RU", "SG", "ES", "CH", "TR", "UY",
        ],
        live_fetcher=fake_live_fetcher,
        judge=judge,
        pricing_by_model={
            "stub-provider:stub-model": {
                "prompt_token_count": 0.1,
                "candidates_token_count": 0.1,
            }
        },
    )

    assert report["gate"]["passes"] is True
    assert report["gate"]["failures"] == []
    assert report["gate"]["estimated_full_run_cost_usd"]["configured"] is True
    assert (
        report["gate"]["estimated_full_run_cost_usd"]["total_cost_usd"]
        <= EVALUATION_GATE_THRESHOLDS["max_full_run_cost_usd"]
    )
    enforce_evaluation_gate(report)


def test_evaluation_gate_raises_when_required_inputs_are_missing() -> None:
    """The evaluation harness should be enforceable as a real gate, not just telemetry."""
    failing_report = {
        "gate": {
            "passes": False,
            "failures": [
                "Evaluation did not run the full approved 17-country scope.",
                "Groundedness and coherence scoring was not configured for this run.",
            ],
        }
    }

    try:
        enforce_evaluation_gate(failing_report)
    except EvaluationGateFailure as exc:
        assert "17-country scope" in str(exc)
        assert "Groundedness and coherence" in str(exc)
    else:
        raise AssertionError("Expected the evaluation gate to raise on failing evidence.")


def test_builtin_evaluation_judge_returns_normalized_scores() -> None:
    """The default rubric should emit bounded groundedness/coherence scores."""
    judge = create_builtin_evaluation_judge()

    indicator_result = judge(
        {
            "indicator_code": "NY.GDP.MKTP.KD.ZG",
            "indicator_name": "GDP growth (annual %)",
            "latest_value": 0.6,
            "previous_value": 1.2,
            "percent_change": -50.0,
            "is_anomaly": True,
            "data_year": 2024,
        },
        {
            "trend": "declining",
            "narrative": "GDP growth printed 0.6 in 2024, down sharply from the prior year.",
            "risk_level": "high",
            "confidence": "high",
        },
    )
    synthesis_result = judge(
        {
            "indicators": [
                {
                    "indicator_code": "NY.GDP.MKTP.KD.ZG",
                    "indicator_name": "GDP growth (annual %)",
                    "latest_value": 0.6,
                    "percent_change": -50.0,
                    "risk_level": "high",
                    "is_anomaly": True,
                },
                {
                    "indicator_code": "FP.CPI.TOTL.ZG",
                    "indicator_name": "Inflation, consumer prices (annual %)",
                    "latest_value": 6.4,
                    "percent_change": 12.0,
                    "risk_level": "high",
                    "is_anomaly": False,
                },
            ]
        },
        {
            "summary": "GDP growth slowed to 0.6 while inflation held at 6.4, leaving the macro picture fragile.",
            "risk_flags": [
                "Growth is weak at 0.6.",
                "Inflation remains elevated at 6.4.",
            ],
            "outlook": "bearish",
        },
    )

    assert 0.0 <= indicator_result["groundedness"] <= 1.0
    assert 0.0 <= synthesis_result["groundedness"] <= 1.0
    assert 0.0 <= synthesis_result["coherence"] <= 1.0
