"""Business tests for the local first-slice pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.main import run_pipeline
from pipeline.storage import LocalRawArchiveStore, get_raw_archive_store
from shared.repository import get_repository, get_repository_backend


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


def test_local_pipeline_persists_private_provenance_and_raw_archives(tmp_path: Path) -> None:
    """A completed local run should persist provenance privately and archive raw payloads."""
    repository = get_repository()
    run_id = "0f7d5b51-2f8f-4ca7-9626-0de8b17d9b02"

    summary = run_pipeline(repository=repository, run_id=run_id)

    indicator_record = repository._records["indicator:ZA:NY.GDP.MKTP.KD.ZG"]
    country_record = repository._records["country:ZA"]

    assert summary["raw_archives_written"] == 7
    assert indicator_record["run_id"] == run_id
    assert indicator_record["raw_backup_reference"] == f"local://runs/{run_id}/raw/NY.GDP.MKTP.KD.ZG.json"
    assert indicator_record["source_provenance"]["source_name"] == "world_analyst_local_fixture"
    assert indicator_record["ai_provenance"] == {
        "provider": "deterministic-development",
        "model": "local-fixture-v1",
    }
    assert country_record["run_id"] == run_id
    assert country_record["raw_backup_reference"] == f"local://runs/{run_id}/raw/manifest.json"
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

    raw_archive_root = tmp_path / "raw-archives" / "runs" / run_id / "raw"
    assert raw_archive_root.joinpath("manifest.json").exists()
    assert raw_archive_root.joinpath("NY.GDP.MKTP.KD.ZG.json").exists()


def test_repository_backend_prefers_repository_mode_alias(monkeypatch) -> None:
    """Repository backend selection should prefer REPOSITORY_MODE over the legacy alias."""
    monkeypatch.setenv("WORLD_ANALYST_STORAGE_BACKEND", "local")
    monkeypatch.setenv("REPOSITORY_MODE", "firestore")

    assert get_repository_backend() == "firestore"


def test_firestore_mode_requires_gcs_raw_archive_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
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

