"""Business and contract tests for the Firestore-backed repository adapter."""

from __future__ import annotations

import copy

import pytest

import shared.firestore_repository as firestore_repository_module
from shared.firestore_repository import FirestoreInsightsRepository
from shared.repository import get_repository, get_repository_backend, reset_repository_cache


class FakeDocumentSnapshot:
    """Minimal Firestore snapshot used to test repository behavior."""

    def __init__(self, store: dict[str, dict], document_id: str) -> None:
        self._store = store
        self._document_id = document_id
        self.reference = FakeDocumentReference(store, document_id)

    @property
    def exists(self) -> bool:
        return self._document_id in self._store

    @property
    def id(self) -> str:
        """Mirror Firestore snapshot.id for adapter parity."""
        return self._document_id

    def to_dict(self) -> dict:
        return copy.deepcopy(self._store[self._document_id])


class FakeDocumentReference:
    """Minimal Firestore document reference used by the fake client."""

    def __init__(self, store: dict[str, dict], document_id: str) -> None:
        self._store = store
        self._document_id = document_id

    def set(self, data: dict, merge: bool = False) -> None:
        if merge and self._document_id in self._store:
            self._store[self._document_id] = {**self._store[self._document_id], **copy.deepcopy(data)}
            return
        self._store[self._document_id] = copy.deepcopy(data)

    def get(self) -> FakeDocumentSnapshot:
        return FakeDocumentSnapshot(self._store, self._document_id)

    def delete(self) -> None:
        self._store.pop(self._document_id, None)


class FakeBatch:
    """Minimal Firestore batch delete implementation."""

    def __init__(self) -> None:
        self._references: list[FakeDocumentReference] = []

    def delete(self, reference: FakeDocumentReference) -> None:
        self._references.append(reference)

    def commit(self) -> None:
        for reference in self._references:
            reference.delete()


class FakeCollection:
    """Minimal Firestore collection interface used by the adapter tests."""

    def __init__(self, store: dict[str, dict]) -> None:
        self._store = store

    def document(self, document_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._store, document_id)

    def stream(self) -> list[FakeDocumentSnapshot]:
        return [FakeDocumentSnapshot(self._store, document_id) for document_id in list(self._store.keys())]


