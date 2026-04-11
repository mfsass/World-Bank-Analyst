"""World Analyst API — Connexion application factory.

Creates and configures the Connexion FlaskApp with OpenAPI spec,
strict request/response validation, and CORS middleware.
"""

import connexion
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware


def create_app() -> connexion.FlaskApp:
    """Create and configure the Connexion application.

    The application reads openapi.yaml and automatically wires routes
    to handler functions via the operationId field. Strict validation
    ensures requests and responses match the spec.

    Returns:
        Configured Connexion FlaskApp instance.
    """
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
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
    )
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
