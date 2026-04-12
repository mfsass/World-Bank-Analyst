"""Overview API handler.

Serves the monitored-set overview briefing for the Global Overview page.
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


def get() -> tuple[dict[str, Any], int]:
    """Retrieve the latest monitored-set overview briefing.

    Returns:
        Tuple of (overview_payload, status_code).
    """
    logger.info("Retrieving monitored-set overview")
    repository = get_repository()
    overview = repository.get_global_overview()
    if overview is None:
        return {"error": "Not found"}, 404
    return overview, 200