class FakeFirestoreClient:
    """Minimal Firestore client for contract tests."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def collection(self, _name: str) -> FakeCollection:
        return FakeCollection(self.store)

    def batch(self) -> FakeBatch:
        return FakeBatch()


def test_firestore_repository_persists_status_and_country_detail() -> None:
    """The Firestore adapter should serve the same payload shapes as local mode."""
    client = FakeFirestoreClient()
    repository = FirestoreInsightsRepository(project_id="test-project", client=client)

    repository.reset()
    repository.upsert_pipeline_status(
        {
            "status": "complete",
            "run_id": "f9710a31-8f35-43d0-b75e-78054470ab80",
            "started_at": "2026-04-09T12:00:00+00:00",
            "completed_at": "2026-04-09T12:00:05+00:00",
            "steps": [
                {
                    "name": "store",
                    "status": "complete",
                    "duration_ms": 42,
                    "started_at": "2026-04-09T12:00:04+00:00",
                    "completed_at": "2026-04-09T12:00:05+00:00",
                }
            ],
        }
    )
    repository.upsert_indicator(
        {
            "indicator_code": "NY.GDP.MKTP.KD.ZG",
            "indicator_name": "GDP growth (annual %)",
            "country_code": "za",
            "latest_value": 0.6,
            "previous_value": 1.2,
            "percent_change": -50.0,
            "is_anomaly": True,
            "ai_analysis": "Growth has slowed materially.",
            "data_year": 2024,
            "updated_at": "2026-04-09T12:00:05+00:00",
            "run_id": "f9710a31-8f35-43d0-b75e-78054470ab80",
            "raw_backup_reference": "gs://world-analyst-raw/runs/f9710a31-8f35-43d0-b75e-78054470ab80/raw/NY.GDP.MKTP.KD.ZG.json",
            "source_provenance": {
                "source_name": "world_bank_indicators_api",
                "source_date_range": "2010:2024",
            },
            "ai_provenance": {"provider": "google-genai", "model": "gemma-4-31b-it"},
        }
    )
    repository.upsert_country(
        {
            "code": "za",
            "name": "South Africa",
            "region": "Sub-Saharan Africa",
            "income_level": "Upper middle income",
            "macro_synthesis": "The macro picture remains fragile.",
            "risk_flags": ["Growth is weak", "Inflation is sticky"],
            "outlook": "cautious",
            "updated_at": "2026-04-09T12:00:05+00:00",
            "run_id": "f9710a31-8f35-43d0-b75e-78054470ab80",
            "raw_backup_reference": "gs://world-analyst-raw/runs/f9710a31-8f35-43d0-b75e-78054470ab80/raw/manifest.json",
            "source_provenance": {
                "source_name": "world_bank_indicators_api",
                "source_date_range": "2010:2024",
                "indicator_codes": ["NY.GDP.MKTP.KD.ZG"],
            },
            "ai_provenance": {"provider": "google-genai", "model": "gemma-4-31b-it"},
        }
    )

    status = repository.get_pipeline_status()
    detail = repository.get_country_detail("ZA")

    assert status["status"] == "complete"
    assert "run_id" not in status
    assert detail is not None
    assert detail["code"] == "ZA"
    assert detail["macro_synthesis"] == "The macro picture remains fragile."
    assert len(detail["indicators"]) == 1
    assert detail["indicators"][0]["country_code"] == "ZA"
    assert "run_id" not in detail
    assert "raw_backup_reference" not in detail
    assert "source_provenance" not in detail["indicators"][0]
    assert client.store["indicator:ZA:NY.GDP.MKTP.KD.ZG"]["run_id"] == "f9710a31-8f35-43d0-b75e-78054470ab80"
    assert client.store["country:ZA"]["raw_backup_reference"].endswith("/manifest.json")


def test_firestore_repository_reset_restores_idle_status() -> None:
    """Reset should clear persisted records while keeping the status contract valid."""
    client = FakeFirestoreClient()
    repository = FirestoreInsightsRepository(project_id="test-project", client=client)

    repository.upsert_country(
        {
            "code": "ZA",
            "name": "South Africa",
            "region": "Sub-Saharan Africa",
            "income_level": "Upper middle income",
            "macro_synthesis": "Temporary",
            "risk_flags": ["Temporary"],
            "outlook": "cautious",
            "updated_at": "2026-04-09T12:00:05+00:00",
        }
    )

    repository.reset()

    assert repository.get_country_detail("ZA") is None
    assert repository.get_pipeline_status()["status"] == "idle"


def test_firestore_repository_rejects_missing_required_fields() -> None:
    """Repository writes should fail with a clear contract error when fields are missing."""
    client = FakeFirestoreClient()
    repository = FirestoreInsightsRepository(project_id="test-project", client=client)

    with pytest.raises(ValueError, match=r"indicator record missing required field\(s\): country_code"):
        repository.upsert_indicator(
            {
                "indicator_code": "NY.GDP.MKTP.KD.ZG",
                "indicator_name": "GDP growth (annual %)",
                "data_year": 2024,
            }
        )


def test_repository_backend_alias_remains_backward_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy storage env var should still work when REPOSITORY_MODE is unset."""
    monkeypatch.delenv("REPOSITORY_MODE", raising=False)
    monkeypatch.setenv("WORLD_ANALYST_STORAGE_BACKEND", "local")
    reset_repository_cache()

    assert get_repository_backend() == "local"


def test_repository_backend_defaults_to_local_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository selection should stay deterministic when no backend env vars are set."""
    monkeypatch.delenv("REPOSITORY_MODE", raising=False)
    monkeypatch.delenv("WORLD_ANALYST_STORAGE_BACKEND", raising=False)
    reset_repository_cache()

    assert get_repository_backend() == "local"


def test_get_repository_requires_project_id_in_firestore_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Firestore mode should fail fast until a Cloud Run project is configured."""
    monkeypatch.setenv("REPOSITORY_MODE", "firestore")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    reset_repository_cache()

    with pytest.raises(
        ValueError,
        match=r"REPOSITORY_MODE=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID",
    ):
        get_repository()


