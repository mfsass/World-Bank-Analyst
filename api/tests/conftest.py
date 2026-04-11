"""Shared fixtures for API business tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "api"

for path in (REPO_ROOT, API_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app import create_app  # noqa: E402
from shared.repository import get_repository, reset_repository_cache  # noqa: E402


@pytest.fixture(autouse=True)
def reset_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Reset the shared repository between tests."""
    monkeypatch.setenv("WORLD_ANALYST_LOCAL_RAW_ARCHIVE_DIR", str(tmp_path / "raw-archives"))
    monkeypatch.delenv("REPOSITORY_MODE", raising=False)
    monkeypatch.delenv("WORLD_ANALYST_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("WORLD_ANALYST_RAW_ARCHIVE_BUCKET", raising=False)
    reset_repository_cache()
    repository = get_repository()
    repository.reset()
    yield
    repository.reset()
    reset_repository_cache()


@pytest.fixture()
def client():
    """Create a test client for the Connexion application."""
    connexion_app = create_app()
    return connexion_app.test_client()
