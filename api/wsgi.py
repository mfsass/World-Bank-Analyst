"""ASGI entrypoint for production API serving."""

from app import create_app

# Connexion's FlaskApp is an ASGI application. Gunicorn must serve the Connexion
# wrapper itself through an ASGI worker so the mounted OpenAPI routes are active.
app = create_app()