def test_get_repository_uses_explicit_firestore_collection_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Firestore mode should honor the configured collection name when cloud env vars are set."""
    captured: dict[str, str | None] = {}

    class StubFirestoreRepository:
        """Minimal stand-in used to capture Firestore constructor arguments."""

        def __init__(
            self,
            project_id: str,
            collection_name: str = "insights",
            client=None,
        ) -> None:
            del client
            captured["project_id"] = project_id
            captured["collection_name"] = collection_name

    monkeypatch.setenv("REPOSITORY_MODE", "firestore")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "world-analyst-demo")
    monkeypatch.setenv("WORLD_ANALYST_FIRESTORE_COLLECTION", "world-analyst-prod")
    monkeypatch.setattr(
        firestore_repository_module,
        "FirestoreInsightsRepository",
        StubFirestoreRepository,
    )
    reset_repository_cache()

    repository = get_repository()

    assert isinstance(repository, StubFirestoreRepository)
    assert captured == {
        "project_id": "world-analyst-demo",
        "collection_name": "world-analyst-prod",
    }


def test_firestore_status_write_clears_stale_failure_fields() -> None:
    """A successful status rewrite should remove stale failure detail in Firestore mode."""
    client = FakeFirestoreClient()
    repository = FirestoreInsightsRepository(project_id="test-project", client=client)

    repository.upsert_pipeline_status(
        {
            "status": "failed",
            "run_id": "f9710a31-8f35-43d0-b75e-78054470ab80",
            "started_at": "2026-04-09T12:00:00+00:00",
            "completed_at": "2026-04-09T12:00:05+00:00",
            "steps": [{"name": "synthesise", "status": "failed"}],
            "error": "Synthetic failure",
            "failure_summary": {
                "run_id": "f9710a31-8f35-43d0-b75e-78054470ab80",
                "step": "synthesise",
                "message": "Synthetic failure",
            },
        }
    )

    repository.upsert_pipeline_status(
        {
            "status": "complete",
            "run_id": "3b8e29c7-0b6b-4cdd-a36e-453403ce3c26",
            "started_at": "2026-04-09T12:10:00+00:00",
            "completed_at": "2026-04-09T12:10:05+00:00",
            "steps": [{"name": "store", "status": "complete"}],
        }
    )

    stored_status = repository.get_pipeline_status_record()

    assert stored_status["status"] == "complete"
    assert "error" not in stored_status
    assert "failure_summary" not in stored_status


def test_firestore_repository_can_load_private_stored_record_for_ai_reuse() -> None:
    """The Firestore adapter should return the full stored record with document id."""
    client = FakeFirestoreClient()
    repository = FirestoreInsightsRepository(project_id="test-project", client=client)

    repository.upsert_indicator(
        {
            "indicator_code": "NY.GDP.MKTP.KD.ZG",
            "indicator_name": "GDP growth (annual %)",
            "country_code": "za",
            "latest_value": 0.6,
            "data_year": 2024,
            "ai_analysis": "Growth has slowed materially.",
            "ai_structured_output": {
                "trend": "declining",
                "narrative": "Growth has slowed materially.",
                "risk_level": "high",
                "confidence": "high",
            },
            "ai_provenance": {
                "provider": "google-genai",
                "model": "gemma-4-31b-it",
                "step_name": "indicator_analysis",
                "lineage": {"input_fingerprint": "abc123", "reused_from": None},
                "degraded": False,
            },
        }
    )

    stored_record = repository.get_stored_record(
        entity_type="indicator",
        key="ZA:NY.GDP.MKTP.KD.ZG",
    )

    assert stored_record is not None
    assert stored_record["document_id"] == "indicator:ZA:NY.GDP.MKTP.KD.ZG"
    assert stored_record["ai_structured_output"]["trend"] == "declining"
    assert stored_record["ai_provenance"]["lineage"]["input_fingerprint"] == "abc123"
