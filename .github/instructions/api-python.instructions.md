---
name: API Handler Rules
description: "Use when editing Python files under api/ so handler changes remain spec-driven, typed, and testable."
applyTo: api/**/*.py
---

- Do not add route behavior here unless it is represented in [api/openapi.yaml](../../api/openapi.yaml).
- Keep handlers thin: parse input, delegate domain logic, return payloads that match the spec.
- Use type hints, Google-style docstrings, and structured logging instead of `print()`.
- Add concise inline comments when orchestration, contract shaping, or business thresholds would not be obvious from the handler code alone.
- Update tests to prove the behavior promised by the contract, not implementation details.
- Use [connexion-api-development](../skills/connexion-api-development/SKILL.md) and [world-analyst-engineering](../skills/world-analyst-engineering/SKILL.md) when the change is non-trivial.
