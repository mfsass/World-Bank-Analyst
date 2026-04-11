---
name: connexion-api-development
description: Connexion + OpenAPI development patterns for World Analyst. Use when writing or modifying the API spec, creating handlers, adding routes, implementing auth, or debugging API issues. This skill enforces Spec-Driven Development (SDD) — the spec is the source of truth, never the code.
---

# Connexion API Development — Spec-Driven Development

> **Core Principle**: The API spec (`openapi.yaml`) is the source of truth.
> Connexion reads it, wires routes, validates requests. You implement handlers. Never the reverse.

---

## When to Apply

Use this skill when the task involves:

- Adding or modifying API endpoints
- Writing or editing `openapi.yaml`
- Creating handler functions in `api/handlers/`
- Implementing request validation or error handling
- Adding authentication or authorization
- Debugging API routing, 404s, or validation errors

**Skip** for frontend-only work, pipeline internals, or infrastructure.

---

## The SDD Workflow

```
1. Define the endpoint in openapi.yaml
2. Point operationId to handler function
3. Implement the handler function
4. Write a test that validates business behaviour
5. Run ruff check + pytest
```

**Never:** Write a handler first and then add it to the spec. That's code-driven development, not spec-driven.

---

## OpenAPI Spec Patterns

### Route Definition

```yaml
paths:
  /api/v1/indicators:
    get:
      operationId: handlers.indicators.get_all
      summary: Retrieve all indicator insights
      tags:
        - Indicators
      security:
        - ApiKeyAuth: []
      parameters:
        - name: country
          in: query
          required: false
          schema:
            type: string
            description: ISO 3166-1 alpha-2 country code
      responses:
        '200':
          description: List of indicator insights
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/IndicatorInsight'
        '401':
          description: Unauthorized — missing or invalid API key
        '500':
          description: Internal server error
```

### Key Rules

1. **operationId** maps directly to `module.function` — e.g., `handlers.indicators.get_all` resolves to `api/handlers/indicators.py::get_all()`
2. **Every route** must have `security: [ApiKeyAuth: []]` unless explicitly public (health check only)
3. **Response schemas** should use `$ref` to components, not inline definitions
4. **Use semantic HTTP methods:** GET for reads, POST for triggers, no PATCH/PUT unless updating resources

### Authentication

```yaml
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
```

---

## Handler Patterns

### Standard Handler Structure

```python
"""Indicator API handlers.

Serves processed economic indicator insights from Firestore.
"""

import logging
from typing import Any

from google.cloud import firestore

logger = logging.getLogger(__name__)
db = firestore.Client()


def get_all(country: str | None = None) -> tuple[list[dict[str, Any]], int]:
    """Retrieve all indicator insights, optionally filtered by country.

    Args:
        country: ISO 3166-1 alpha-2 country code for filtering.

    Returns:
        Tuple of (response_body, status_code).
    """
    try:
        collection = db.collection("insights")
        if country:
            collection = collection.where("country_code", "==", country.upper())

        docs = collection.stream()
        results = [doc.to_dict() for doc in docs]
        logger.info("Retrieved %d indicators", len(results))
        return results, 200

    except Exception:
        logger.exception("Failed to retrieve indicators")
        return {"error": "Internal server error"}, 500
```

### Handler Rules

1. **Type hints** on every function signature
2. **Google-style docstrings** — Args, Returns sections
3. **Return tuples** `(body, status_code)` — Connexion handles serialisation
4. **Log with `logging`**, never `print()`
5. **Parameters match openapi.yaml** — Connexion passes query/path params as function arguments
6. **Error handling:** catch broadly at the handler level, return structured error responses

---

## App Factory Pattern

```python
"""World Analyst API — Connexion application factory."""

import connexion
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware


def create_app() -> connexion.FlaskApp:
    """Create and configure the Connexion application.

    Returns:
        Configured Connexion FlaskApp instance.
    """
    app = connexion.FlaskApp(
        __name__,
        specification_dir=".",
    )
    app.add_api(
        "openapi.yaml",
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
```

---

## Testing Pattern

```python
"""Test indicator handlers — business-driven validation."""

import pytest


class TestGetAllIndicators:
    """Validate indicator retrieval business logic."""

    def test_returns_insights_for_valid_country(self, client):
        """Pipeline-processed insights are retrievable by country code."""
        response = client.get("/api/v1/indicators?country=ZA")
        assert response.status_code == 200
        data = response.json()
        assert all(d["country_code"] == "ZA" for d in data)

    def test_rejects_request_without_api_key(self, client_no_auth):
        """Unauthenticated requests receive 401."""
        response = client_no_auth.get("/api/v1/indicators")
        assert response.status_code == 401
```

**Testing philosophy:** Test what the business cares about. "Can I get South Africa's GDP insights?" — yes. "Does the function call Firestore's stream() method exactly once?" — no.

---

## Common Pitfalls

| Mistake | Fix |
|---------|-----|
| Handler returns dict without status code | Always return `(body, status_code)` tuple |
| Route works but 404s | Check `operationId` matches `module.function` exactly |
| Validation errors on valid requests | Check parameter names match between spec and handler args |
| CORS blocked | Add CORSMiddleware via Connexion's middleware system |
| Auth not enforced | Ensure `security` key is on each path, not just globally |

---

## File Map

```
api/
├── openapi.yaml          ← Write this FIRST
├── app.py                ← create_app() factory
├── handlers/
│   ├── __init__.py
│   ├── indicators.py     ← /api/v1/indicators
│   ├── countries.py      ← /api/v1/countries
│   ├── health.py         ← /health (no auth)
│   └── pipeline.py       ← /api/v1/pipeline/trigger
├── requirements.txt
└── tests/
    └── test_handlers.py
```
