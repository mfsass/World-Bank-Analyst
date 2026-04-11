---
name: ship-check
description: "Run a findings-first review for a World Analyst change before shipping it."
agent: world-analyst-reviewer
tools:
  - read
  - search
  - search/codebase
argument-hint: "Describe the change, branch, or files you want reviewed."
---

Review this World Analyst change before it ships:

${input:request:Describe the change or review scope}

Focus on:

- correctness and regressions
- openapi and handler drift
- design-system violations
- missing or weak tests
- missing ADR updates in [docs/DECISIONS.md](../../docs/DECISIONS.md)

Return findings first, then a short residual-risk summary.
