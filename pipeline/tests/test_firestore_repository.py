"""Business and contract tests for the Firestore-backed repository adapter."""

from __future__ import annotations

import copy

import pytest

from shared.firestore_repository import FirestoreInsightsRepository


class FakeDocumentSnapshot:
    """Minimal Firestore snapshot used to test repository behavior."""

    def __init__(self, store: dict[str, dict], document_id: str) -> None:
        self._store = store
        self._document_id = document_id
        self.reference = FakeDocumentReference(store, document_id)

    @property
    def exists(self) -> bool:
        return self._document_id in self._store

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
            "started_at": "2026-04-09T12:00:00+00:00",
            "completed_at": "2026-04-09T12:00:05+00:00",
            "steps": [{"name": "store", "status": "complete", "duration_ms": 42}],
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
        }
    )

    status = repository.get_pipeline_status()
    detail = repository.get_country_detail("ZA")

    assert status["status"] == "complete"
    assert detail is not None
    assert detail["code"] == "ZA"
    assert detail["macro_synthesis"] == "The macro picture remains fragile."
    assert len(detail["indicators"]) == 1
    assert detail["indicators"][0]["country_code"] == "ZA"


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