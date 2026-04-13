"""Country API handlers.

Serves country metadata and per-country intelligence reports.
"""

import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.repository import get_repository  # noqa: E402

logger = logging.getLogger(__name__)


def get_all() -> tuple[list[dict[str, Any]], int]:
    """Retrieve all available countries.

    Returns:
        Tuple of (country_list, status_code).
    """
    logger.info("Retrieving country list")
    repository = get_repository()
    return repository.list_countries(), 200


def get_by_code(country_code: str) -> tuple[dict[str, Any], int]:
    """Retrieve detailed country profile with all indicators and AI analysis.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.

    Returns:
        Tuple of (country_detail, status_code).
    """
    logger.info("Retrieving country detail for %s", country_code)
    repository = get_repository()
    country_detail = repository.get_country_detail(country_code)
    if country_detail is None:
        return {"error": "Not found"}, 404
    return country_detail, 200
