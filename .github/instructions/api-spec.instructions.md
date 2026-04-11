---
name: API Spec First
description: "Use when editing api/openapi.yaml so contract changes stay spec-first and stay aligned with Connexion handlers."
applyTo: api/openapi.yaml
---

- Treat [api/openapi.yaml](../../api/openapi.yaml) as the API source of truth.
- Define or change the contract before editing handlers, tests, or frontend consumers.
- Keep `operationId`, schemas, examples, and auth requirements aligned in the same change.
- If a contract change creates a meaningful trade-off, log it in [docs/DECISIONS.md](../../docs/DECISIONS.md).
- Use [connexion-api-development](../skills/connexion-api-development/SKILL.md) for detailed patterns.
