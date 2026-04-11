"""Business tests for the local first-slice pipeline."""

from __future__ import annotations

from pipeline.main import run_pipeline
from shared.repository import get_repository


def test_local_pipeline_persists_indicator_and_country_records() -> None:
    """A local pipeline run should write the mixed document types needed by the API."""
    repository = get_repository()

    summary = run_pipeline(repository=repository)

    assert summary["data_points_fetched"] == 42
    assert summary["indicators_analysed"] == 6
    assert summary["countries_synthesised"] == 1
    assert summary["indicator_records"] == 6
    assert summary["country_records"] == 1

    detail = repository.get_country_detail("ZA")
    assert detail is not None
    assert detail["code"] == "ZA"
    assert len(detail["indicators"]) == 6
    assert detail["macro_synthesis"]
    assert len(detail["risk_flags"]) == 3


def test_local_pipeline_is_deterministic_across_reruns() -> None:
    """The development adapter should keep local runs stable across reruns."""
    repository = get_repository()

    run_pipeline(repository=repository)
    first_detail = repository.get_country_detail("ZA")

    run_pipeline(repository=repository)
    second_detail = repository.get_country_detail("ZA")

    assert first_detail is not None
    assert second_detail is not None
    assert first_detail["macro_synthesis"] == second_detail["macro_synthesis"]
    assert first_detail["risk_flags"] == second_detail["risk_flags"]
    assert [indicator["ai_analysis"] for indicator in first_detail["indicators"]] == [
        indicator["ai_analysis"] for indicator in second_detail["indicators"]
    ]
