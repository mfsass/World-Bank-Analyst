"""Firestore-backed mixed-document repository.

This adapter persists indicator insights, country briefings, and pipeline status
in the same logical collection so the API can keep its current response shapes
while moving off process-local state.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from google.cloud import firestore

from shared.repository import LOCAL_COUNTRY_CATALOG, default_pipeline_status, require_fields

logger = logging.getLogger(__name__)


class FirestoreInsightsRepository:
    """Durable repository backed by Firestore mixed documents."""

    def __init__(
        self,
        project_id: str,
        collection_name: str = "insights",
        client: firestore.Client | None = None,
    ) -> None:
        """Initialise the Firestore repository.

        Args:
            project_id: GCP project identifier.
            collection_name: Firestore collection storing mixed documents.
            client: Optional injected Firestore client for tests.
        """
        # Firestore clients are safe to reuse across threads, so the repository does
        # not need the explicit per-record locking used by the in-memory backend.
        self._client = client or firestore.Client(project=project_id)
        self._collection = self._client.collection(collection_name)

    def reset(self) -> None:
        """Clear all mixed documents and restore idle status.

        This is mainly used by tests and local debugging helpers.
        """
        batch = self._client.batch()
        wrote_delete = False
        for snapshot in self._collection.stream():
            batch.delete(snapshot.reference)
            wrote_delete = True
        if wrote_delete:
            batch.commit()
        self.upsert_pipeline_status(default_pipeline_status())

    def list_countries(self) -> list[dict[str, Any]]:
        """List monitored countries supported by the current slice.

        Returns:
            Country metadata entries.
        """
        return [copy.deepcopy(country) for country in LOCAL_COUNTRY_CATALOG.values()]

    def get_country_metadata(self, country_code: str) -> dict[str, Any] | None:
        """Return metadata for a monitored country.

        Args:
            country_code: ISO 3166-1 alpha-2 country code.

        Returns:
            Country metadata dict when supported, else None.
        """
        return copy.deepcopy(LOCAL_COUNTRY_CATALOG.get(country_code.upper()))

    def upsert_indicator(self, record: dict[str, Any]) -> None:
        """Store or replace an indicator insight record.

        Args:
            record: Mixed-document indicator record.

        Raises:
            ValueError: If the record is missing required fields.
        """
        require_fields(record, ("country_code", "indicator_code", "indicator_name", "data_year"), "indicator")
        country_code = record["country_code"].upper()
        indicator_code = record["indicator_code"]
        document_id = self._document_id("indicator", f"{country_code}:{indicator_code}")
        self._collection.document(document_id).set(
            {"entity_type": "indicator", **record, "country_code": country_code},
            merge=True,
        )

    def upsert_country(self, record: dict[str, Any]) -> None:
        """Store or replace a materialised country briefing.

        Args:
            record: Mixed-document country record.

        Raises:
            ValueError: If the record is missing required fields.
        """
        require_fields(
            record,
            ("code", "name", "region", "income_level", "macro_synthesis", "risk_flags", "outlook"),
            "country",
        )
        country_code = record["code"].upper()
        document_id = self._document_id("country", country_code)
        self._collection.document(document_id).set(
            {"entity_type": "country", **record, "code": country_code},
            merge=True,
        )

    def upsert_pipeline_status(self, record: dict[str, Any]) -> None:
        """Store the latest pipeline status record.

        Args:
            record: Pipeline status payload.

        Raises:
            ValueError: If the record is missing required fields.
        """
        require_fields(record, ("status", "steps"), "pipeline_status")
        document_id = self._document_id("pipeline_status", "current")
        self._collection.document(document_id).set(
            {"entity_type": "pipeline_status", **record},
            merge=True,
        )

    def list_indicator_insights(self, country_code: str | None = None) -> list[dict[str, Any]]:
        """Retrieve indicator insight payloads.

        Args:
            country_code: Optional ISO country code filter.

        Returns:
            Sorted list of indicator insight dicts.
        """
        normalized = country_code.upper() if country_code else None
        records_to_scan = self._scan_records()
        records = [
            self._public_record(record)
            for record in records_to_scan
            if record.get("entity_type") == "indicator"
            and (normalized is None or record.get("country_code") == normalized)
        ]
        return sorted(records, key=lambda item: item["indicator_name"])

    def get_country_detail(self, country_code: str) -> dict[str, Any] | None:
        """Retrieve a country detail payload.

        Args:
            country_code: ISO 3166-1 alpha-2 country code.

        Returns:
            Country detail payload or None when not yet materialised.
        """
        normalized = country_code.upper()
        snapshot = self._collection.document(self._document_id("country", normalized)).get()
        if not snapshot.exists:
            return None

        detail = self._public_record(snapshot.to_dict() or {})
        detail["indicators"] = self.list_indicator_insights(normalized)
        return detail

    def get_pipeline_status(self) -> dict[str, Any]:
        """Return the latest pipeline status payload.

        Returns:
            Pipeline status dict.
        """
        snapshot = self._collection.document(self._document_id("pipeline_status", "current")).get()
        if not snapshot.exists:
            return default_pipeline_status()
        return self._public_record(snapshot.to_dict() or {})

    @staticmethod
    def _document_id(entity_type: str, key: str) -> str:
        """Build a mixed-document identifier.

        Args:
            entity_type: Logical record type.
            key: Natural key portion.

        Returns:
            Stable document identifier.
        """
        return f"{entity_type}:{key}"

    @staticmethod
    def _public_record(record: dict[str, Any]) -> dict[str, Any]:
        """Strip repository-only metadata before returning data.

        Args:
            record: Internal record dict.

        Returns:
            Copy without internal metadata.
        """
        public_record = copy.deepcopy(record)
        public_record.pop("entity_type", None)
        return public_record

    def _scan_records(self) -> list[dict[str, Any]]:
        """Load all mixed documents for bounded-scope repository reads.

        Returns:
            List of raw repository records.
        """
        records = [snapshot.to_dict() or {} for snapshot in self._collection.stream()]
        if len(records) > 500:
            logger.warning(
                "Firestore repository scanned %d mixed documents; switch to targeted queries before expanding scope further",
                len(records),
            )
        return records