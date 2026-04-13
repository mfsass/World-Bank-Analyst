"""Storage operations for repository-backed insights and raw-data archival.

Mixed-document insight writes now flow through one storage boundary that can
archive raw payloads locally for deterministic tests or to GCS in deployed
environments before persisting processed records.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.local_data import (  # noqa: E402
    LOCAL_TARGET_COUNTRY,
    LOCAL_TARGET_COUNTRY_INCOME_LEVEL,
    LOCAL_TARGET_COUNTRY_NAME,
    LOCAL_TARGET_COUNTRY_REGION,
)
from shared.repository import InsightsRepository, get_repository, get_repository_backend  # noqa: E402

logger = logging.getLogger(__name__)
DEFAULT_LOCAL_RAW_ARCHIVE_ROOT = REPO_ROOT / ".world_analyst" / "raw_archives"
RAW_ARCHIVE_MANIFEST_KEY = "manifest"


class RawArchiveStore(Protocol):
    """Boundary for archiving raw payloads.

    Local development and tests use a filesystem-backed implementation while the
    deployed path uses GCS with the same run-scoped relative paths.
    """

    def archive_json(self, relative_path: str, payload: Any) -> str:
        """Persist a JSON payload and return a stable reference string."""


@dataclass(frozen=True)
class RawArchiveResult:
    """References created for one run-scoped raw archive."""

    scope_references: dict[str, str]
    manifest_reference: str


class LocalRawArchiveStore:
    """Persist raw payloads to the local filesystem for deterministic tests."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialise the local raw archive store.

        Args:
            base_dir: Optional filesystem root for local archives.
        """
        configured_root = os.environ.get("WORLD_ANALYST_LOCAL_RAW_ARCHIVE_DIR")
        self._base_dir = (
            Path(configured_root)
            if configured_root
            else (base_dir or DEFAULT_LOCAL_RAW_ARCHIVE_ROOT)
        )

    def archive_json(self, relative_path: str, payload: Any) -> str:
        """Persist one JSON payload under a run-scoped relative path.

        Args:
            relative_path: Run-scoped archive path.
            payload: JSON-serialisable payload.

        Returns:
            Stable local archive reference.
        """
        normalized_path = relative_path.replace("\\", "/")
        file_path = self._base_dir / Path(normalized_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        return f"local://{normalized_path}"


class GCSRawArchiveStore:
    """Persist raw payloads to Google Cloud Storage."""

    def __init__(self, project_id: str, bucket_name: str) -> None:
        """Initialise the GCS-backed raw archive store.

        Args:
            project_id: GCP project identifier.
            bucket_name: GCS bucket used for raw archives.
        """
        from google.cloud import storage

        self._bucket_name = bucket_name
        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket_name)

    def archive_json(self, relative_path: str, payload: Any) -> str:
        """Persist one JSON payload to GCS.

        Args:
            relative_path: Run-scoped archive path.
            payload: JSON-serialisable payload.

        Returns:
            GCS archive reference.
        """
        normalized_path = relative_path.replace("\\", "/")
        blob = self._bucket.blob(normalized_path)
        blob.upload_from_string(
            json.dumps(payload, indent=2, sort_keys=True),
            content_type="application/json",
        )
        return f"gs://{self._bucket_name}/{normalized_path}"


def store_slice(
    insights: list[dict[str, Any]],
    country_syntheses: dict[str, dict[str, Any]],
    global_overview: dict[str, Any],
    raw_data_points: list[dict[str, Any]],
    run_id: str,
    raw_fetch_payloads: dict[str, Any] | None = None,
    ai_provenance: dict[str, Any] | None = None,
    repository: InsightsRepository | None = None,
    raw_archive_store: RawArchiveStore | None = None,
) -> dict[str, int]:
    """Persist the current slice into the configured repository backend.

    Args:
        insights: Enriched per-indicator insight payloads.
        country_syntheses: Country synthesis payloads keyed by country code.
        global_overview: Cross-country overview synthesis payload.
        raw_data_points: Raw fetched payloads for the current run.
        raw_fetch_payloads: Optional live request-response envelopes keyed by indicator code.
        run_id: UUID v4 run identifier for durable provenance.
        ai_provenance: Minimal AI provenance when narrative generation is available.
        repository: Shared repository instance.
        raw_archive_store: Optional raw archive implementation override.

    Returns:
        Counts of indicator, country, and overview records written.
    """
    repo = repository or get_repository()
    updated_at = datetime.now(timezone.utc).isoformat()
    grouped_raw_payloads = _group_raw_payloads_by_indicator(raw_data_points)
    archivable_raw_payloads: dict[str, Any] = {
        indicator_code: copy.deepcopy(payload)
        for indicator_code, payload in grouped_raw_payloads.items()
    }
    if raw_fetch_payloads:
        archivable_raw_payloads.update(
            {
                indicator_code: copy.deepcopy(payload)
                for indicator_code, payload in raw_fetch_payloads.items()
            }
        )

    archive_result = archive_raw_payloads(
        archivable_raw_payloads, run_id, raw_archive_store
    )
    source_provenance_by_indicator = {
        indicator_code: _build_source_provenance(payload)
        for indicator_code, payload in archivable_raw_payloads.items()
    }

    indicator_writes = 0
    for insight in insights:
        indicator_record = {
            "indicator_code": insight["indicator_code"],
            "indicator_name": insight["indicator_name"],
            "country_code": insight["country_code"],
            "latest_value": insight["latest_value"],
            "previous_value": insight.get("previous_value"),
            "percent_change": insight.get("percent_change"),
            "change_value": insight.get("change_value"),
            "change_basis": insight.get("change_basis"),
            "signal_polarity": insight.get("signal_polarity"),
            "is_anomaly": bool(insight.get("is_anomaly", False)),
            "anomaly_basis": insight.get("anomaly_basis"),
            "ai_analysis": insight.get("ai_analysis", ""),
            "data_year": insight["data_year"],
            "time_series": copy.deepcopy(insight.get("time_series", [])),
            "updated_at": updated_at,
            "run_id": run_id,
            "raw_backup_reference": archive_result.scope_references.get(
                insight["indicator_code"],
                archive_result.manifest_reference,
            ),
        }
        source_provenance = source_provenance_by_indicator.get(
            insight["indicator_code"]
        )
        if source_provenance:
            indicator_record["source_provenance"] = source_provenance
        record_ai_provenance = _resolve_record_ai_provenance(insight, ai_provenance)
        if record_ai_provenance and insight.get("ai_analysis"):
            indicator_record["ai_provenance"] = record_ai_provenance
        structured_ai_output = _build_indicator_structured_output(insight)
        if structured_ai_output:
            indicator_record["ai_structured_output"] = structured_ai_output

        repo.upsert_indicator(indicator_record)
        indicator_writes += 1

    country_writes = 0
    for country_code, synthesis in country_syntheses.items():
        country_metadata = _resolve_country_metadata(
            repo=repo, country_code=country_code
        )

        country_record = {
            **country_metadata,
            "macro_synthesis": synthesis["summary"],
            "risk_flags": synthesis["risk_flags"],
            "outlook": synthesis["outlook"],
            "regime_label": synthesis.get("regime_label"),
            "updated_at": updated_at,
            "run_id": run_id,
            "raw_backup_reference": archive_result.manifest_reference,
        }
        country_source_provenance = _build_country_source_provenance(
            country_code=country_code,
            insights=insights,
            source_provenance_by_indicator=source_provenance_by_indicator,
        )
        if country_source_provenance:
            country_record["source_provenance"] = country_source_provenance
            country_record["source_date_range"] = country_source_provenance.get(
                "source_date_range"
            )
        record_ai_provenance = _resolve_record_ai_provenance(synthesis, ai_provenance)
        if record_ai_provenance and synthesis.get("summary"):
            country_record["ai_provenance"] = record_ai_provenance
        structured_ai_output = _build_country_structured_output(synthesis)
        if structured_ai_output:
            country_record["ai_structured_output"] = structured_ai_output

        repo.upsert_country(country_record)
        country_writes += 1

    overview_record = {
        "summary": global_overview["summary"],
        "risk_flags": copy.deepcopy(global_overview["risk_flags"]),
        "outlook": global_overview["outlook"],
        "country_count": len(country_syntheses),
        "country_codes": sorted(country_syntheses.keys()),
        "updated_at": updated_at,
        "run_id": run_id,
        "raw_backup_reference": archive_result.manifest_reference,
    }
    overview_source_provenance = _build_panel_source_provenance(
        country_syntheses=country_syntheses,
        source_provenance_by_indicator=source_provenance_by_indicator,
    )
    if overview_source_provenance:
        overview_record["source_provenance"] = overview_source_provenance
        overview_record["source_date_range"] = overview_source_provenance.get(
            "source_date_range"
        )
    record_ai_provenance = _resolve_record_ai_provenance(global_overview, ai_provenance)
    if record_ai_provenance and global_overview.get("summary"):
        overview_record["ai_provenance"] = record_ai_provenance
    structured_ai_output = _build_global_overview_structured_output(global_overview)
    if structured_ai_output:
        overview_record["ai_structured_output"] = structured_ai_output

    repo.upsert_global_overview(overview_record)

    logger.info(
        "Stored %d indicator insights, %d country syntheses, one global overview, and %d raw payload archives for run %s",
        indicator_writes,
        country_writes,
        len(archive_result.scope_references) + 1,
        run_id,
    )
    return {
        "indicator_records": indicator_writes,
        "country_records": country_writes,
        "global_overview_records": 1,
        "raw_archives_written": len(archive_result.scope_references) + 1,
    }


def store_local_slice(
    insights: list[dict[str, Any]],
    country_syntheses: dict[str, dict[str, Any]],
    global_overview: dict[str, Any],
    raw_data_points: list[dict[str, Any]],
    run_id: str,
    raw_fetch_payloads: dict[str, Any] | None = None,
    ai_provenance: dict[str, Any] | None = None,
    repository: InsightsRepository | None = None,
    raw_archive_store: RawArchiveStore | None = None,
) -> dict[str, int]:
    """Backward-compatible wrapper for the original local-slice storage call.

    Args:
        insights: Enriched per-indicator insight payloads.
        country_syntheses: Country synthesis payloads keyed by country code.
        global_overview: Cross-country overview synthesis payload.
        raw_data_points: Raw fetched payloads for the current run.
        raw_fetch_payloads: Optional live request-response envelopes keyed by indicator code.
        run_id: UUID v4 run identifier for durable provenance.
        ai_provenance: Minimal AI provenance when available.
        repository: Shared repository instance.
        raw_archive_store: Optional raw archive implementation override.

    Returns:
        Counts of indicator, country, and overview records written.
    """
    return store_slice(
        insights=insights,
        country_syntheses=country_syntheses,
        global_overview=global_overview,
        raw_data_points=raw_data_points,
        raw_fetch_payloads=raw_fetch_payloads,
        run_id=run_id,
        ai_provenance=ai_provenance,
        repository=repository,
        raw_archive_store=raw_archive_store,
    )


def store_insights(insights: list[dict[str, Any]], project_id: str) -> int:
    """Store processed indicator insights in Firestore.

    Each insight is stored as a document in the 'insights' collection,
    keyed by country_code + indicator_code for idempotent updates.

    Args:
        insights: List of processed insight dicts.
        project_id: GCP project ID for Firestore client.

    Returns:
        Number of documents written.
    """
    from google.cloud import firestore

    db = firestore.Client(project=project_id)
    batch = db.batch()
    count = 0

    for insight in insights:
        doc_id = f"{insight['country_code']}_{insight['indicator_code']}"
        doc_ref = db.collection("insights").document(doc_id)
        insight["updated_at"] = datetime.now(timezone.utc).isoformat()
        batch.set(doc_ref, insight, merge=True)
        count += 1

    batch.commit()
    logger.info("Stored %d insights in Firestore", count)
    return count


def archive_raw_data(
    data: list[dict[str, Any]], project_id: str, bucket_name: str
) -> str:
    """Backward-compatible helper for archiving one raw payload to GCS.

    Args:
        data: Raw API response data.
        project_id: GCP project ID.
        bucket_name: GCS bucket name for raw data archival.

    Returns:
        Archive reference string.
    """
    relative_path = (
        f"runs/manual-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}/"
        "raw/raw-data.json"
    )
    return GCSRawArchiveStore(
        project_id=project_id, bucket_name=bucket_name
    ).archive_json(relative_path, data)


def archive_raw_payloads(
    grouped_raw_payloads: dict[str, Any],
    run_id: str,
    raw_archive_store: RawArchiveStore | None = None,
) -> RawArchiveResult:
    """Archive run-scoped raw payloads before processed persistence.

    Args:
        grouped_raw_payloads: Raw payloads keyed by fetch scope.
        run_id: UUID v4 run identifier.
        raw_archive_store: Optional raw archive implementation override.

    Returns:
        Archive references for each scope and the run manifest.
    """
    archive_store = raw_archive_store or get_raw_archive_store()
    scope_references: dict[str, str] = {}
    for scope_name, payload in grouped_raw_payloads.items():
        scope_references[scope_name] = archive_store.archive_json(
            _raw_archive_relative_path(run_id, scope_name),
            payload,
        )

    manifest_payload = {
        "run_id": run_id,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "scopes": scope_references,
    }
    manifest_reference = archive_store.archive_json(
        _raw_archive_relative_path(run_id, RAW_ARCHIVE_MANIFEST_KEY),
        manifest_payload,
    )
    return RawArchiveResult(
        scope_references=scope_references,
        manifest_reference=manifest_reference,
    )


def get_raw_archive_store() -> RawArchiveStore:
    """Select the configured raw archive backend.

    Returns:
        Raw archive implementation.

    Raises:
        ValueError: If Firestore mode is enabled without a raw archive bucket, or if a
            GCS bucket is configured without a project identifier.
    """
    if get_repository_backend() != "firestore":
        return LocalRawArchiveStore()

    bucket_name = os.environ.get("WORLD_ANALYST_RAW_ARCHIVE_BUCKET")
    if not bucket_name:
        raise ValueError(
            "REPOSITORY_MODE=firestore requires WORLD_ANALYST_RAW_ARCHIVE_BUCKET "
            "so durable records point at GCS raw archives"
        )

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
        "GCP_PROJECT_ID"
    )
    if not project_id:
        raise ValueError(
            "WORLD_ANALYST_RAW_ARCHIVE_BUCKET requires GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID"
        )
    return GCSRawArchiveStore(project_id=project_id, bucket_name=bucket_name)


def _build_country_source_provenance(
    country_code: str,
    insights: list[dict[str, Any]],
    source_provenance_by_indicator: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a country-level source provenance envelope.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.
        insights: Stored indicator insights for the run.
        source_provenance_by_indicator: Source provenance keyed by indicator code.

    Returns:
        Country-level source provenance when available.
    """
    indicator_codes = sorted(
        {
            insight["indicator_code"]
            for insight in insights
            if insight.get("country_code", "").upper() == country_code.upper()
        }
    )
    if not indicator_codes:
        return {}

    exemplar = next(
        (
            source_provenance_by_indicator[indicator_code]
            for indicator_code in indicator_codes
            if source_provenance_by_indicator.get(indicator_code)
        ),
        {},
    )
    country_provenance = {key: copy.deepcopy(value) for key, value in exemplar.items()}
    country_provenance["indicator_codes"] = indicator_codes
    return country_provenance


