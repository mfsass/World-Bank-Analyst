# Contributing

This repo is part product artifact and part paper trail. Treat both as first-class.

## What Belongs In Git

- Product code in `api/`, `pipeline/`, `frontend/`, and `shared/`
- Design and planning context in `docs/`, `docs/prds/`, `docs/plans/`, `Design Mockups/`, and `Project Context/`
- AI workflow assets in `.github/`, `.agents/`, `AGENTS.md`, and `GEMINI.md`
- `.vscode/extensions.json` by default, with any other editor files added only by deliberate exception

## What Stays Out

- Secrets, `.env` files, service-account keys, and any credential export
- Virtual environments, `node_modules/`, caches, coverage outputs, and build artifacts
- Personal editor settings, scratch files, and local-only AI notes
- Generated noise that a reviewer cannot act on or explain

## Working Agreement

1. Start with intent. If the change has real scope, capture the why in a plan, PRD, or issue-sized note before editing code.
2. Keep the contract ahead of the implementation. For API changes, `api/openapi.yaml` moves before handlers.
3. Keep tests business-facing. Add or update tests to prove the user-visible outcome, not just the mechanism.
4. Log trade-offs. If a reviewer could reasonably ask why one option beat another, add an ADR in `docs/DECISIONS.md`.
5. Stage deliberately. Use hunk staging or explicit file staging so each commit carries one clear intent.

## Commit Shape

- Prefer one intent per commit.
- Keep repo hygiene, documentation, tests, and behavior changes separate when practical.
- Use `type: description` commit messages such as `docs: clarify repository workflow`.
- Do not mix generated output or unrelated cleanup into a feature commit.
- If a change is hard to explain in one sentence, it is probably too large for one commit.

## Bootstrap Sequence

For this repository, the preferred opening history is:

1. `chore: establish repository hygiene`
2. `docs: document repository workflow`
3. `chore: import world analyst baseline`

That order makes the audit trail readable from the start: first define the boundaries, then document the method, then import the working baseline.

## Pre-Commit Check

- The staged diff matches a single intention.
- No secrets, local state, or generated output are staged.
- Tests relevant to the change have been run or the gap is explicit.
- The README and ADR log still describe reality.
