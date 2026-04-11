---
name: spec-first-api
description: "Implement an API contract change by updating OpenAPI first, then handlers and tests."
agent: world-analyst-implementer
tools:
  - read
  - edit
  - search
  - search/codebase
  - runCommand
argument-hint: "Describe the endpoint, payload, or contract change."
---

Implement this API change for World Analyst:

${input:request:Describe the endpoint or contract change}

Start in [api/openapi.yaml](../../api/openapi.yaml).
Use [connexion-api-development](../skills/connexion-api-development/SKILL.md) and [world-analyst-engineering](../skills/world-analyst-engineering/SKILL.md).

Requirements:

- change the contract first
- align handlers with the contract
- update or add business-outcome tests
- call out whether [docs/DECISIONS.md](../../docs/DECISIONS.md) needs an ADR entry
