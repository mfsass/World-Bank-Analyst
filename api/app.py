"""World Analyst API — Connexion application factory.

Creates and configures the Connexion FlaskApp with OpenAPI spec,
strict request/response validation, and CORS middleware.
"""

import os

import connexion
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

from handlers.auth import require_api_key_configuration


LOCAL_ALLOWED_ORIGINS = [
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _get_allowed_origins() -> list[str]:
    """Return the allowed origins for the active runtime.

    Local development stays explicit but convenient. Deployed environments must
    set ``WORLD_ANALYST_ALLOWED_ORIGINS`` and cannot use a wildcard.
    """
    runtime_environment = os.environ.get("WORLD_ANALYST_RUNTIME_ENV", "local").strip().lower()
    if runtime_environment == "local":
        return LOCAL_ALLOWED_ORIGINS

    configured_origins = os.environ.get("WORLD_ANALYST_ALLOWED_ORIGINS", "")
    allowed_origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]

    if not allowed_origins:
        raise RuntimeError(
            "WORLD_ANALYST_ALLOWED_ORIGINS must be set when WORLD_ANALYST_RUNTIME_ENV is not local."
        )

    if "*" in allowed_origins:
        raise RuntimeError(
            "WORLD_ANALYST_ALLOWED_ORIGINS cannot contain '*' outside local development."
        )

    return allowed_origins


def create_app() -> connexion.FlaskApp:
    """Create and configure the Connexion application.

    The application reads openapi.yaml and automatically wires routes
    to handler functions via the operationId field. Strict validation
    ensures requests and responses match the spec.

    Returns:
        Configured Connexion FlaskApp instance.
    """
    require_api_key_configuration()

    app = connexion.FlaskApp(
        __name__,
        specification_dir=".",
    )
    app.add_api(
        "openapi.yaml",
        base_path="/api/v1",
        strict_validation=True,
        validate_responses=True,
    )
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=_get_allowed_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type"],
    )
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
