"""Indicator API handlers.

Serves processed economic indicator insights from the shared local repository.
"""

import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.repository import get_repository

logger = logging.getLogger(__name__)


def get_all(country: str | None = None) -> tuple[list[dict[str, Any]], int]:
    """Retrieve all indicator insights, optionally filtered by country.

    Args:
        country: ISO 3166-1 alpha-2 country code for filtering.

    Returns:
        Tuple of (response_body, status_code).
    """
    logger.info("Retrieving indicators (country=%s)", country)
    repository = get_repository()
    return repository.list_indicator_insights(country), 200
