"""LLM abstraction layer for the analysis and synthesis chain.

Why this exists:
    The pipeline needs one provider-facing seam for live AI while keeping the
    caller contract stable: `analyse_indicator()`, `synthesise_country()`, and
    `synthesise_global_overview()`.

Why it is hardened:
    Real provider output can still fail around the edges even with structured
    generation. Gemma 4 proved viable for this repo, but only after lowering
    variance, stripping bounded stray Markdown fences, retrying a small number
    of times, and falling back explicitly when validation still fails.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_AI_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemma-4-31b-it"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_MAX_ATTEMPTS = 2
STEP1_NAME = "indicator_analysis"
STEP2_NAME = "macro_synthesis"
STEP3_NAME = "panel_overview"
STEP1_PROMPT_VERSION = "step1.v1.0.0"
STEP2_PROMPT_VERSION = "step2.v2.0.0"
STEP3_PROMPT_VERSION = "step3.v2.0.0"


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------


class IndicatorInsight(BaseModel):
    """Step 1 output: analysis of a single indicator for a single country."""

    trend: Literal["improving", "stable", "declining"] = Field(
        description="Direction of the indicator based on year-over-year change"
    )
    narrative: str = Field(
        description="2-3 sentence analysis: significance, drivers, risk"
    )
    risk_level: Literal["low", "moderate", "high"] = Field(
        description="Risk implication based on trend and anomaly status"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Data completeness and reliability assessment"
    )


class MacroSynthesis(BaseModel):
    """Structured synthesis output reused for country and panel briefings."""

    summary: str = Field(
        description="Executive summary, 3-4 sentences, suitable for a policy brief"
    )
    risk_flags: list[str] = Field(
        description="Top 2-3 specific risk factors with supporting data"
    )
    outlook: Literal["bullish", "cautious", "bearish"] = Field(
        description="Forward-looking assessment based on indicator consensus"
    )
    regime_label: Literal[
        "recovery", "expansion", "overheating", "contraction", "stagnation"
    ] = Field(
        default="stagnation",
        description="Macroeconomic regime classification derived from the indicator consensus",
    )


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

STEP1_SYSTEM = """You are an economic data analyst producing structured insights
for a global intelligence dashboard. You receive pre-computed statistics from
Pandas — trust the numbers.

Your job is NARRATIVE interpretation, not mathematical computation:
- Explain the significance of the value and trend.
- Identify potential drivers.
- Assess the risk implication.

Write for a professional audience. Be precise. Cite specific numbers.
No filler. Reuters wire-service tone."""

STEP2_SYSTEM = """You are a senior macroeconomic strategist synthesising indicator
analyses into a country-level intelligence briefing.

You receive multiple indicator insights for a single country. Your task:
1. Identify the dominant macroeconomic narrative.
2. Flag the top 2-3 risk factors with supporting data points.
3. Write an executive summary suitable for a policy brief (max 200 words).
4. Assign an outlook based on indicator consensus.
5. Classify the macroeconomic regime: recovery (improving from trough),
   expansion (broad-based growth), overheating (growth with rising imbalances),
   contraction (declining output or demand), or stagnation (flat growth with
   persistent structural weakness).

Cross-reference indicators. If GDP is weak but employment is strong,
acknowledge the tension. Be specific — cite exact figures."""

STEP3_SYSTEM = """You are a senior macroeconomic strategist writing a global economic
intelligence brief for professional financial users.

You receive country-level briefings from a 17-country coverage set spanning six major regions:
Europe, Latin America, Asia-Pacific, Sub-Saharan Africa, the Middle East & North Africa,
and North America/South Asia.

Your task:
1. Write an executive summary of the global economic picture. Lead with the dominant
   macro narrative across regions — not any single country's story. Open with what
   matters most to institutional investors and analysts: growth trajectory, inflation
   regime, fiscal pressures, or trade vulnerabilities.
2. Flag the top 2–3 cross-country risk concentrations. Each flag must cite at least
   two countries and name the specific indicator driving the risk.