def _build_panel_source_provenance(
    *,
    country_syntheses: dict[str, dict[str, Any]],
    source_provenance_by_indicator: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build source provenance for the cross-country overview record."""

    source_names = {
        provenance.get("source_name")
        for provenance in source_provenance_by_indicator.values()
        if provenance.get("source_name")
    }
    source_date_ranges = {
        provenance.get("source_date_range")
        for provenance in source_provenance_by_indicator.values()
        if provenance.get("source_date_range")
    }
    source_last_updated = {
        provenance.get("source_last_updated")
        for provenance in source_provenance_by_indicator.values()
        if provenance.get("source_last_updated")
    }
    source_ids = {
        provenance.get("source_id")
        for provenance in source_provenance_by_indicator.values()
        if provenance.get("source_id")
    }
    if not source_names:
        return {}

    return {
        "source_name": sorted(source_names)[0],
        "source_date_range": _merge_source_date_ranges(source_date_ranges),
        "source_last_updated": max(source_last_updated)
        if source_last_updated
        else None,
        "source_id": sorted(source_ids)[0] if source_ids else None,
        "country_codes": sorted(country_syntheses.keys()),
    }


def _merge_source_date_ranges(source_date_ranges: set[str]) -> str | None:
    """Merge one or more YYYY:YYYY source windows into one panel-wide range."""

    if not source_date_ranges:
        return None

    parsed_ranges: list[tuple[int, int]] = []
    for value in source_date_ranges:
        try:
            start_text, end_text = str(value).split(":", maxsplit=1)
            parsed_ranges.append((int(start_text), int(end_text)))
        except (TypeError, ValueError):
            continue

    if not parsed_ranges:
        return sorted(source_date_ranges)[0]

    start_year = min(start_year for start_year, _ in parsed_ranges)
    end_year = max(end_year for _, end_year in parsed_ranges)
    return f"{start_year}:{end_year}"


def _resolve_record_ai_provenance(
    record: dict[str, Any],
    default_ai_provenance: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return record-specific AI provenance when available, else the shared fallback."""

    record_ai_provenance = record.get("ai_provenance")
    if isinstance(record_ai_provenance, dict) and record_ai_provenance:
        return copy.deepcopy(record_ai_provenance)
    if default_ai_provenance:
        return copy.deepcopy(default_ai_provenance)
    return None


def _build_indicator_structured_output(
    insight: dict[str, Any],
) -> dict[str, Any] | None:
    """Persist the private Step 1 result fields needed for exact-match reuse.

    Args:
        insight: Enriched indicator insight prepared for storage.

    Returns:
        Private structured AI payload, else None when the required fields are absent.
    """
    required_fields = ("trend", "ai_analysis", "risk_level", "confidence")
    if any(field_name not in insight for field_name in required_fields):
        return None

    return {
        "trend": insight["trend"],
        "narrative": insight["ai_analysis"],
        "risk_level": insight["risk_level"],
        "confidence": insight["confidence"],
    }


def _build_country_structured_output(
    synthesis: dict[str, Any],
) -> dict[str, Any] | None:
    """Persist the private Step 2 payload in one stable shape for reuse.

    Args:
        synthesis: Country synthesis prepared for storage.

    Returns:
        Private structured AI payload, else None when the required fields are absent.
    """
    required_fields = ("summary", "risk_flags", "outlook")
    if any(field_name not in synthesis for field_name in required_fields):
        return None

    return {
        "summary": synthesis["summary"],
        "risk_flags": copy.deepcopy(synthesis["risk_flags"]),
        "outlook": synthesis["outlook"],
    }


def _build_global_overview_structured_output(
    synthesis: dict[str, Any],
) -> dict[str, Any] | None:
    """Persist the private Step 3 payload in one stable shape for reuse."""

    required_fields = ("summary", "risk_flags", "outlook")
    if any(field_name not in synthesis for field_name in required_fields):
        return None

    return {
        "summary": synthesis["summary"],
        "risk_flags": copy.deepcopy(synthesis["risk_flags"]),
        "outlook": synthesis["outlook"],
    }


def _resolve_country_metadata(
    repo: InsightsRepository,
    country_code: str,
) -> dict[str, Any]:
    """Resolve metadata for country syntheses persisted through the storage seam.

    The live monitored panel is intentionally strict, but the deterministic ZA
    development slice still needs stable metadata even after that panel changed.
    """
    country_metadata = repo.get_country_metadata(country_code)
    if country_metadata is not None:
        return country_metadata

    if country_code.upper() == LOCAL_TARGET_COUNTRY:
        return {
            "code": LOCAL_TARGET_COUNTRY,
            "name": LOCAL_TARGET_COUNTRY_NAME,
            "region": LOCAL_TARGET_COUNTRY_REGION,
            "income_level": LOCAL_TARGET_COUNTRY_INCOME_LEVEL,
        }

    raise ValueError(f"Unsupported local country: {country_code}")


def _build_source_provenance(raw_payload: Any) -> dict[str, Any]:
    """Extract persisted source provenance from one raw payload scope.

    Args:
        raw_payload: Raw payload for one scope.

    Returns:
        Source provenance dictionary.
    """
    if not raw_payload:
        return {}

    if isinstance(raw_payload, list):
        exemplar = raw_payload[0] if raw_payload else {}
    elif isinstance(raw_payload, dict):
        exemplar = raw_payload
    else:
        return {}

    provenance: dict[str, Any] = {}
    for field_name in (
        "source_name",
        "source_date_range",
        "source_last_updated",
        "source_id",
    ):
        field_value = exemplar.get(field_name)
        if field_value is not None:
            provenance[field_name] = field_value
    return provenance


def _group_raw_payloads_by_indicator(
    raw_data_points: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group raw fetched data by indicator code for run-scoped archival.

    Args:
        raw_data_points: Raw fetched data points for the run.

    Returns:
        Raw payloads keyed by indicator code.
    """
    grouped_payloads: dict[str, list[dict[str, Any]]] = {}
    for data_point in raw_data_points:
        indicator_code = data_point["indicator_code"]
        grouped_payloads.setdefault(indicator_code, []).append(
            copy.deepcopy(data_point)
        )

    for payload in grouped_payloads.values():
        payload.sort(
            key=lambda item: (item.get("country_code", ""), item.get("year", 0))
        )
    return grouped_payloads


def _raw_archive_relative_path(run_id: str, scope_name: str) -> str:
    """Build the run-scoped relative archive path for one raw payload.

    Args:
        run_id: UUID v4 run identifier.
        scope_name: Fetch scope or manifest key.

    Returns:
        Run-scoped relative archive path.
    """
    return f"runs/{run_id}/raw/{scope_name}.json"
