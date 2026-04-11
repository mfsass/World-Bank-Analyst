"""Shared repository contract and backend selection.

The API and pipeline both depend on the same mixed-document repository shape.
This module keeps that contract stable while allowing local and Firestore-backed
implementations to be selected by configuration.
"""

from __future__ import annotations

import copy
import logging
import os
from threading import Lock
from typing import Any, Protocol

PIPELINE_STEP_NAMES = ("fetch", "analyse", "synthesise", "store")
PIPELINE_STATUS_PUBLIC_FIELDS = ("status", "started_at", "completed_at", "steps", "error")
PIPELINE_STATUS_STEP_PUBLIC_FIELDS = ("name", "status", "duration_ms")
INDICATOR_PUBLIC_FIELDS = (
    "indicator_code",
    "indicator_name",
    "country_code",
    "latest_value",
    "previous_value",
    "percent_change",
    "is_anomaly",
    "ai_analysis",
    "data_year",
    "updated_at",
)
COUNTRY_PUBLIC_FIELDS = (
    "code",
    "name",
    "region",
    "income_level",
    "macro_synthesis",
    "risk_flags",
    "outlook",
    "updated_at",
)

_REPOSITORIES: dict[str, InsightsRepository] = {}
_REPOSITORY_LOCK = Lock()
logger = logging.getLogger(__name__)


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

    def get_pipeline_status_record(self) -> dict[str, Any]:
        """Return the full stored pipeline status for internal mutation."""

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


def project_public_record(record: dict[str, Any]) -> dict[str, Any]:
    """Project a stored mixed document back to the public API contract.

    Args:
        record: Stored mixed-document record.

    Returns:
        Public-facing payload with private provenance and status detail removed.
    """
    entity_type = record.get("entity_type")
    if entity_type == "indicator":
        return _project_fields(record, INDICATOR_PUBLIC_FIELDS)

    if entity_type == "country":
        return _project_fields(record, COUNTRY_PUBLIC_FIELDS)

    if entity_type == "pipeline_status":
        projected = _project_fields(record, PIPELINE_STATUS_PUBLIC_FIELDS)
        projected["steps"] = [
            _project_fields(step, PIPELINE_STATUS_STEP_PUBLIC_FIELDS)
            for step in record.get("steps", build_pipeline_steps())
        ]
        return projected

    public_record = copy.deepcopy(record)
    public_record.pop("entity_type", None)
    return public_record


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
        REPOSITORY_MODE: `local` or `firestore`. Defaults to `local`.
        WORLD_ANALYST_STORAGE_BACKEND: Backward-compatible alias for REPOSITORY_MODE.
        WORLD_ANALYST_FIRESTORE_COLLECTION: Optional collection name override.
        GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID: Project identifier for Firestore.

    Returns:
        Shared repository instance for the selected backend.
    """
    backend = get_repository_backend()
    if backend not in _REPOSITORIES:
        with _REPOSITORY_LOCK:
            if backend not in _REPOSITORIES:
                _REPOSITORIES[backend] = _build_repository(backend)
    return _REPOSITORIES[backend]


def get_repository_backend() -> str:
    """Resolve the configured repository backend.

    Returns:
        Normalized repository backend name.
    """
    backend = os.environ.get("REPOSITORY_MODE")
    if backend:
        return backend.lower()

    legacy_backend = os.environ.get("WORLD_ANALYST_STORAGE_BACKEND")
    if legacy_backend:
        logger.info(
            "Using WORLD_ANALYST_STORAGE_BACKEND as a backward-compatible alias for REPOSITORY_MODE"
        )
        return legacy_backend.lower()

    return "local"


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
                "REPOSITORY_MODE=firestore requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"
            )

        return FirestoreInsightsRepository(
            project_id=project_id,
            collection_name=os.environ.get("WORLD_ANALYST_FIRESTORE_COLLECTION", "insights"),
        )

    raise ValueError(f"Unsupported repository backend: {backend}")


def _project_fields(record: dict[str, Any], field_names: tuple[str, ...]) -> dict[str, Any]:
    """Copy a known subset of fields from a stored record.

    Args:
        record: Stored record.
        field_names: Public fields to copy when present.

    Returns:
        Copied subset of the stored record.
    """
    return {field_name: copy.deepcopy(record[field_name]) for field_name in field_names if field_name in record}