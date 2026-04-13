"""Business tests for the hardened live AI client boundary."""

from __future__ import annotations

from typing import Any

import pipeline.ai_client as ai_client_module
from pipeline.ai_client import GeminiClient, STEP1_PROMPT_VERSION, STEP2_PROMPT_VERSION


class FakeGeminiResponse:
    """Minimal SDK response carrying the generated text payload."""

    def __init__(self, text: str) -> None:
        self.text = text


class FakeGeminiModels:
    """Minimal model stub that returns queued structured-output responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def generate_content(
        self, *, model: str, contents: str, config: dict[str, Any]
    ) -> FakeGeminiResponse:
        self.calls.append(
            {
                "model": model,
                "contents": contents,
                "config": config,
            }
        )
        response_text = self._responses.pop(0)
        return FakeGeminiResponse(response_text)


class FakeGeminiSDKClient:
    """Container mirroring the SDK shape used by GeminiClient."""

    def __init__(self, responses: list[str]) -> None:
        self.models = FakeGeminiModels(responses)


def test_gemini_indicator_analysis_uses_gemma4_low_variance_config_and_repairs_fence() -> (
    None
):
    """Step 1 should stay on Gemma 4, validate structured JSON, and repair a stray fence."""

    fake_client = FakeGeminiSDKClient(
        [
            (
                '{"trend":"declining","narrative":"Growth slowed to 0.6% in 2024, '
                'underscoring weak momentum.","risk_level":"high","confidence":"high"}\n```'
            )
        ]
    )
    client = GeminiClient(model_name="gemma-4-31b-it", client=fake_client)

    result = client.analyse_indicator(
        {
            "country_name": "South Africa",
            "country_code": "ZA",
            "indicator_name": "GDP growth (annual %)",
            "indicator_code": "NY.GDP.MKTP.KD.ZG",
            "latest_value": 0.6,
            "previous_value": 1.2,
            "percent_change": -50.0,
            "change_value": -0.6,
            "change_basis": "percentage_point",
            "signal_polarity": "higher_is_better",
            "is_anomaly": True,
            "anomaly_basis": "panel_and_historical",
            "data_year": 2024,
        }
    )

    assert result["trend"] == "declining"
    assert "0.6%" in result["narrative"]
    assert result["ai_provenance"]["prompt_version"] == STEP1_PROMPT_VERSION
    assert result["ai_provenance"]["degraded"] is False
    assert result["ai_provenance"]["repair_applied"] is True
    assert fake_client.models.calls[0]["model"] == "gemma-4-31b-it"
    assert fake_client.models.calls[0]["config"]["temperature"] == 0
    assert (
        "Year-over-Year Move: -0.60 percentage points"
        in fake_client.models.calls[0]["contents"]
    )
    assert (
        "Signal Polarity: Higher values are economically favorable"
        in fake_client.models.calls[0]["contents"]
    )


def test_gemini_macro_synthesis_repairs_trailing_fence_before_schema_validation() -> (
    None
):
    """Step 2 should survive the trailing-fence failure mode seen in the live spike."""

    fake_client = FakeGeminiSDKClient(
        [
            (
                '{"summary":"Brazil faces persistent inflation pressure alongside weak growth.",'
                '"risk_flags":["Inflation remains sticky.","Growth remains soft."],'
                '"outlook":"cautious"}\n```'
            )
        ]
    )
    client = GeminiClient(model_name="gemma-4-31b-it", client=fake_client)

    result = client.synthesise_country(
        [
            {
                "country_name": "Brazil",
                "country_code": "BR",
                "indicator_code": "FP.CPI.TOTL.ZG",
                "indicator_name": "Inflation, consumer prices (annual %)",
                "latest_value": 5.1,
                "data_year": 2024,
                "ai_analysis": "Inflation remains sticky at 5.1%.",
                "risk_level": "high",
            },
            {
                "country_name": "Brazil",
                "country_code": "BR",
                "indicator_code": "NY.GDP.MKTP.KD.ZG",
                "indicator_name": "GDP growth (annual %)",
                "latest_value": 1.0,
                "data_year": 2024,
                "ai_analysis": "Growth remains soft at 1.0%.",
                "risk_level": "moderate",
            },
        ]
    )

    assert result["outlook"] == "cautious"
    assert len(result["risk_flags"]) == 2
    assert result["ai_provenance"]["prompt_version"] == STEP2_PROMPT_VERSION
    assert result["ai_provenance"]["repair_applied"] is True
    assert result["ai_provenance"]["degraded"] is False


def test_gemini_indicator_analysis_returns_explicit_degraded_fallback_after_bounded_retries() -> (
    None
):
    """Repeated invalid structured output should degrade cleanly instead of crashing the run."""

    fake_client = FakeGeminiSDKClient(["not json", "still not json"])
    client = GeminiClient(
        model_name="gemma-4-31b-it",
        max_attempts=2,
        client=fake_client,
    )

    result = client.analyse_indicator(
        {
            "country_name": "South Africa",
            "country_code": "ZA",
            "indicator_name": "Unemployment, total (% of total labor force)",
            "indicator_code": "SL.UEM.TOTL.ZS",
            "latest_value": 32.1,
            "previous_value": 31.6,
            "percent_change": 1.58,
            "change_value": 0.5,
            "change_basis": "percentage_point",
            "signal_polarity": "lower_is_better",
            "is_anomaly": False,
            "data_year": 2024,
        }
    )

    assert result["confidence"] == "low"
    assert "degraded" in result["narrative"].lower()
    assert result["ai_provenance"]["degraded"] is True
    assert result["ai_provenance"]["retry_count"] == 1
    assert result["ai_provenance"]["lineage"]["reused_from"] is None
    assert len(fake_client.models.calls) == 2


def test_create_client_prefers_world_analyst_prefixed_live_ai_configuration(
    monkeypatch,
) -> None:
    """The live AI factory should prefer repo-prefixed config over legacy aliases."""

    captured: dict[str, Any] = {}

    class StubGeminiClient:
        def __init__(
            self,
            model_name: str = "",
            max_attempts: int = 0,
            client: Any | None = None,
        ) -> None:
            del client
            captured["model_name"] = model_name
            captured["max_attempts"] = max_attempts

    monkeypatch.setenv("WORLD_ANALYST_AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("WORLD_ANALYST_GEMINI_MODEL", "gemma-4-31b-it-stage1")
    monkeypatch.setenv("GEMINI_MODEL", "legacy-gemini-model")
    monkeypatch.setenv("WORLD_ANALYST_AI_MAX_ATTEMPTS", "3")
    monkeypatch.setattr(ai_client_module, "GeminiClient", StubGeminiClient)

    client = ai_client_module.create_client()

    assert isinstance(client, StubGeminiClient)
    assert captured == {
        "model_name": "gemma-4-31b-it-stage1",
        "max_attempts": 3,
    }
