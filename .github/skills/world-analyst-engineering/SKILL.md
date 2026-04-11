---
name: world-analyst-engineering
description: Engineering principles, quality standards, and ML6 Way of Working for the World Analyst project. Use when making architecture decisions, writing tests, reviewing code quality, planning features, or debating trade-offs. This skill is the "engineering conscience" — consult it before shipping anything.
---

# World Analyst Engineering — ML6 Way of Working

> **Core Thesis**: AI-native engineering is not about maximum velocity or shortcut-driven delivery.
> It is about disciplined, intent-driven development where humans remain accountable
> for every decision the AI makes.

---

## When to Apply

Use this skill when the task involves:

- Architecture decisions or trade-off analysis
- Writing or reviewing tests
- Code quality assessment
- Feature planning or scoping
- Debugging complex issues
- Preparing for code review

**This skill is always relevant.** It is the engineering conscience of the project.

---

## The Four Principles (ML6 WoW)

### 1. Intent-First Development

Before writing code, the engineer must document the "why" and the trade-offs.

**In practice:**
- New features start with a plan in `docs/plans/` (see `@writing-plans`)
- Architecture decisions are recorded in `docs/context/world-analyst-project.md`
- The README explains choices, not just instructions

**Test:** Can you explain every architectural choice without notes?

### 2. PaperTrail of Context

Context lives in the repo, not in ephemeral chats.

**In practice:**
- `GEMINI.md` / `AGENTS.md` / `.github/copilot-instructions.md` — agent context
- `openapi.yaml` — API contract
- `README.md` — the spec that guided the build
- `docs/design-mockups/` — visual language
- Code comments and docstrings — the local explanation for business rules, orchestration, and trade-offs that are not obvious from function names alone

**Test:** Can a new engineer understand every design decision from the repo alone?

### 3. Absolute Ownership

Every line you commit is yours. "The AI wrote it" is not a defence.

**In practice:**
- Review all generated code before committing
- Understand what every function does and why
- Delete code you cannot explain
- No "keep as reference" rationalisation
- Add targeted inline comments where a reviewer would otherwise need chat context to understand why the code is shaped the way it is

**Test:** Can you defend every line in a technical interview?

### 4. Business-Driven Testing

Tests prove business requirements, not coverage metrics.

**In practice:**
- "Does the pipeline detect a 5% GDP anomaly?" ✓
- "Does the function return 200?" ✗ (too shallow)
- "Does the AI narrative include risk flags for negative GDP delta?" ✓
- "Does the mock get called exactly 3 times?" ✗ (implementation testing)

**Test:** Does each test name describe a business outcome?

---

## Code Quality Standards

### Python

```python
# ✓ Good: type hints, docstring, structured logging, clear intent
def detect_anomalies(indicators: list[dict]) -> list[dict]:
    """Flag indicators with year-over-year changes exceeding threshold.

    An anomaly is defined as a >3% absolute change in any indicator
    value between consecutive years. This threshold was chosen to
    balance sensitivity with false-positive rate for macro indicators.

    Args:
        indicators: List of indicator dicts with 'value' and 'year' keys.

    Returns:
        List of indicator dicts with 'is_anomaly' boolean added.
    """
    ...

# ✗ Bad: no types, no docstring, unclear threshold, prints instead of logging
def check(data):
    for d in data:
        if abs(d['change']) > 3:
            print(f"anomaly: {d}")
            d['flag'] = True
    return data
```

### JavaScript/React

```jsx
// ✓ Good: named export, destructured props, semantic structure
export function KPICard({ label, value, trend, freshness }) {
  return (
    <div className="kpi-card">
      <span className="kpi-card__label">{label}</span>
      <span className="kpi-card__value">{value}</span>
      <span className={`kpi-card__trend kpi-card__trend--${trend > 0 ? 'up' : 'down'}`}>
        {trend > 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}%
      </span>
      <span className="kpi-card__freshness">{freshness}</span>
    </div>
  );
}

// ✗ Bad: default export, inline styles, no accessibility
export default function Card(props) {
  return (
    <div style={{background: '#1A1A1A', padding: 20}}>
      <p>{props.v}</p>
    </div>
  );
}
```

---

## Decision Framework

When facing an architectural choice:

1. **State the options** — What are the alternatives?
2. **Identify the constraints** — What does the spec, brief, or design system require?
3. **Evaluate trade-offs** — What do you gain and lose with each option?
4. **Document the decision** — Why this choice? What would change the decision?
5. **Prepare the defence** — How would you explain this in a 15-minute Q&A?

### Example: Firestore vs BigQuery

| Criterion | Firestore | BigQuery |
|-----------|----------|----------|
| Data shape | Document (JSON) ✓ | Tabular |
| Query pattern | doc.get() ✓ | SQL |
| Workload | Read-heavy ✓ | Analytical |
| Overhead | Zero management ✓ | Requires schema |
| Cost | Pay-per-read ✓ | Minimum slot cost |
| Future migration | → BigQuery possible ✓ | N/A |

**Decision:** Firestore. **Defence:** "Our data is naturally document-shaped, our workload is read-heavy serving, and Firestore's serverless model matches Cloud Run's scale-to-zero. If analytical queries become a future requirement, migration is documented as a path."

---

## Workflow Integration

| Phase | Skill | Action |
|-------|-------|--------|
| Planning | `@writing-plans` | Create implementation plan with bite-sized tasks |
| Design | `world-analyst-design-system` | Validate UI decisions against design tokens |
| API | `connexion-api-development` | Write spec first, then handlers |
| Implementation | `@test-driven-development` | RED → GREEN → REFACTOR cycle |
| Review | `@code-reviewer` | Pre-commit quality check |
| Debug | `@systematic-debugging` | Root-cause analysis before fixing |

---

## Anti-Patterns (Red Flags)

| Pattern | Why It's Wrong |
|---------|---------------|
| Writing code before writing a test | Violates TDD; you don't know if the test catches bugs |
| Writing a handler before adding the route to openapi.yaml | Violates SDD; the spec must lead |
| Using `print()` for debugging in committed code | Use `logging` module; print is not production-grade |
| Hardcoding hex colors in components | Use CSS custom properties; hardcoded values drift from the design system |
| Testing mock behaviour instead of business outcomes | You're testing your test infrastructure, not your product |
| Committing code you can't explain | Violates Absolute Ownership; delete and rewrite |
| Adding features not in the plan | YAGNI — if it's not scoped, it's scope creep |

---

## Verification Checklist

Before marking any task complete:

- [ ] All new functions have type hints and docstrings (Python)
- [ ] Non-obvious business rules, orchestration, and state transitions have targeted inline comments
- [ ] Tests validate business outcomes, not implementation details
- [ ] No `print()` or `console.log()` in production code
- [ ] CSS uses custom properties, not hardcoded values
- [ ] openapi.yaml updated BEFORE handler was written
- [ ] Code is explainable and defensible
- [ ] No TODO without a plan reference
