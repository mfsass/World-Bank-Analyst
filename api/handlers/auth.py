"""Authentication helpers for local API key validation."""

from __future__ import annotations

import os
from typing import Any


def get_runtime_environment() -> str:
    """Return the configured runtime environment.

    Returns:
        Lowercase runtime environment name. Defaults to ``local``.
    """
    return os.environ.get("WORLD_ANALYST_RUNTIME_ENV", "local").strip().lower()


def get_expected_api_key() -> str | None:
    """Return the configured API key for the current runtime.

    Local development keeps a fixed fallback so the API and Vite proxy can run
    without extra setup. Non-local environments must provide an explicit key.

    Returns:
        Expected API key for the current runtime, or ``None`` when a non-local
        environment is missing required configuration.
    """
    configured_api_key = os.environ.get("WORLD_ANALYST_API_KEY")
    if configured_api_key:
        return configured_api_key

    if get_runtime_environment() == "local":
        return "local-dev"

    return None


def require_api_key_configuration() -> None:
    """Fail fast when deployed auth configuration is missing."""
    if get_expected_api_key() is None:
        raise RuntimeError(
            "WORLD_ANALYST_API_KEY must be set when WORLD_ANALYST_RUNTIME_ENV is not local."
        )


def validate_api_key(apikey: str, required_scopes: list[str] | None = None) -> dict[str, Any] | None:
    """Validate the configured API key for local development.

    Args:
        apikey: API key provided in the X-API-Key header.
        required_scopes: Unused for this API-key scheme.

    Returns:
        Auth context dict when the key is valid, else None.
    """
    del required_scopes

    expected_api_key = get_expected_api_key()
    if expected_api_key is None:
        return None

    if apikey == expected_api_key:
        return {"sub": "local-dev-user"}
    return None
