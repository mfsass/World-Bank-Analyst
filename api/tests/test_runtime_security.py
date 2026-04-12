"""Security-focused runtime configuration tests for the API app."""

from __future__ import annotations

import pytest

from app import create_app
from handlers.auth import validate_api_key


def test_create_app_allows_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local development should boot without extra runtime secrets."""
    monkeypatch.delenv("WORLD_ANALYST_RUNTIME_ENV", raising=False)
    monkeypatch.delenv("WORLD_ANALYST_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("WORLD_ANALYST_API_KEY", raising=False)

    connexion_app = create_app()

    assert connexion_app is not None


def test_create_app_requires_api_key_outside_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deployed runtimes should fail fast when the shared API key is missing."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.setenv("WORLD_ANALYST_ALLOWED_ORIGINS", "https://world-analyst.example")
    monkeypatch.delenv("WORLD_ANALYST_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="WORLD_ANALYST_API_KEY"):
        create_app()


def test_create_app_rejects_wildcard_origins_outside_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deployed runtimes should not allow wildcard CORS origins."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.setenv("WORLD_ANALYST_API_KEY", "configured-secret")
    monkeypatch.setenv("WORLD_ANALYST_ALLOWED_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="WORLD_ANALYST_ALLOWED_ORIGINS"):
        create_app()


def test_create_app_accepts_explicit_production_runtime_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A deployed API should boot once its explicit runtime settings are in place."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.setenv(
        "WORLD_ANALYST_ALLOWED_ORIGINS",
        "https://world-analyst.example, https://review.world-analyst.example",
    )
    monkeypatch.setenv("WORLD_ANALYST_API_KEY", "configured-secret")

    connexion_app = create_app()

    assert connexion_app is not None


def test_validate_api_key_rejects_missing_non_local_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requests should not authenticate when deployed auth is misconfigured."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.delenv("WORLD_ANALYST_API_KEY", raising=False)

    assert validate_api_key("local-dev") is None


def test_validate_api_key_accepts_configured_non_local_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deployed requests should authenticate once the shared runtime secret is configured."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.setenv("WORLD_ANALYST_API_KEY", "configured-secret")

    assert validate_api_key("configured-secret") is not None


def test_protected_endpoint_rejects_requests_without_api_key_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protected endpoints should return 401 when the browser skips the API key."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.setenv("WORLD_ANALYST_ALLOWED_ORIGINS", "https://world-analyst.example")
    monkeypatch.setenv("WORLD_ANALYST_API_KEY", "configured-secret")

    client = create_app().test_client()

    response = client.get("/api/v1/countries")

    assert response.status_code == 401
    assert "configured-secret" not in response.text


def test_protected_endpoint_rejects_wrong_api_key_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protected endpoints should return 401 for the wrong shared API key."""
    monkeypatch.setenv("WORLD_ANALYST_RUNTIME_ENV", "production")
    monkeypatch.setenv("WORLD_ANALYST_ALLOWED_ORIGINS", "https://world-analyst.example")
    monkeypatch.setenv("WORLD_ANALYST_API_KEY", "configured-secret")

    client = create_app().test_client()

    response = client.get("/api/v1/countries", headers={"X-API-Key": "wrong-secret"})

    assert response.status_code == 401
    assert "configured-secret" not in response.text