3. Assign a global outlook (bullish / cautious / bearish) based on the
   balance of country outlooks across the coverage set.

Hard rules:
- NEVER open your summary with a single country's name or story.
- Cover at least three distinct geographic regions in the executive summary.
- Reference the data year when citing trends (the data year is provided in the prompt).
- Keep the summary to 220 words maximum. Each risk flag is one concise sentence.
- Write in plain financial English. No jargon: no "monitored-set", "materialised",
  "panel" in user-facing prose, or operational/pipeline language of any kind."""


def _build_step1_prompt(context: dict[str, Any]) -> str:
    """Build the Step 1 user prompt."""

    return f"""Analyse this economic indicator:

Country: {context['country_name']} ({context['country_code']})
Indicator: {context['indicator_name']}
Latest Value: {context['latest_value']}
Previous Value: {context.get('previous_value', 'N/A')}
Year-over-Year Change: {context.get('percent_change', 'N/A')}%
Anomaly Flagged: {context.get('is_anomaly', False)}
Data Year: {context['data_year']}"""


def _build_step2_prompt(indicators: list[dict[str, Any]]) -> str:
    """Build the Step 2 user prompt."""

    ordered_indicators = _ordered_indicator_inputs(indicators)
    indicator_summary = json.dumps(
        ordered_indicators, indent=2, default=str, sort_keys=True
    )
    return f"""Synthesise these indicator analyses into a country-level assessment:

{indicator_summary}"""


def _build_step3_prompt(country_briefings: list[dict[str, Any]]) -> str:
    """Build the Step 3 user prompt with data year context."""

    ordered_briefings = _ordered_country_briefings(country_briefings)
    # Extract the most recent data year across all briefings for the prompt header.
    data_year = max(
        (int(b.get("data_year", 0) or 0) for b in ordered_briefings),
        default=0,
    ) or None
    year_note = f" (data year: {data_year})" if data_year else ""
    briefing_summary = json.dumps(
        ordered_briefings, indent=2, default=str, sort_keys=True
    )
    return (
        f"Synthesise these 17-country briefings into a global economic overview{year_note}:\n\n"
        f"{briefing_summary}"
    )


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------


class AIClient(ABC):
    """Interface for live and deterministic AI clients."""

    @abstractmethod
    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate per-indicator analysis."""
        ...

    @abstractmethod
    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate macro-level country synthesis."""
        ...

    @abstractmethod
    def synthesise_global_overview(
        self, country_briefings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate cross-country global economic synthesis from country briefings."""
        ...

    @abstractmethod
    def get_provenance(self) -> dict[str, Any]:
        """Return provider and model metadata for persisted provenance."""
        ...


# ---------------------------------------------------------------------------
# Gemini Client
# ---------------------------------------------------------------------------


