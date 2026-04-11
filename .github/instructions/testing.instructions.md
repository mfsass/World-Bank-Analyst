---
name: Business Outcome Tests
description: "Use when editing test files so tests validate business behavior, regressions, and contract guarantees instead of implementation trivia."
applyTo: "**/tests/**"
---

- Write tests around business outcomes, contract guarantees, anomaly rules, and user-visible behavior.
- Prefer realistic fixtures and clear test names over mock-heavy interaction testing.
- When changing API behavior, assert the payload shape and status promised by the spec.
- When changing pipeline behavior, assert real indicator outcomes such as anomaly flags or summary outputs.
- Add small comments only when a fixture or scenario needs extra business context; the test name should still do most of the explanatory work.
- Use [world-analyst-engineering](../skills/world-analyst-engineering/SKILL.md) when deciding what a test should prove.
