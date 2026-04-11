---
description: Log an architecture decision to docs/DECISIONS.md
---

## When to Use

Run `/decision` whenever you:
- Choose between two viable technical approaches
- Reject a common default (e.g., "why not FastAPI?", "why not Tailwind?")
- Change an earlier decision
- Add a new dependency or service
- Make a trade-off that a reviewer might question

## Template

Append this to `docs/DECISIONS.md`:

```markdown
---

## ADR-NNN: [Short title — verb phrase preferred]

**Context:** [What problem or question triggered this decision?]

**Decision:** [What did we choose?]

**Why:** [The reasoning — be specific, cite numbers if possible]

**Trade-off:** [What we gave up, and why that's acceptable]

**Date:** YYYY-MM-DD
```

## Steps

1. Read `docs/DECISIONS.md` to get the current ADR count
// turbo
2. Determine the next ADR number (increment from the last one)
3. Append the new ADR entry to `docs/DECISIONS.md` using the template above
4. Confirm the entry was added correctly by reading the file
// turbo

## Rules

- **Keep it short.** Each section should be 1-3 sentences. This is a log, not an essay.
- **No AI slop.** Write like a human engineer explaining to a colleague.
- **Always include trade-offs.** Every decision gives up something. Say what.
- **Date it.** So we know when the decision was made.
- **Reference code.** Link to the file or function the decision affects.
