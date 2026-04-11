---
name: write-prd
description: "Draft a World Analyst PRD or feature brief before implementation. Clarifies missing scope before writing."
agent: world-analyst-prd
tools:
  - read
  - edit
  - search
  - web
  - vscode/askQuestions
  - todo
argument-hint: "Describe the feature, user, business outcome, and known constraints."
---

Draft a World Analyst PRD for:

${input:request:Describe the feature, user, business outcome, and any known constraints}

Use [GEMINI.md](../../GEMINI.md), [AGENTS.md](../../AGENTS.md), and [docs/DECISIONS.md](../../docs/DECISIONS.md).

If the brief is materially underspecified, stop and use #tool:vscode/askQuestions before drafting.

If the target PRD path is clear, write or update the PRD directly under [docs/prds](../../docs/prds) instead of only returning a proposed outline. If the draft locks a meaningful trade-off, append the ADR entry directly to [docs/DECISIONS.md](../../docs/DECISIONS.md).

Return:

- goal
- user and business value
- non-goals
- scope
- functional requirements
- acceptance criteria
- dependencies and risks
- validation plan
- ADR requirement
- open questions