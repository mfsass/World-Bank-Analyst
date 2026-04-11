"""Authentication helpers for local API key validation."""

from __future__ import annotations

import os
from typing import Any


def validate_api_key(apikey: str, required_scopes: list[str] | None = None) -> dict[str, Any] | None:
    """Validate the configured API key for local development.

    Args:
        apikey: API key provided in the X-API-Key header.
        required_scopes: Unused for this API-key scheme.

    Returns:
        Auth context dict when the key is valid, else None.
    """
    del required_scopes

    expected_api_key = os.environ.get("WORLD_ANALYST_API_KEY", "local-dev")
    if apikey == expected_api_key:
        return {"sub": "local-dev-user"}
    return None
