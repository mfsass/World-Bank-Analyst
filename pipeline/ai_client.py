"""LLM abstraction layer for the two-step agentic analysis chain.

Why this exists:
    The pipeline needs to swap between Gemini and OpenAI without changing
    business logic. This module provides a single `create_client()` factory
    that returns a provider-specific client, both implementing the same
    interface: `analyse_indicator()` and `synthesise_country()`.

Why two steps:
    Step 1 (per-indicator) is I/O-parallel — one call per country-indicator pair.
    Step 2 (macro synthesis) is sequential — it needs all Step 1 outputs for a
    country before it can reason across indicators. Splitting them avoids
    context collapse and keeps per-call token budgets low.

Why schema-constrained output:
    Prompting the LLM to "return JSON" is unreliable across runs — it works 90%
    of the time, then silently breaks in production. Both Gemini and OpenAI now
    support schema-constrained output at the token level, which makes invalid
    JSON structurally impossible. We define the output shape once in Pydantic
    and both providers enforce it.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field
from typing import Literal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas — shared across providers
# ---------------------------------------------------------------------------
# These Pydantic models define the *contract* between the AI and the rest of
# the pipeline. They are the single source of truth for what the LLM must
# return. Field descriptions act as embedded prompt engineering.

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
    """Step 2 output: country-level synthesis across all indicators."""

    summary: str = Field(
        description="Executive summary, 3-4 sentences, suitable for a policy brief"
    )
    risk_flags: list[str] = Field(
        description="Top 2-3 specific risk factors with supporting data"
    )
    outlook: Literal["bullish", "cautious", "bearish"] = Field(
        description="Forward-looking assessment based on indicator consensus"
    )


# ---------------------------------------------------------------------------
# Prompt Templates — stable across providers, cacheable
# ---------------------------------------------------------------------------
# System instructions are long-lived and identical across calls.
# User prompts are templated with per-call data.

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

Cross-reference indicators. If GDP is weak but employment is strong,
acknowledge the tension. Be specific — cite exact figures."""


def _build_step1_prompt(context: dict[str, Any]) -> str:
    """Build the user prompt for per-indicator analysis.

    Args:
        context: Dict with indicator data from the analyser.

    Returns:
        Formatted user prompt string.
    """
    return f"""Analyse this economic indicator:

Country: {context['country_name']} ({context['country_code']})
Indicator: {context['indicator_name']}
Latest Value: {context['latest_value']}
Previous Value: {context.get('previous_value', 'N/A')}
Year-over-Year Change: {context.get('percent_change', 'N/A')}%
Anomaly Flagged: {context.get('is_anomaly', False)}
Data Year: {context['data_year']}"""


def _build_step2_prompt(indicators: list[dict[str, Any]]) -> str:
    """Build the user prompt for macro country synthesis.

    Args:
        indicators: List of per-indicator context dicts with AI analysis.

    Returns:
        Formatted user prompt string.
    """
    indicator_summary = json.dumps(indicators, indent=2, default=str)
    return f"""Synthesise these indicator analyses into a country-level assessment:

{indicator_summary}"""


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class AIClient(ABC):
    """Interface for LLM providers.

    Both Gemini and OpenAI implement this. The pipeline only sees this
    interface — it never knows which provider is running.
    """

    @abstractmethod
    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate per-indicator analysis.

        Args:
            context: Structured dict from the analyser.

        Returns:
            Dict matching IndicatorInsight schema.
        """
        ...

    @abstractmethod
    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate macro-level country synthesis.

        Args:
            indicators: List of per-indicator analysis results.

        Returns:
            Dict matching MacroSynthesis schema.
        """
        ...


# ---------------------------------------------------------------------------
# Gemini Client — Primary provider
# ---------------------------------------------------------------------------

class GeminiClient(AIClient):
    """Google Gemini via the google-genai SDK.

    Uses schema-constrained structured output — the model physically cannot
    return invalid JSON because the schema is enforced at the token level.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash") -> None:
        """Initialise Gemini client.

        Args:
            model_name: Gemini model identifier from Vertex AI.
        """
        from google import genai

        self._client = genai.Client()
        self._model_name = model_name
        logger.info("Initialised Gemini client: %s", model_name)

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate per-indicator analysis with schema-constrained output."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=_build_step1_prompt(context),
            config={
                "system_instruction": STEP1_SYSTEM,
                "response_mime_type": "application/json",
                "response_json_schema": IndicatorInsight.model_json_schema(),
            },
        )
        insight = IndicatorInsight.model_validate_json(response.text)
        return insight.model_dump()

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate macro synthesis with schema-constrained output."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=_build_step2_prompt(indicators),
            config={
                "system_instruction": STEP2_SYSTEM,
                "response_mime_type": "application/json",
                "response_json_schema": MacroSynthesis.model_json_schema(),
            },
        )
        synthesis = MacroSynthesis.model_validate_json(response.text)
        return synthesis.model_dump()


# ---------------------------------------------------------------------------
# OpenAI Client — Fallback provider
# ---------------------------------------------------------------------------

class OpenAIClient(AIClient):
    """OpenAI GPT via the openai SDK.

    Uses Strict Mode structured output — `response_format` with `strict: true`
    to enforce the JSON schema server-side.
    """

    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        """Initialise OpenAI client.

        Args:
            model_name: OpenAI model identifier.
        """
        from openai import OpenAI

        self._client = OpenAI()
        self._model_name = model_name
        logger.info("Initialised OpenAI client: %s", model_name)

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate per-indicator analysis with strict structured output."""
        response = self._client.beta.chat.completions.parse(
            model=self._model_name,
            messages=[
                {"role": "system", "content": STEP1_SYSTEM},
                {"role": "user", "content": _build_step1_prompt(context)},
            ],
            response_format=IndicatorInsight,
        )
        if response.choices[0].message.refusal:
            logger.warning("OpenAI refused Step 1: %s", response.choices[0].message.refusal)
            return IndicatorInsight(
                trend="stable", narrative="Analysis unavailable — model refusal.",
                risk_level="low", confidence="low",
            ).model_dump()

        return response.choices[0].message.parsed.model_dump()

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate macro synthesis with strict structured output."""
        response = self._client.beta.chat.completions.parse(
            model=self._model_name,
            messages=[
                {"role": "system", "content": STEP2_SYSTEM},
                {"role": "user", "content": _build_step2_prompt(indicators)},
            ],
            response_format=MacroSynthesis,
        )
        if response.choices[0].message.refusal:
            logger.warning("OpenAI refused Step 2: %s", response.choices[0].message.refusal)
            return MacroSynthesis(
                summary="Synthesis unavailable — model refusal.",
                risk_flags=[], outlook="cautious",
            ).model_dump()

        return response.choices[0].message.parsed.model_dump()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(provider: str = "gemini") -> AIClient:
    """Create the appropriate AI client.

    Why a factory:
        The pipeline calls `create_client()` once at startup. Everything
        downstream uses the AIClient interface. To switch providers, change
        the AI_PROVIDER env var — no code changes needed.

    Args:
        provider: Either 'gemini' or 'openai'.

    Returns:
        Configured AIClient instance.

    Raises:
        ValueError: If provider is not recognised.
    """
    providers = {
        "gemini": GeminiClient,
        "openai": OpenAIClient,
    }
    if provider not in providers:
        raise ValueError(
            f"Unknown AI provider: '{provider}'. "
            f"Supported: {', '.join(providers.keys())}"
        )
    return providers[provider]()
