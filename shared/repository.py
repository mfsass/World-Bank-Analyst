"""Shared repository contract and backend selection.

The API and pipeline both depend on the same mixed-document repository shape.
This module keeps that contract stable while allowing local and Firestore-backed
implementations to be selected by configuration.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any, Protocol

PIPELINE_STEP_NAMES = ("fetch", "analyse", "synthesise", "store")

LOCAL_COUNTRY_CATALOG: dict[str, dict[str, str]] = {
    "ZA": {
        "code": "ZA",
        "name": "South Africa",
        "region": "Sub-Saharan Africa",
        "income_level": "Upper middle income",
    }
}

_REPOSITORIES: dict[str, InsightsRepository] = {}
_REPOSITORY_LOCK = Lock()


class InsightsRepository(Protocol):
    """Contract shared by the API and the pipeline.

    Both the local slice and the durable Firestore path must expose the same
    read and write methods so the frontend contract stays unchanged.
    """

    def reset(self) -> None:
        """Reset repository state for tests or local development."""

    def list_countries(self) -> list[dict[str, Any]]:
        """Return monitored-country metadata."""

    def get_country_metadata(self, country_code: str) -> dict[str, Any] | None:
        """Return metadata for one monitored country."""

    def upsert_indicator(self, record: dict[str, Any]) -> None:
        """Store one indicator insight record."""

    def upsert_country(self, record: dict[str, Any]) -> None:
        """Store one materialised country briefing."""

    def upsert_pipeline_status(self, record: dict[str, Any]) -> None:
        """Store the latest pipeline status payload."""

    def list_indicator_insights(self, country_code: str | None = None) -> list[dict[str, Any]]:
        """Return indicator insights, optionally filtered by country."""

    def get_country_detail(self, country_code: str) -> dict[str, Any] | None:
        """Return one country detail payload if materialised."""

    def get_pipeline_status(self) -> dict[str, Any]:
        """Return the latest pipeline status payload."""


def build_pipeline_steps() -> list[dict[str, Any]]:
    """Create the default step list for pipeline status payloads.

    Returns:
        List of pending step dictionaries.
    """
    return [{"name": name, "status": "pending"} for name in PIPELINE_STEP_NAMES]


def default_pipeline_status() -> dict[str, Any]:
    """Return the default idle pipeline status payload.

    Returns:
        Pipeline status dictionary matching the API contract.
    """
    return {
        "status": "idle",
        "steps": build_pipeline_steps(),
    }


def require_fields(record: dict[str, Any], required_fields: tuple[str, ...], record_type: str) -> None:
    """Validate that a record contains the fields required by the repository.

    Args:
        record: Candidate record payload.
        required_fields: Field names that must be present.
        record_type: Logical record name used in error messages.

    Raises:
        ValueError: If one or more required fields are missing.
    """
    missing_fields = [field for field in required_fields if field not in record]
    if missing_fields:
        raise ValueError(
            f"{record_type} record missing required field(s): {', '.join(sorted(missing_fields))}"
        )


def get_repository() -> InsightsRepository:
    """Return the configured repository backend.

    Environment:
        WORLD_ANALYST_STORAGE_BACKEND: `local` or `firestore`. Defaults to `local`.
        WORLD_ANALYST_FIRESTORE_COLLECTION: Optional collection name override.
        GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID: Project identifier for Firestore.

    Returns:
        Shared repository instance for the selected backend.
    """
    backend = os.environ.get("WORLD_ANALYST_STORAGE_BACKEND", "local").lower()
    if backend not in _REPOSITORIES:
        with _REPOSITORY_LOCK:
            if backend not in _REPOSITORIES:
                _REPOSITORIES[backend] = _build_repository(backend)
    return _REPOSITORIES[backend]


def reset_repository_cache() -> None:
    """Clear cached repository singletons.

    This is mainly useful for tests that need to switch backend selection.
    """
    with _REPOSITORY_LOCK:
        _REPOSITORIES.clear()


def _build_repository(backend: str) -> InsightsRepository:
    """Instantiate a repository backend.

    Args:
        backend: Repository backend name.

    Returns:
        Repository implementation.

    Raises:
        ValueError: If configuration is incomplete or the backend is unknown.
    """
    if backend == "local":
        from shared.local_repository import InMemoryInsightsRepository

        return InMemoryInsightsRepository()

    if backend == "firestore":
        from shared.firestore_repository import FirestoreInsightsRepository

        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")
        if not project_id:
            raise ValueError(
                "WORLD_ANALYST_STORAGE_BACKEND=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"
            )

        return FirestoreInsightsRepository(
            project_id=project_id,
            collection_name=os.environ.get("WORLD_ANALYST_FIRESTORE_COLLECTION", "insights"),
        )

    raise ValueError(f"Unsupported repository backend: {backend}")