"""Storage operations for repository-backed insights and raw-data archival.

Mixed-document insight writes now flow through the shared repository contract so
the pipeline can target local or Firestore-backed persistence without changing
its orchestration logic.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.repository import InsightsRepository, get_repository

logger = logging.getLogger(__name__)


def store_slice(
    insights: list[dict[str, Any]],
    country_syntheses: dict[str, dict[str, Any]],
    repository: InsightsRepository | None = None,
) -> dict[str, int]:
    """Persist the current slice into the configured repository backend.

    Args:
        insights: Enriched per-indicator insight payloads.
        country_syntheses: Country synthesis payloads keyed by country code.
        repository: Shared repository instance.

    Returns:
        Counts of indicator and country records written.
    """
    repo = repository or get_repository()
    updated_at = datetime.now(timezone.utc).isoformat()

    indicator_writes = 0
    for insight in insights:
        repo.upsert_indicator(
            {
                "indicator_code": insight["indicator_code"],
                "indicator_name": insight["indicator_name"],
                "country_code": insight["country_code"],
                "latest_value": insight["latest_value"],
                "previous_value": insight.get("previous_value"),
                "percent_change": insight.get("percent_change"),
                "is_anomaly": bool(insight.get("is_anomaly", False)),
                "ai_analysis": insight.get("ai_analysis", ""),
                "data_year": insight["data_year"],
                "updated_at": updated_at,
            }
        )
        indicator_writes += 1

    country_writes = 0
    for country_code, synthesis in country_syntheses.items():
        country_metadata = repo.get_country_metadata(country_code)
        if country_metadata is None:
            raise ValueError(f"Unsupported local country: {country_code}")

        repo.upsert_country(
            {
                **country_metadata,
                "macro_synthesis": synthesis["summary"],
                "risk_flags": synthesis["risk_flags"],
                "outlook": synthesis["outlook"],
                "updated_at": updated_at,
            }
        )
        country_writes += 1

    logger.info("Stored %d indicator insights and %d country syntheses", indicator_writes, country_writes)
    return {
        "indicator_records": indicator_writes,
        "country_records": country_writes,
    }


def store_local_slice(
    insights: list[dict[str, Any]],
    country_syntheses: dict[str, dict[str, Any]],
    repository: InsightsRepository | None = None,
) -> dict[str, int]:
    """Backward-compatible wrapper for the original local-slice storage call.

    Args:
        insights: Enriched per-indicator insight payloads.
        country_syntheses: Country synthesis payloads keyed by country code.
        repository: Shared repository instance.

    Returns:
        Counts of indicator and country records written.
    """
    return store_slice(insights, country_syntheses, repository)


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


def archive_raw_data(data: list[dict[str, Any]], project_id: str, bucket_name: str) -> str:
    """Archive raw World Bank API responses to GCS.

    Creates timestamped JSON blobs for audit trail and reproducibility.

    Args:
        data: Raw API response data.
        project_id: GCP project ID.
        bucket_name: GCS bucket name for raw data archival.

    Returns:
        GCS blob path of the archived file.
    """
    from google.cloud import storage

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    blob_name = f"raw_data/{timestamp}.json"
    blob = bucket.blob(blob_name)

    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json",
    )

    logger.info("Archived raw data to gs://%s/%s", bucket_name, blob_name)
    return f"gs://{bucket_name}/{blob_name}"
