---
name: start-feature
description: "Plan a World Analyst feature or refactor before writing code. Clarifies missing scope before drafting."
agent: world-analyst-planner
tools:
  - read
  - edit
  - search
  - web
  - vscode/askQuestions
  - todo
argument-hint: "Describe the outcome, constraints, and files if known."
---

Plan this World Analyst change:

${input:request:Describe the feature, refactor, or implementation goal}

Use [docs/plans/TEMPLATE.md](../../docs/plans/TEMPLATE.md) when the work is more than trivial.
Consult [GEMINI.md](../../GEMINI.md), [AGENTS.md](../../AGENTS.md), and [docs/DECISIONS.md](../../docs/DECISIONS.md).

If the request leaves material ambiguity around the outcome, constraints, stakeholders, acceptance criteria, or file scope, stop and use #tool:vscode/askQuestions before drafting.

If the user wants a repo-backed planning artifact, create or update it directly under [docs/plans](../../docs/plans), [docs/plans/task-board.md](../../docs/plans/task-board.md), or [docs/plans/implementation-sequence.md](../../docs/plans/implementation-sequence.md) instead of only returning a plan in chat.

Return:

- goal
- affected areas
- implementation steps
- validation plan
- ADR requirement
- open questions
