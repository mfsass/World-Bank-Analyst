# PRD delivery principles

These principles apply across World Analyst PRDs. They exist to keep the solution reviewable, teachable, and proportional to the challenge.

## 1. Prefer the simplest solution that satisfies the brief
- Do not add architectural layers, abstractions, or infrastructure unless they solve a real requirement in the challenge or product brief.
- Avoid speculative scale work, generic platform features, or future-proofing that the current scope does not need.
- When two approaches are viable, prefer the one that is easier to explain, easier to test, and easier to maintain.

## 2. Keep code location and ownership obvious
- A reviewer should be able to tell where frontend shell code lives, where page composition lives, where shared UI components live, where API handlers live, and where pipeline orchestration lives without digging.
- Prefer clear file boundaries and straightforward naming over clever indirection.
- Shared code should only become shared when duplication is real and recurring.

## 3. Optimize for human reviewability
- Someone reading the repo should be able to follow the system without needing chat history.
- Documentation should explain why a decision exists, but the code structure should also make the implementation legible on its own.
- PRDs should describe boundaries clearly so implementation does not sprawl across unrelated files or responsibilities.
- For architecture or explanation surfaces, visible technical claims should map to real code, approved PRD targets, or explicit decision records.

## 4. Match implementation complexity to challenge scope
- The project remains bounded around 15 countries, 6 indicators, one Cloud Run job, one Firestore collection, and one live demo URL.
- Design and engineering quality should feel production-grade, but the solution should not imitate a large-enterprise platform where the challenge does not require it.
- A small, well-structured implementation is better than a broad but brittle one.

## 5. Use abstraction only when it reduces confusion
- Introduce components, helpers, and service boundaries when they make the system easier to understand or reuse.
- Do not split logic across many tiny files if that makes the feature harder to trace.
- If a new abstraction needs a long explanation to justify itself, it is probably too early.

## 6. Preserve truthful UX without overbuilding
- The interface should feel deliberate and polished, but it must not pretend unfinished systems are complete.
- Placeholder states are acceptable when clearly controlled and when they protect the final page structure.
- Technical explanation content such as architecture diagrams, system flows, and telemetry needs claim-to-code or claim-to-PRD traceability rather than looser placeholder treatment.
- Interaction polish should improve clarity and confidence, not add decorative complexity.

## 7. Make every PRD executable
- Each PRD should be narrow enough to implement without guessing what belongs in or out of scope.
- Acceptance criteria should validate user-visible outcomes and architectural intent, not implementation trivia.
- Each PRD should leave the repo in a cleaner and more understandable state than before.

## 8. Recommended Order
- Implement durable system truth before review-facing explanation.
- Recommended implementation order lives in `docs/plans/implementation-sequence.md` and should be treated as the working sequence unless a new ADR changes it.
