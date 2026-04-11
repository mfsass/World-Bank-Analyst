---
name: log-decision
description: "Draft a short ADR entry for a trade-off or architecture choice in World Analyst."
agent: world-analyst-planner
tools:
  - read
  - edit
  - search
argument-hint: "Describe the choice, alternatives, and why it matters."
---

Draft an ADR entry for this World Analyst decision:

${input:request:Describe the decision, alternatives, and chosen direction}

Use the format and numbering style in [docs/DECISIONS.md](../../docs/DECISIONS.md).

When the ADR numbering is clear, append the entry directly to [docs/DECISIONS.md](../../docs/DECISIONS.md) instead of only returning draft text.

Requirements:

- keep each section concise
- state the real trade-off
- reference the affected area of the repo
- do not log routine implementation details as ADRs
