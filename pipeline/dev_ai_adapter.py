"""Deterministic development AI adapter for local runs."""

from __future__ import annotations

from typing import Any


class DeterministicDevelopmentAIClient:
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
        anomaly_text = " The latest move is anomalous versus the recent history." if is_anomaly else ""

        narrative = (
            f"{context['indicator_name']} printed {_format_value(indicator_code, latest_value)} in {context['data_year']}, "
            f"{change_text}. {significance}{anomaly_text}"
        )

        return {
            "trend": trend,
            "narrative": narrative,
            "risk_level": risk_level,
            "confidence": confidence,
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

        summary = (
            f"{country_name} enters the latest reading with growth at {_format_value('NY.GDP.MKTP.KD.ZG', growth.get('latest_value'))}, "
            f"inflation at {_format_value('FP.CPI.TOTL.ZG', inflation.get('latest_value'))}, and unemployment still elevated at "
            f"{_format_value('SL.UEM.TOTL.ZS', unemployment.get('latest_value'))}. "
            f"The macro mix remains fragile as fiscal pressure has pushed government debt to "
            f"{_format_value('GC.DOD.TOTL.GD.ZS', debt.get('latest_value'))} while the current account sits at "
            f"{_format_value('BN.CAB.XOKA.GD.ZS', current_account.get('latest_value'))}. "
            "The balance of signals points to persistent sovereign and household stress rather than a clean recovery."
        )

        risk_flags = [
            f"Growth is running at {_format_value('NY.GDP.MKTP.KD.ZG', growth.get('latest_value'))}, leaving little buffer against further supply or power shocks.",
            f"Inflation remains sticky at {_format_value('FP.CPI.TOTL.ZG', inflation.get('latest_value'))}, limiting room for an easier policy stance.",
            f"Government debt has climbed to {_format_value('GC.DOD.TOTL.GD.ZS', debt.get('latest_value'))} and the current account is at {_format_value('BN.CAB.XOKA.GD.ZS', current_account.get('latest_value'))}, tightening fiscal and external space.",
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


def _classify_risk(indicator_code: str, latest_value: float | None, is_anomaly: bool) -> str:
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
    if indicator_code in {"NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS", "BN.CAB.XOKA.GD.ZS", "GC.DOD.TOTL.GD.ZS"}:
        return f"{value:.1f}%"
    return f"{value:,.2f}"
