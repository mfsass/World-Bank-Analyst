"""In-memory repository used for local development and tests.

The local backend preserves the same mixed-document contract as Firestore so
the API and pipeline can switch storage backends without changing payload shape.
"""

from __future__ import annotations

import copy
from threading import RLock
from typing import Any

from shared.country_catalog import MONITORED_COUNTRY_CATALOG
from shared.repository import (
    default_pipeline_status,
    project_public_record,
    require_fields,
)


class InMemoryInsightsRepository:
    """Mixed-document local repository used by the API and pipeline.

    Records are stored as a single logical collection with mixed entity types,
    mirroring the future Firestore model while remaining process-local.
    """

    def __init__(self) -> None:
        """Initialise the repository with default status."""
        self._lock = RLock()
        self._records: dict[str, dict[str, Any]] = {}
        self.reset()

    def reset(self) -> None:
        """Clear all stored records and restore idle pipeline status."""
        with self._lock:
            self._records = {
                self._document_id("pipeline_status", "current"): {
                    "entity_type": "pipeline_status",
                    **default_pipeline_status(),
                }
            }

    def list_countries(self) -> list[dict[str, Any]]:
        """List supported countries for the local slice.

        Returns:
            Country metadata entries.
        """
        return [copy.deepcopy(country) for country in MONITORED_COUNTRY_CATALOG.values()]

    def get_country_metadata(self, country_code: str) -> dict[str, Any] | None:
        """Return metadata for a supported country.

        Args:
            country_code: ISO 3166-1 alpha-2 country code.

        Returns:
            Country metadata dict when supported, else None.
        """
        return copy.deepcopy(MONITORED_COUNTRY_CATALOG.get(country_code.upper()))

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
        self._upsert(document_id, {"entity_type": "indicator", **record, "country_code": country_code})

    def upsert_country(self, record: dict[str, Any]) -> None:
        """Store or replace a country synthesis record.

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
        self._upsert(document_id, {"entity_type": "country", **record, "code": country_code})

    def upsert_pipeline_status(self, record: dict[str, Any]) -> None:
        """Store the latest pipeline status record.

        Args:
            record: Pipeline status payload.

        Raises:
            ValueError: If the record is missing required fields.
        """
        require_fields(record, ("status", "steps"), "pipeline_status")
        document_id = self._document_id("pipeline_status", "current")
        self._upsert(document_id, {"entity_type": "pipeline_status", **record})

    def list_indicator_insights(self, country_code: str | None = None) -> list[dict[str, Any]]:
        """Retrieve indicator insight payloads.

        Args:
            country_code: Optional ISO country code filter.

        Returns:
            Sorted list of indicator insight dicts.
        """
        normalized = country_code.upper() if country_code else None
        with self._lock:
            records = [
                project_public_record(record)
                for record in self._records.values()
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
        document_id = self._document_id("country", normalized)
        with self._lock:
            country_record = self._records.get(document_id)
            if country_record is None:
                return None

            detail = project_public_record(country_record)

        detail["indicators"] = self.list_indicator_insights(normalized)
        return detail

    def get_pipeline_status_record(self) -> dict[str, Any]:
        """Return the stored pipeline status, including private fields.

        Returns:
            Full stored pipeline status payload.
        """
        document_id = self._document_id("pipeline_status", "current")
        with self._lock:
            record = self._records.get(document_id, {"entity_type": "pipeline_status", **default_pipeline_status()})

        stored_record = copy.deepcopy(record)
        stored_record.pop("entity_type", None)
        return stored_record

    def get_pipeline_status(self) -> dict[str, Any]:
        """Return the latest pipeline status payload.

        Returns:
            Pipeline status dict.
        """
        document_id = self._document_id("pipeline_status", "current")
        with self._lock:
            record = self._records.get(document_id, {"entity_type": "pipeline_status", **default_pipeline_status()})
        return project_public_record(record)

    def _upsert(self, document_id: str, record: dict[str, Any]) -> None:
        """Write a record under a stable document identifier.

        Args:
            document_id: Logical mixed-document identifier.
            record: Record payload.
        """
        with self._lock:
            self._records[document_id] = copy.deepcopy(record)

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

