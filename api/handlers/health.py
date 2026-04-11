"""Health check handler — no authentication required."""

from datetime import datetime, timezone
from typing import Any


def check() -> tuple[dict[str, Any], int]:
    """Return service health status.

    Returns:
        Tuple of (health_response, 200).
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }, 200
