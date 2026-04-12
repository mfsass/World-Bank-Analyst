"""Deterministic development AI adapter for local runs."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pipeline.ai_client import (
    AIClient,
    STEP1_NAME,
    STEP1_PROMPT_VERSION,
    STEP2_NAME,
    STEP2_PROMPT_VERSION,
    STEP3_NAME,
    STEP3_PROMPT_VERSION,
)


class DeterministicDevelopmentAIClient(AIClient):
    """Generate repeatable indicator and country narratives for local runs."""

    _PROVIDER_NAME = "deterministic-development"
    _MODEL_NAME = "local-fixture-v1"

    def analyse_indicator(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return deterministic per-indicator analysis.

        Args:
            context: Prepared indicator context from the analyser.

        Returns:
            Stable structured analysis dictionary.
        """
        indicator_code = context["indicator_code"]
        latest_value = context["latest_value"]
        percent_change = context.get("percent_change")
        is_anomaly = context.get("is_anomaly", False)

        trend = _classify_trend(percent_change)
        risk_level = _classify_risk(indicator_code, latest_value, is_anomaly)
        confidence = "high" if context.get("previous_value") is not None else "medium"

        change_text = _format_change(percent_change)
        significance = _indicator_significance(indicator_code, latest_value)
        anomaly_text = (
            " The latest move is anomalous versus the recent history."
            if is_anomaly
            else ""
        )

        narrative = (
            f"{context['indicator_name']} printed {_format_value(indicator_code, latest_value)} in {context['data_year']}, "
            f"{change_text}. {significance}{anomaly_text}"
        )

        return {
            "trend": trend,
            "narrative": narrative,
            "risk_level": risk_level,
            "confidence": confidence,
            "ai_provenance": _build_ai_provenance(
                step_name=STEP1_NAME,
                prompt_version=STEP1_PROMPT_VERSION,
                prompt_input=context,
                provider=self._PROVIDER_NAME,
                model=self._MODEL_NAME,
            ),
        }

    def synthesise_country(self, indicators: list[dict[str, Any]]) -> dict[str, Any]:
        """Return deterministic macro synthesis for one country.

        Args:
            indicators: Indicator contexts enriched with deterministic analysis.

        Returns:
            Stable country synthesis dictionary.
        """
        by_code = {indicator["indicator_code"]: indicator for indicator in indicators}
        country_name = indicators[0]["country_name"] if indicators else "This country"

        growth = by_code.get("NY.GDP.MKTP.KD.ZG", {})
        inflation = by_code.get("FP.CPI.TOTL.ZG", {})
        unemployment = by_code.get("SL.UEM.TOTL.ZS", {})
        current_account = by_code.get("BN.CAB.XOKA.GD.ZS", {})
        debt = by_code.get("GC.DOD.TOTL.GD.ZS", {})
        growth_value = growth.get("latest_value")
        inflation_value = inflation.get("latest_value")
        unemployment_value = unemployment.get("latest_value")
        current_account_value = current_account.get("latest_value")
        debt_value = debt.get("latest_value")

        # Missing live series should be called unavailable explicitly instead of being narrated as a move to n/a.
        summary = (
            f"{country_name} enters the latest reading with {_build_growth_summary(growth_value)}, "
            f"{_build_inflation_summary(inflation_value)}, and {_build_unemployment_summary(unemployment_value)}. "
            f"{_build_balance_summary(debt_value, current_account_value)} "
            "The balance of signals points to persistent sovereign and household stress rather than a clean recovery."
        )

        risk_flags = [
            _build_growth_risk_flag(growth_value),
            _build_inflation_risk_flag(inflation_value),
            _build_balance_risk_flag(debt_value, current_account_value),
        ]

        high_risk_count = sum(
            1
            for indicator in indicators
            if indicator.get("risk_level") == "high" or indicator.get("is_anomaly")
        )
        outlook = "bearish" if high_risk_count >= 3 else "cautious"

        return {
            "summary": summary,
            "risk_flags": risk_flags,
            "outlook": outlook,
            "ai_provenance": _build_ai_provenance(
                step_name=STEP2_NAME,
                prompt_version=STEP2_PROMPT_VERSION,
                prompt_input=indicators,
                provider=self._PROVIDER_NAME,
                model=self._MODEL_NAME,
            ),
        }

    def synthesise_global_overview(
        self, country_briefings: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Return deterministic cross-country overview synthesis."""

        country_count = len(country_briefings)
        bearish_count = sum(
            1 for briefing in country_briefings if briefing.get("outlook") == "bearish"
        )
        cautious_count = sum(
            1 for briefing in country_briefings if briefing.get("outlook") == "cautious"
        )
        bullish_count = sum(
            1 for briefing in country_briefings if briefing.get("outlook") == "bullish"
        )
        dominant_country = (
            country_briefings[0]["name"] if country_briefings else "the panel"
        )

        summary = (
            f"The monitored panel currently spans {country_count} materialised country briefings, "
            f"with {bearish_count} bearish, {cautious_count} cautious, and {bullish_count} bullish outlooks. "
            f"The current operating picture is not one lead market story: it is a panel view built from all stored "
            f"country briefings, even when the sharpest pressure point is visible in {dominant_country}."
        )
        risk_flags = [
            f"{briefing['name']} remains flagged: {briefing['risk_flags'][0]}"
            for briefing in country_briefings
            if briefing.get("risk_flags")
        ][:3]
        if not risk_flags:
            risk_flags = [
                "No country-level risk flags are materialised yet for the monitored panel."
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
            "ai_provenance": _build_ai_provenance(
                step_name=STEP3_NAME,
                prompt_version=STEP3_PROMPT_VERSION,
                prompt_input=country_briefings,
                provider=self._PROVIDER_NAME,
                model=self._MODEL_NAME,
            ),
        }

    def get_provenance(self) -> dict[str, str]:
        """Return the provider and model metadata for persisted AI provenance.

        Returns:
            Minimal AI provenance payload.
        """
        return {
            "provider": self._PROVIDER_NAME,
            "model": self._MODEL_NAME,
        }


def create_development_client() -> DeterministicDevelopmentAIClient:
    """Create the deterministic development AI client.

    Returns:
        Deterministic local AI adapter.
    """
    return DeterministicDevelopmentAIClient()


def _classify_trend(percent_change: float | None) -> str:
    if percent_change is None:
        return "stable"
    if percent_change > 1.0:
        return "improving"
    if percent_change < -1.0:
        return "declining"
    return "stable"


def _classify_risk(
    indicator_code: str, latest_value: float | None, is_anomaly: bool
) -> str:
    if latest_value is None:
        return "moderate"
    if indicator_code == "NY.GDP.MKTP.KD.ZG" and latest_value < 1.0:
        return "high"
    if indicator_code == "FP.CPI.TOTL.ZG" and latest_value >= 6.0:
        return "high"
    if indicator_code == "SL.UEM.TOTL.ZS" and latest_value >= 30.0:
        return "high"
    if indicator_code == "GC.DOD.TOTL.GD.ZS" and latest_value >= 70.0:
        return "high"
    if indicator_code == "BN.CAB.XOKA.GD.ZS" and latest_value < 0.0:
        return "moderate"
    return "high" if is_anomaly else "low"


def _build_growth_summary(latest_value: float | None) -> str:
    """Build the growth clause for country synthesis."""
    if latest_value is None:
        return "growth data unavailable"
    return f"growth at {_format_value('NY.GDP.MKTP.KD.ZG', latest_value)}"


def _build_inflation_summary(latest_value: float | None) -> str:
    """Build the inflation clause for country synthesis."""
    if latest_value is None:
        return "inflation data unavailable"
    return f"inflation at {_format_value('FP.CPI.TOTL.ZG', latest_value)}"


def _build_unemployment_summary(latest_value: float | None) -> str:
    """Build the unemployment clause for country synthesis."""
    if latest_value is None:
        return "unemployment data unavailable"
    return f"unemployment still elevated at {_format_value('SL.UEM.TOTL.ZS', latest_value)}"


def _build_balance_summary(
    debt_value: float | None, current_account_value: float | None
) -> str:
    """Build the fiscal and external balance clause for country synthesis."""
    if debt_value is None and current_account_value is None:
        return (
            "The macro mix remains fragile, but government debt and current-account data are unavailable "
            "in the live source."
        )
    if debt_value is None:
        return (
            "The macro mix remains fragile as the current account sits at "
            f"{_format_value('BN.CAB.XOKA.GD.ZS', current_account_value)}, while government debt data is "
            "unavailable in the live source."
        )
    if current_account_value is None:
        return (
            "The macro mix remains fragile as fiscal pressure has pushed government debt to "
            f"{_format_value('GC.DOD.TOTL.GD.ZS', debt_value)}, while current-account data is unavailable "
            "in the live source."
        )
    return (
        "The macro mix remains fragile as fiscal pressure has pushed government debt to "
        f"{_format_value('GC.DOD.TOTL.GD.ZS', debt_value)} while the current account sits at "
        f"{_format_value('BN.CAB.XOKA.GD.ZS', current_account_value)}."
    )


def _build_growth_risk_flag(latest_value: float | None) -> str:
    """Build the growth-focused risk flag for country synthesis."""
    if latest_value is None:
        return "Growth data is unavailable in the live source, so cyclical risk should be treated as incomplete."
    return (
        f"Growth is running at {_format_value('NY.GDP.MKTP.KD.ZG', latest_value)}, leaving little buffer "
        "against further supply or power shocks."
    )


def _build_inflation_risk_flag(latest_value: float | None) -> str:
    """Build the inflation-focused risk flag for country synthesis."""
    if latest_value is None:
        return "Inflation data is unavailable in the live source, so price-pressure risk should be treated as incomplete."
    return (
        f"Inflation remains sticky at {_format_value('FP.CPI.TOTL.ZG', latest_value)}, limiting room for an "
        "easier policy stance."
    )


def _build_balance_risk_flag(
    debt_value: float | None, current_account_value: float | None
) -> str:
    """Build the fiscal and external risk flag for country synthesis."""
    if debt_value is None and current_account_value is None:
        return (
            "Government debt and current-account data are unavailable in the live source, so fiscal and "
            "external risk should be treated as incomplete."
        )
    if debt_value is None:
        return (
            "Government debt data is unavailable in the live source, while the current account is at "
            f"{_format_value('BN.CAB.XOKA.GD.ZS', current_account_value)}; treat the fiscal risk readout as "
            "incomplete."
        )
    if current_account_value is None:
        return (
            "Current-account data is unavailable in the live source, while government debt stands at "
            f"{_format_value('GC.DOD.TOTL.GD.ZS', debt_value)}; treat the external-risk readout as incomplete."
        )
    return (
        f"Government debt has climbed to {_format_value('GC.DOD.TOTL.GD.ZS', debt_value)} and the current "
        f"account is at {_format_value('BN.CAB.XOKA.GD.ZS', current_account_value)}, tightening fiscal and "
        "external space."
    )


def _indicator_significance(indicator_code: str, latest_value: float) -> str:
    if indicator_code == "NY.GDP.MKTP.KD.ZG":
        return "Growth remains too weak to absorb fiscal and labour-market pressure."
    if indicator_code == "FP.CPI.TOTL.ZG":
        return "Price pressure is still elevated for a finance audience watching rate sensitivity and household strain."
    if indicator_code == "SL.UEM.TOTL.ZS":
        return "Labour-market slack remains structurally severe and limits domestic demand resilience."
    if indicator_code == "BN.CAB.XOKA.GD.ZS":
        return "The external balance is back in deficit, which weakens the country’s shock absorber."
    if indicator_code == "GC.DOD.TOTL.GD.ZS":
        return "The fiscal position remains stretched and narrows room for counter-cyclical support."
    if indicator_code == "NY.GDP.MKTP.CD":
        return "Nominal output is softening, reinforcing the broader loss of momentum."
    return f"The latest reading of {latest_value:.2f} warrants close monitoring."


def _format_change(percent_change: float | None) -> str:
    if percent_change is None:
        return "with no prior year comparison available"
    direction = "up" if percent_change >= 0 else "down"
    return f"{direction} {abs(percent_change):.2f}% year over year"


def _format_value(indicator_code: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    if indicator_code == "NY.GDP.MKTP.CD":
        return f"${value / 1_000_000_000:.1f}B"
    if indicator_code in {
        "NY.GDP.MKTP.KD.ZG",
        "FP.CPI.TOTL.ZG",
        "SL.UEM.TOTL.ZS",
        "BN.CAB.XOKA.GD.ZS",
        "GC.DOD.TOTL.GD.ZS",
    }:
        return f"{value:.1f}%"
    return f"{value:,.2f}"


def _build_ai_provenance(
    *,
    step_name: str,
    prompt_version: str,
    prompt_input: Any,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Build the private AI provenance payload for deterministic local runs."""

    normalized_input = json.dumps(
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
    return {
        "provider": provider,
        "model": model,
        "step_name": step_name,
        "prompt_version": prompt_version,
        "degraded": False,
        "retry_count": 0,
        "repair_applied": False,
        "lineage": {
            "input_fingerprint": hashlib.sha256(
                normalized_input.encode("utf-8")
            ).hexdigest(),
            "reused_from": None,
        },
    }