class GeminiClient(AIClient):
    """Google GenAI client hardened for the repo's structured-output needs."""

    _PROVIDER_NAME = "google-genai"

    def __init__(
        self,
        model_name: str = DEFAULT_GEMINI_MODEL,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        client: Any | None = None,
    ) -> None:
        """Initialise the Gemini client.

        Args:
            model_name: Google model identifier.
            max_attempts: Maximum bounded attempts before degraded fallback.
            client: Optional injected SDK client for tests.
        """
        if client is None:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key) if api_key else genai.Client()

        self._client = client
        self._model_name = model_name
        self._max_attempts = max(1, max_attempts)
        logger.info(
            "Initialised Gemini client: model=%s max_attempts=%d",
            model_name,
            self._max_attempts,
        )

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate per-indicator analysis with bounded repair and fallback."""

        normalized_input = _normalise_indicator_input(context)
        return self._generate_structured_result(
            step_name=STEP1_NAME,
            prompt_version=STEP1_PROMPT_VERSION,
            prompt_input=normalized_input,
            contents=_build_step1_prompt(context),
            system_instruction=STEP1_SYSTEM,
            response_model=IndicatorInsight,
            fallback_payload=_build_indicator_fallback(context),
            max_output_tokens=280,
        )

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate macro synthesis with bounded repair and fallback."""

        ordered_indicators = _ordered_indicator_inputs(indicators)
        return self._generate_structured_result(
            step_name=STEP2_NAME,
            prompt_version=STEP2_PROMPT_VERSION,
            prompt_input=ordered_indicators,
            contents=_build_step2_prompt(ordered_indicators),
            system_instruction=STEP2_SYSTEM,
            response_model=MacroSynthesis,
            fallback_payload=_build_macro_fallback(ordered_indicators),
            max_output_tokens=420,
        )

    def synthesise_global_overview(
        self, country_briefings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate monitored-set overview with bounded repair and fallback."""

        ordered_briefings = _ordered_country_briefings(country_briefings)
        return self._generate_structured_result(
            step_name=STEP3_NAME,
            prompt_version=STEP3_PROMPT_VERSION,
            prompt_input=ordered_briefings,
            contents=_build_step3_prompt(ordered_briefings),
            system_instruction=STEP3_SYSTEM,
            response_model=MacroSynthesis,
            fallback_payload=_build_panel_overview_fallback(ordered_briefings),
            max_output_tokens=420,
        )

    def get_provenance(self) -> dict[str, Any]:
        """Return provider and model metadata."""

        return {
            "provider": self._PROVIDER_NAME,
            "model": self._model_name,
        }

    def _generate_structured_result(
        self,
        *,
        step_name: str,
        prompt_version: str,
        prompt_input: Any,
        contents: str,
        system_instruction: str,
        response_model: type[BaseModel],
        fallback_payload: dict[str, Any],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        """Call Gemini with bounded retries and degraded fallback."""

        input_fingerprint = build_input_fingerprint(
            step_name=step_name,
            prompt_version=prompt_version,
            prompt_input=prompt_input,
            provider=self._PROVIDER_NAME,
            model=self._model_name,
        )
        last_error = "No response returned."
        repair_applied = False
        last_usage: dict[str, Any] | None = None
        provider_model_version: str | None = None

        from google.genai.errors import APIError, ClientError

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                        "response_json_schema": response_model.model_json_schema(),
                        # Gemma 4 proved more reliable on this repo at temperature 0.
                        "temperature": 0,
                        "max_output_tokens": max_output_tokens,
                    },
                )
                last_usage = _extract_gemini_usage_metadata(response)
                provider_model_version = getattr(response, "model_version", None)
                response_text = (getattr(response, "text", None) or "").strip()
                if not response_text:
                    raise ValueError("Empty structured response.")

                repaired_text, repaired = repair_markdown_fences(response_text)
                repair_applied = repair_applied or repaired
                parsed = response_model.model_validate_json(repaired_text)
                result = parsed.model_dump()
                result["ai_provenance"] = _build_ai_provenance(
                    provider=self._PROVIDER_NAME,
                    model=self._model_name,
                    step_name=step_name,
                    prompt_version=prompt_version,
                    input_fingerprint=input_fingerprint,
                    degraded=False,
                    retry_count=attempt - 1,
                    repair_applied=repair_applied,
                    usage=last_usage,
                    provider_model_version=provider_model_version,
                )
                return result
            except (ValidationError, ValueError, TypeError) as exc:
                last_error = str(exc)
                logger.warning(
                    "Gemini structured output validation failed for %s on attempt %d/%d: %s",
                    step_name,
                    attempt,
                    self._max_attempts,
                    exc,
                )
            except (
                APIError
            ) as exc:  # pragma: no cover - exercised by live-provider runs
                last_error = str(exc)
                logger.warning(
                    "Gemini request failed for %s on attempt %d/%d: %s",
                    step_name,
                    attempt,
                    self._max_attempts,
                    exc,
                )
                if isinstance(exc, ClientError) and getattr(
                    exc, "status", None
                ) not in {408, 429}:
                    break

        fallback_result = dict(fallback_payload)
        fallback_result["ai_provenance"] = _build_ai_provenance(
            provider=self._PROVIDER_NAME,
            model=self._model_name,
            step_name=step_name,
            prompt_version=prompt_version,
            input_fingerprint=input_fingerprint,
            degraded=True,
            retry_count=max(0, self._max_attempts - 1),
            repair_applied=repair_applied,
            degraded_reason=last_error,
            usage=last_usage,
            provider_model_version=provider_model_version,
        )
        return fallback_result


# ---------------------------------------------------------------------------
# OpenAI Client
# ---------------------------------------------------------------------------


class OpenAIClient(AIClient):
    """OpenAI fallback provider with the same bounded fallback behaviour."""

    _PROVIDER_NAME = "openai"

    def __init__(
        self,
        model_name: str = DEFAULT_OPENAI_MODEL,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        client: Any | None = None,
    ) -> None:
        """Initialise the OpenAI client."""

        if client is None:
            from openai import OpenAI

            client = OpenAI()

        self._client = client
        self._model_name = model_name
        self._max_attempts = max(1, max_attempts)
        logger.info(
            "Initialised OpenAI client: model=%s max_attempts=%d",
            model_name,
            self._max_attempts,
        )

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate per-indicator analysis."""

        normalized_input = _normalise_indicator_input(context)
        return self._generate_structured_result(
            step_name=STEP1_NAME,
            prompt_version=STEP1_PROMPT_VERSION,
            prompt_input=normalized_input,
            messages=[
                {"role": "system", "content": STEP1_SYSTEM},
                {"role": "user", "content": _build_step1_prompt(context)},
            ],
            response_model=IndicatorInsight,
            fallback_payload=_build_indicator_fallback(context),
        )

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate macro synthesis."""

        ordered_indicators = _ordered_indicator_inputs(indicators)
        return self._generate_structured_result(
            step_name=STEP2_NAME,
            prompt_version=STEP2_PROMPT_VERSION,
            prompt_input=ordered_indicators,
            messages=[
                {"role": "system", "content": STEP2_SYSTEM},
                {"role": "user", "content": _build_step2_prompt(ordered_indicators)},
            ],
            response_model=MacroSynthesis,
            fallback_payload=_build_macro_fallback(ordered_indicators),
        )

    def synthesise_global_overview(
        self, country_briefings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate monitored-set overview synthesis."""

        ordered_briefings = _ordered_country_briefings(country_briefings)
        return self._generate_structured_result(
            step_name=STEP3_NAME,
            prompt_version=STEP3_PROMPT_VERSION,
            prompt_input=ordered_briefings,
            messages=[
                {"role": "system", "content": STEP3_SYSTEM},
                {
                    "role": "user",
                    "content": _build_step3_prompt(ordered_briefings),
                },
            ],
            response_model=MacroSynthesis,
            fallback_payload=_build_panel_overview_fallback(ordered_briefings),
        )

    def get_provenance(self) -> dict[str, Any]:
        """Return provider and model metadata."""

        return {
            "provider": self._PROVIDER_NAME,
            "model": self._model_name,
        }

    def _generate_structured_result(
        self,
        *,
        step_name: str,
        prompt_version: str,
        prompt_input: Any,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        fallback_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Call OpenAI with bounded retries and degraded fallback."""

        input_fingerprint = build_input_fingerprint(
            step_name=step_name,
            prompt_version=prompt_version,
            prompt_input=prompt_input,
            provider=self._PROVIDER_NAME,
            model=self._model_name,
        )
        last_error = "No response returned."
        last_usage: dict[str, Any] | None = None

        from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.beta.chat.completions.parse(
                    model=self._model_name,
                    messages=messages,
                    response_format=response_model,
                    temperature=0,
                )
                last_usage = _extract_openai_usage(response)
                message = response.choices[0].message
                if message.refusal:
                    raise ValueError(f"Model refusal: {message.refusal}")
                if message.parsed is None:
                    raise ValueError("OpenAI returned no parsed structured output.")

                result = message.parsed.model_dump()
                result["ai_provenance"] = _build_ai_provenance(
                    provider=self._PROVIDER_NAME,
                    model=self._model_name,
                    step_name=step_name,
                    prompt_version=prompt_version,
                    input_fingerprint=input_fingerprint,
                    degraded=False,
                    retry_count=attempt - 1,
                    repair_applied=False,
                    usage=last_usage,
                )
                return result
            except ValueError as exc:
                last_error = str(exc)
                logger.warning(
                    "OpenAI structured output validation failed for %s on attempt %d/%d: %s",
                    step_name,
                    attempt,
                    self._max_attempts,
                    exc,
                )
            except (
                APIConnectionError,
                APITimeoutError,
            ) as exc:  # pragma: no cover - fallback provider
                last_error = str(exc)
                logger.warning(
                    "OpenAI request failed for %s on attempt %d/%d: %s",
                    step_name,
                    attempt,
                    self._max_attempts,
                    exc,
                )
            except APIStatusError as exc:  # pragma: no cover - fallback provider
                last_error = str(exc)
                logger.warning(
                    "OpenAI structured output failed for %s on attempt %d/%d: %s",
                    step_name,
                    attempt,
                    self._max_attempts,
                    exc,
                )
                if getattr(exc, "status_code", None) not in {
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    break
            except APIError as exc:  # pragma: no cover - fallback provider
                last_error = str(exc)
                logger.warning(
                    "OpenAI request failed for %s on attempt %d/%d: %s",
                    step_name,
                    attempt,
                    self._max_attempts,
                    exc,
                )
                break

        fallback_result = dict(fallback_payload)
        fallback_result["ai_provenance"] = _build_ai_provenance(
            provider=self._PROVIDER_NAME,
            model=self._model_name,
            step_name=step_name,
            prompt_version=prompt_version,
            input_fingerprint=input_fingerprint,
            degraded=True,
            retry_count=max(0, self._max_attempts - 1),
            repair_applied=False,
            degraded_reason=last_error,
            usage=last_usage,
        )
        return fallback_result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_client(provider: str | None = None) -> AIClient:
    """Create the configured live AI client."""

    selected_provider = (
        provider
        or os.environ.get("WORLD_ANALYST_AI_PROVIDER")
        or os.environ.get("AI_PROVIDER")
        or DEFAULT_AI_PROVIDER
    ).lower()
    max_attempts = _get_max_attempts()

    if selected_provider == "gemini":
        return GeminiClient(
            model_name=(
                os.environ.get("WORLD_ANALYST_GEMINI_MODEL")
                or os.environ.get("GEMINI_MODEL")
                or DEFAULT_GEMINI_MODEL
            ),
            max_attempts=max_attempts,
        )

    if selected_provider == "openai":
        return OpenAIClient(
            model_name=(
                os.environ.get("WORLD_ANALYST_OPENAI_MODEL")
                or os.environ.get("OPENAI_MODEL")
                or DEFAULT_OPENAI_MODEL
            ),
            max_attempts=max_attempts,
        )

    raise ValueError(
        f"Unknown AI provider: '{selected_provider}'. Supported: gemini, openai"
    )


def build_input_fingerprint(
    *,
    step_name: str,
    prompt_version: str,
    prompt_input: Any,
    provider: str,
    model: str,
) -> str:
    """Build the exact-input fingerprint used for later AI reuse lineage."""

    normalized_payload = json.dumps(
        {
            "step_name": step_name,
            "prompt_version": prompt_version,
            "provider": provider,
            "model": model,
            "prompt_input": prompt_input,
        },
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()


def repair_markdown_fences(raw_text: str) -> tuple[str, bool]:
    """Strip one leading and/or trailing Markdown fence around JSON output.

    The repair is intentionally bounded so the client does not silently reshape
    arbitrary model text before validation.
    """

    candidate = raw_text.strip()
    repaired = False

    if candidate.startswith("```json"):
        candidate = candidate[len("```json") :].lstrip()
        repaired = True
    elif candidate.startswith("```"):
        candidate = candidate[3:].lstrip()
        repaired = True

    if candidate.endswith("```"):
        candidate = candidate[:-3].rstrip()
        repaired = True

    trailing_fence_index = candidate.rfind("\n```")
    if trailing_fence_index != -1 and candidate[trailing_fence_index:].strip() == "```":
        candidate = candidate[:trailing_fence_index].rstrip()
        repaired = True

    return candidate, repaired


def _build_ai_provenance(
    *,
    provider: str,
    model: str,
    step_name: str,
    prompt_version: str,
    input_fingerprint: str,
    degraded: bool,
    retry_count: int,
    repair_applied: bool,
    degraded_reason: str | None = None,
    usage: dict[str, Any] | None = None,
    provider_model_version: str | None = None,
) -> dict[str, Any]:
    """Build the private AI provenance envelope persisted with records."""

    provenance = {
        "provider": provider,
        "model": model,
        "step_name": step_name,
        "prompt_version": prompt_version,
        "degraded": degraded,
        "retry_count": retry_count,
        "repair_applied": repair_applied,
        "lineage": {
            "input_fingerprint": input_fingerprint,
            "reused_from": None,
        },
    }
    if degraded_reason:
        provenance["degraded_reason"] = degraded_reason
    if usage:
        provenance["usage"] = usage
    if provider_model_version:
        provenance["provider_model_version"] = provider_model_version
    return provenance


def _extract_gemini_usage_metadata(response: Any) -> dict[str, Any] | None:
    """Return the stable subset of Gemini usage metadata worth persisting privately."""

    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata is None:
        return None

    usage = {
        field_name: field_value
        for field_name in (
            "prompt_token_count",
            "candidates_token_count",
            "thoughts_token_count",
            "total_token_count",
            "traffic_type",
        )
        if (field_value := getattr(usage_metadata, field_name, None)) is not None
    }
    return usage or None


def _extract_openai_usage(response: Any) -> dict[str, Any] | None:
    """Return the stable subset of OpenAI usage metadata worth persisting privately."""

    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    if hasattr(usage, "model_dump"):
        usage_payload = usage.model_dump()
    elif isinstance(usage, dict):
        usage_payload = usage
    else:
        return None

    compact_usage = {
        key: value for key, value in usage_payload.items() if value is not None
    }
    return compact_usage or None


def _ordered_indicator_inputs(indicators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return Step 2 inputs in a deterministic order for prompt and lineage stability."""

    return [
        _strip_private_fields(indicator)
        for indicator in sorted(
            indicators,
            key=lambda item: (
                str(item.get("country_code", "")),
                str(item.get("indicator_code", "")),
                int(item.get("data_year", 0) or 0),
            ),
        )
    ]


# Geographic region ordering for Step 3 prompt — leading with Europe and developed
# markets ensures the model opens with the most institutionally watched economies
# rather than anchoring to whichever code sorts first alphabetically (BR = Brazil).
_REGION_PROMPT_ORDER: dict[str, int] = {
    "Europe & Central Asia": 0,
    "North America": 1,
    "East Asia & Pacific": 2,
    "Latin America & Caribbean": 3,
    "Middle East & North Africa": 4,
    "Sub-Saharan Africa": 5,
    "South Asia": 6,
}


def _ordered_country_briefings(
    country_briefings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return Step 3 inputs ordered by geographic region then country code.

    Leading with Europe and developed markets prevents the model from anchoring
    to whichever country sorts first alphabetically (historically Brazil).
    """
    return [
        _strip_private_fields(briefing)
        for briefing in sorted(
            country_briefings,
            key=lambda item: (
                _REGION_PROMPT_ORDER.get(str(item.get("region") or ""), 99),
                str(item.get("code", "")),
            ),
        )
    ]


def _normalise_indicator_input(context: dict[str, Any]) -> dict[str, Any]:
    """Return the Step 1 input content used for lineage fingerprinting."""

    return _strip_private_fields(context)


def _strip_private_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove private AI provenance fields from prompt lineage input."""

    return {
        key: value
        for key, value in payload.items()
        if key
        not in {"ai_provenance", "source_provenance", "raw_backup_reference", "run_id"}
    }


def _build_indicator_fallback(context: dict[str, Any]) -> dict[str, Any]:
    """Create an explicit degraded Step 1 payload when structured output fails."""

    trend = _classify_trend(context.get("percent_change"))
    risk_level = "high" if context.get("is_anomaly") else "moderate"
    latest_value = context.get("latest_value")
    narrative = (
        "Live AI analysis degraded after structured-output retries. "
        f"{context['indicator_name']} stood at {_format_value(latest_value)} in {context['data_year']}; "
        "review the validated pipeline metrics directly."
    )
    return {
        "trend": trend,
        "narrative": narrative,
        "risk_level": risk_level,
        "confidence": "low",
    }


def _build_macro_fallback(indicators: list[dict[str, Any]]) -> dict[str, Any]:
    """Create an explicit degraded Step 2 payload when structured output fails."""

    country_name = (
        indicators[0].get("country_name", "This country")
        if indicators
        else "This country"
    )
    high_risk_indicators = [
        indicator
        for indicator in indicators
        if indicator.get("risk_level") == "high" or indicator.get("is_anomaly")
    ]
    summary = (
        "Live AI synthesis degraded after structured-output retries. "
        f"{country_name} still has {len(high_risk_indicators)} high-risk or anomalous signals in the validated "
        "indicator set; review the indicator narratives directly."
    )
    risk_flags = [
        (
            f"{indicator['indicator_name']} remains a flagged pressure point at "
            f"{_format_value(indicator.get('latest_value'))}."
        )
        for indicator in high_risk_indicators[:3]
    ]
    if not risk_flags:
        risk_flags = [
            "Indicator-level narratives should be reviewed directly because the live synthesis degraded."
        ]

    return {
        "summary": summary,
        "risk_flags": risk_flags,
        "outlook": "bearish" if len(high_risk_indicators) >= 3 else "cautious",
    }


def _build_panel_overview_fallback(
    country_briefings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create an explicit degraded Step 3 payload when structured output fails."""

    country_count = len(country_briefings)
    bearish_count = sum(
        1 for briefing in country_briefings if briefing.get("outlook") == "bearish"
    )
    cautious_count = sum(
        1 for briefing in country_briefings if briefing.get("outlook") == "cautious"
    )
    summary = (
        "Global AI synthesis is temporarily unavailable after structured-output retries. "
        f"The tracked dataset still contains {country_count} country briefings, "
        f"including {bearish_count} bearish and {cautious_count} cautious outlooks; "
        "review the individual country pages directly."
    )

    risk_flags = [
        f"{briefing.get('code', 'Unknown')} remains flagged: {briefing['risk_flags'][0]}"
        for briefing in country_briefings
        if briefing.get("risk_flags")
    ][:3]
    if not risk_flags:
        risk_flags = [
            "Review the individual country pages directly for the current risk picture."
        ]

    if bearish_count > 0:
        outlook = "bearish"
    elif cautious_count > 0:
        outlook = "cautious"
    else:
        outlook = "bullish"

    return {
        "summary": summary,
        "risk_flags": risk_flags,
        "outlook": outlook,
    }


def _classify_trend(
    percent_change: float | None,
) -> Literal["improving", "stable", "declining"]:
    """Map a year-over-year change into the public trend contract."""

    if percent_change is None:
        return "stable"
    if percent_change > 1.0:
        return "improving"
    if percent_change < -1.0:
        return "declining"
    return "stable"


def _format_value(value: Any) -> str:
    """Format a scalar value for degraded fallback copy."""

    if value is None:
        return "n/a"
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)


def _get_max_attempts() -> int:
    """Return the configured bounded retry count for live AI calls."""

    configured_value = os.environ.get("WORLD_ANALYST_AI_MAX_ATTEMPTS")
    if configured_value is None:
        return DEFAULT_MAX_ATTEMPTS

    try:
        return max(1, int(configured_value))
    except ValueError:
        logger.warning(
            "Invalid WORLD_ANALYST_AI_MAX_ATTEMPTS=%s; falling back to %d",
            configured_value,
            DEFAULT_MAX_ATTEMPTS,
        )
        return DEFAULT_MAX_ATTEMPTS
