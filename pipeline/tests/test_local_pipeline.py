"""Business tests for the local first-slice pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

import pipeline.main as pipeline_main
from pipeline.main import run_managed_pipeline, run_pipeline
from pipeline.storage import (
    LocalRawArchiveStore,
    _build_panel_source_provenance,
    get_raw_archive_store,
)
from shared.repository import get_repository, get_repository_backend

EXPECTED_MONITORED_COUNTRY_CODES = [
    "BR",
    "CA",
    "GB",
    "US",
    "BS",
    "CO",
    "SV",
    "GE",
    "HU",
    "MY",
    "NZ",
    "RU",
    "SG",
    "ES",
    "CH",
    "TR",
    "UY",
]


def test_repository_lists_canonical_monitored_countries() -> None:
    """The repository should expose the approved monitored-country catalog."""
    repository = get_repository()

    countries = repository.list_countries()

    assert [
        country["code"] for country in countries
    ] == EXPECTED_MONITORED_COUNTRY_CODES
    assert countries[0]["name"] == "Brazil"
    assert countries[-1]["name"] == "Uruguay"
    assert repository.get_country_metadata("UY") == {
        "code": "UY",
        "name": "Uruguay",
        "region": "Latin America & Caribbean",
        "income_level": "High income",
    }


def test_local_pipeline_persists_indicator_and_country_records() -> None:
    """A local pipeline run should stay on the deterministic ZA slice."""
    repository = get_repository()

    summary = run_pipeline(repository=repository)

    assert summary["data_points_fetched"] == 42
    assert summary["indicators_analysed"] == 6
    assert summary["countries_synthesised"] == 1
    assert summary["indicator_records"] == 6
    assert summary["country_records"] == 1
    assert summary["global_overview_records"] == 1

    detail = repository.get_country_detail("ZA")
    overview = repository.get_global_overview()
    assert detail is not None
    assert overview is not None
    assert detail["code"] == "ZA"
    assert len(detail["indicators"]) == 6
    assert detail["macro_synthesis"]
    assert len(detail["risk_flags"]) == 3
    assert detail["regime_label"] in {
        "recovery",
        "expansion",
        "overheating",
        "contraction",
        "stagnation",
    }
    assert detail["source_date_range"] == "2017:2023"
    assert all(indicator["time_series"] for indicator in detail["indicators"])
    assert all(indicator["time_series"][0]["year"] == 2017 for indicator in detail["indicators"])
    assert all(indicator["time_series"][-1]["year"] == 2023 for indicator in detail["indicators"])
    assert overview["country_count"] == 1
    assert overview["country_codes"] == ["ZA"]
    assert overview["summary"]
    assert overview["source_date_range"] == "2017:2023"
    assert repository.get_country_detail("BE") is None


def test_local_pipeline_is_deterministic_across_reruns() -> None:
    """The development adapter should keep local runs stable across reruns."""
    repository = get_repository()

    run_pipeline(repository=repository)
    first_detail = repository.get_country_detail("ZA")
    first_overview = repository.get_global_overview()

    run_pipeline(repository=repository)
    second_detail = repository.get_country_detail("ZA")
    second_overview = repository.get_global_overview()

    assert first_detail is not None
    assert second_detail is not None
    assert first_overview is not None
    assert second_overview is not None
    assert first_detail["macro_synthesis"] == second_detail["macro_synthesis"]
    assert first_detail["risk_flags"] == second_detail["risk_flags"]
    assert first_detail["regime_label"] == second_detail["regime_label"]
    assert first_overview["summary"] == second_overview["summary"]
    assert first_overview["risk_flags"] == second_overview["risk_flags"]
    assert [indicator["ai_analysis"] for indicator in first_detail["indicators"]] == [
        indicator["ai_analysis"] for indicator in second_detail["indicators"]
    ]
    assert [indicator["time_series"] for indicator in first_detail["indicators"]] == [
        indicator["time_series"] for indicator in second_detail["indicators"]
    ]


def test_pipeline_defaults_to_local_mode_when_env_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without an explicit mode, the pipeline should stay on the deterministic ZA slice."""
    repository = get_repository()
    monkeypatch.delenv("PIPELINE_MODE", raising=False)

    def fail_live_fetch(*_args, **_kwargs):
        raise AssertionError(
            "Local default should not call the live World Bank fetch path."
        )

    monkeypatch.setattr(pipeline_main, "fetch_live_data", fail_live_fetch)

    summary = run_pipeline(repository=repository)

    assert summary["countries_synthesised"] == 1
    assert repository.get_country_detail("ZA") is not None
    assert repository.get_country_detail("BR") is None


