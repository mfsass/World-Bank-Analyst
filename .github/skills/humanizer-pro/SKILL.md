---
name: humanizer-pro
description: Make World Analyst writing sound direct, specific, and credible. Use for ADRs, README prose, presentation copy, user-facing narrative, explanatory comments, and any text that sounds robotic, inflated, or formulaic.
---

# Humanizer Pro

Use this skill when the writing matters to a human reader and generic AI phrasing would weaken trust.

## Where it applies in this repo

- `docs/DECISIONS.md` entries and other architecture notes
- `README.md`, plans, and presentation-facing repo documentation
- User-facing UI copy and responsible-AI messaging
- AI-generated analyst narrative that needs editorial cleanup before shipping
- Explanatory comments when a comment reads like filler instead of a real engineering judgment

## Default writing standard

- Lead with the actual point.
- Prefer specific facts over abstract claims.
- Use direct verbs and active voice.
- Keep sentences tight unless detail is doing real work.
- Replace vague importance language with the concrete implication.
- If a fact is missing, use a bracketed placeholder instead of inventing it.

## Project-specific calibration

### ADRs and decision writing

- State the decision early.
- Name the trade-off plainly.
- Avoid grand language about transformation, innovation, or strategic journeys.
- Write so a reviewer can quote one sentence and understand the call.

### Finance and analyst narrative

- Lead with the signal, the magnitude, and the risk implication.
- Avoid textbook indicator definitions unless the screen explicitly needs them.
- Prefer language such as inflation pressure, fiscal stress, external vulnerability, and recessionary signal when supported by the data.
- Do not inflate certainty. If evidence is mixed, say that directly.

### Code comments

- Keep comments short.
- Explain why the code exists, what trade-off it protects, or what business rule it encodes.
- Do not narrate syntax or obvious control flow.
- If the code can be made clearer by renaming instead of commenting, rename first.

## Patterns to remove

- Sycophantic openers and closers
- Inflated significance language
- Corporate filler and vague signposting
- Vague attributions without a source
- Passive voice that hides the actor
- Generic positive conclusions
- Comment text that restates the code without adding meaning

## Rewrite process

1. Diagnose the slop: identify the phrase, sentence, or paragraph that sounds generic.
2. Find the real point: ask what fact, judgment, or trade-off the sentence is trying to carry.
3. Rewrite with specifics: numbers, actors, consequences, dates, or explicit uncertainty.
4. Do a short audit pass: ask what still sounds AI-generated, then fix that directly.

## Example: ADR sentence

Before:

> This decision marks a pivotal step in our broader effort to enhance the robustness of the platform.

After:

> We chose Firestore because the dashboard reads document-shaped records and does not need warehouse-style queries.

## Example: code comment

Before:

```python
# Start the thread
Thread(target=_execute_local_pipeline, daemon=True).start()
```

After:

```python
# Return 202 immediately while the background run updates shared in-memory status.
Thread(target=_execute_local_pipeline, daemon=True).start()
```

## Output pattern when rewriting prose

1. Draft rewrite
2. Remaining AI tells
3. Final rewrite
4. Missing facts to confirm, if any