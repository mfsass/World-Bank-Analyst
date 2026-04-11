# AI-Native Workflow Baseline

This repo already had strong global context in [GEMINI.md](../GEMINI.md), [AGENTS.md](../AGENTS.md), and [.github/copilot-instructions.md](../.github/copilot-instructions.md). The baseline added here keeps that global context intact and adds reusable workflow assets instead of more always-on instructions.

## What This Adds

- File-scoped instructions in [.github/instructions](../.github/instructions) so the right rules load for API, pipeline, frontend, and tests.
- Custom agents in [.github/agents](../.github/agents) for planning, implementation, and review with explicit handoffs.
- Prompt files in [.github/prompts](../.github/prompts) for the highest-value recurring tasks.
- Planning and task scaffolds in [docs/plans/TEMPLATE.md](../docs/plans/TEMPLATE.md) and [tasks/todo.md](../tasks/todo.md).
- Recommended extensions in [.vscode/extensions.json](../.vscode/extensions.json).

## Recommended Copilot Loop

1. Start non-trivial work with `/start-feature` or the `world-analyst-planner` agent.
2. For API changes, use `/spec-first-api` so the contract changes before handler code.
3. For substantive code changes, use the `world-analyst-dual-lane` agent or run the `world-analyst-implementer` and `world-analyst-reviewer` lanes in parallel while the main conversation keeps final ownership.
4. Use the `world-analyst-implementer` agent alone only for trivial or tightly scoped edits where a second lane would cost more than it saves.
5. Run `/ship-check` or the `world-analyst-reviewer` agent against the actual diff before shipping if the task was non-trivial.
6. If the change contains a real trade-off, run `/log-decision` and append the result to [docs/DECISIONS.md](../docs/DECISIONS.md).

## Dual-Lane Guidance

- Keep the main thread as the coordinator. This is a manager-style workflow, not a permanent handoff.
- Start the review lane early enough to challenge the approach, then run it again on the actual diff for substantive work.
- Prefer a different model for the review lane when the custom agent can pin one.
- Do not force the pattern onto read-only questions, one-line mechanical edits, or formatting-only changes. The review tax is not free.

## Why This Is Lean

- Global instructions stay in one place.
- Scoped instructions only activate when relevant files are in play.
- Prompt files cover repeatable tasks without duplicating project rules.
- Agents separate planning, implementation, and review so the repo supports deliberate orchestration instead of one giant all-purpose mode.

## Optional Local VS Code Settings

`.vscode/settings.json` is currently ignored in this repo, so local editor settings should stay user-specific. If you want a strong local setup, use a personal settings file with values such as:

```json
{
  "chat.useAgentsMdFile": true,
  "chat.includeApplyingInstructions": true,
  "chat.includeReferencedInstructions": true,
  "chat.promptFilesRecommendations": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[javascript]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[javascriptreact]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[css]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

## Diagnostics

- Use the Chat Customizations editor to inspect loaded prompts, instructions, and agents.
- Use Chat diagnostics if a prompt, agent, or instruction file is not being picked up.
- Keep instructions concise. If a rule can be enforced by Ruff, ESLint, or Prettier, prefer tooling over more prose.