def test_local_pipeline_persists_private_provenance_and_raw_archives(
    tmp_path: Path,
) -> None:
    """A completed local run should persist provenance privately and archive raw payloads."""
    repository = get_repository()
    run_id = "0f7d5b51-2f8f-4ca7-9626-0de8b17d9b02"

    summary = run_pipeline(repository=repository, run_id=run_id)

    indicator_record = repository._records["indicator:ZA:NY.GDP.MKTP.KD.ZG"]
    country_record = repository._records["country:ZA"]
    overview_record = repository._records["global_overview:current"]

    assert summary["raw_archives_written"] == 7
    assert indicator_record["run_id"] == run_id
    assert (
        indicator_record["raw_backup_reference"]
        == f"local://runs/{run_id}/raw/NY.GDP.MKTP.KD.ZG.json"
    )
    assert (
        indicator_record["source_provenance"]["source_name"]
        == "world_analyst_local_fixture"
    )
    assert indicator_record["ai_provenance"]["provider"] == "deterministic-development"
    assert indicator_record["ai_provenance"]["model"] == "local-fixture-v1"
    assert indicator_record["ai_provenance"]["prompt_version"] == "step1.v1.0.0"
    assert indicator_record["ai_provenance"]["degraded"] is False
    assert indicator_record["ai_provenance"]["lineage"]["reused_from"] is None
    assert country_record["run_id"] == run_id
    assert (
        country_record["raw_backup_reference"]
        == f"local://runs/{run_id}/raw/manifest.json"
    )
    assert country_record["ai_provenance"]["prompt_version"] == "step2.v2.0.0"
    assert country_record["ai_provenance"]["degraded"] is False
    assert country_record["source_provenance"]["indicator_codes"] == sorted(
        [
            "BN.CAB.XOKA.GD.ZS",
            "FP.CPI.TOTL.ZG",
            "GC.DOD.TOTL.GD.ZS",
            "NY.GDP.MKTP.CD",
            "NY.GDP.MKTP.KD.ZG",
            "SL.UEM.TOTL.ZS",
        ]
    )
    assert overview_record["run_id"] == run_id
    assert (
        overview_record["raw_backup_reference"]
        == f"local://runs/{run_id}/raw/manifest.json"
    )
    assert overview_record["ai_provenance"]["prompt_version"] == "step3.v2.0.0"
    assert overview_record["ai_provenance"]["degraded"] is False
    assert overview_record["country_codes"] == ["ZA"]

    raw_archive_root = tmp_path / "raw-archives" / "runs" / run_id / "raw"
    assert raw_archive_root.joinpath("manifest.json").exists()
    assert raw_archive_root.joinpath("NY.GDP.MKTP.KD.ZG.json").exists()


def test_managed_pipeline_run_updates_durable_status_for_job_execution() -> None:
    """A standalone job-style run should keep durable status in sync with the records it writes."""
    repository = get_repository()
    run_id = "4be0b760-87f3-40e9-9ad2-f35318d872f1"

    summary = run_managed_pipeline(repository=repository, run_id=run_id)

    stored_status = repository.get_pipeline_status_record()
    assert summary["run_id"] == run_id
    assert stored_status["status"] == "complete"
    assert stored_status["run_id"] == run_id
    assert stored_status["completed_at"]
    assert any(
        step["name"] == "store" and step["status"] == "complete"
        for step in stored_status["steps"]
    )


def test_repository_backend_prefers_repository_mode_alias(monkeypatch) -> None:
    """Repository backend selection should prefer REPOSITORY_MODE over the legacy alias."""
    monkeypatch.setenv("WORLD_ANALYST_STORAGE_BACKEND", "local")
    monkeypatch.setenv("REPOSITORY_MODE", "firestore")

    assert get_repository_backend() == "firestore"


def test_panel_source_provenance_merges_the_full_source_window() -> None:
    """Panel provenance should expose one merged source window across indicators."""

    provenance = _build_panel_source_provenance(
        country_syntheses={
            "BR": {"summary": "placeholder"},
            "ZA": {"summary": "placeholder"},
        },
        source_provenance_by_indicator={
            "GDP": {
                "source_name": "world_bank_indicators_api",
                "source_date_range": "2010:2024",
                "source_last_updated": "2026-04-10",
                "source_id": "2",
            },
            "CPI": {
                "source_name": "world_bank_indicators_api",
                "source_date_range": "2012:2023",
                "source_last_updated": "2026-04-12",
                "source_id": "2",
            },
        },
    )

    assert provenance["source_date_range"] == "2010:2024"
    assert provenance["source_last_updated"] == "2026-04-12"


def test_firestore_mode_requires_gcs_raw_archive_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Firestore mode should fail fast when raw archive storage is not configured."""
    monkeypatch.setenv("REPOSITORY_MODE", "firestore")
    monkeypatch.delenv("WORLD_ANALYST_RAW_ARCHIVE_BUCKET", raising=False)

    with pytest.raises(
        ValueError,
        match=r"REPOSITORY_MODE=firestore requires WORLD_ANALYST_RAW_ARCHIVE_BUCKET",
    ):
        get_raw_archive_store()


def test_local_mode_ignores_gcs_archive_env_and_uses_local_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local repository mode should keep raw archives on the filesystem."""
    monkeypatch.setenv("REPOSITORY_MODE", "local")
    monkeypatch.setenv("WORLD_ANALYST_RAW_ARCHIVE_BUCKET", "world-analyst-raw")

    assert isinstance(get_raw_archive_store(), LocalRawArchiveStore)


def test_firestore_mode_requires_project_id_for_gcs_raw_archive_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Firestore mode should require a project identifier before GCS archiving is enabled."""
    monkeypatch.setenv("REPOSITORY_MODE", "firestore")
    monkeypatch.setenv("WORLD_ANALYST_RAW_ARCHIVE_BUCKET", "world-analyst-raw")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    with pytest.raises(
        ValueError,
        match=r"WORLD_ANALYST_RAW_ARCHIVE_BUCKET requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID",
    ):
        get_raw_archive_store()
