---
name: llm-prompting-and-evaluation
description: "LLM prompting guidelines (Gemini + OpenAI), structured output patterns, and LLM-as-Judge evaluation framework. Use when designing, testing, or iterating on AI prompts for the two-step analysis chain."
---

# LLM Prompting & Evaluation Skill

> **Scope:** Designing prompts for the World Analyst two-step AI chain, enforcing structured JSON output, and evaluating prompt quality with LLM-as-Judge patterns.
>
> **When to use:** Before writing or modifying any prompt in `pipeline/ai_client.py`, before creating system instructions, or when testing prompt variants for the indicator analysis and macro synthesis steps.

---

## 1. Provider-Specific Guidelines

### 1.1 Google Gemini (Primary — via Vertex AI)

**Current models (April 2026):**
- `gemini-3-pro-preview` — 1M context, complex reasoning, coding
- `gemini-3-flash-preview` — 1M context, fast, balanced, multimodal
- `gemini-3.1-pro-preview` — Latest, structured output + tool use

**SDK:** `google-genai` (Python) — `pip install google-genai`

> ⚠ Legacy SDKs `google-generativeai` and `@google/generative-ai` are deprecated. Use `google-genai`.

**Core principles for Gemini 3:**
1. **Be precise and direct.** State the goal clearly. Avoid filler or persuasive language.
2. **Use consistent structure.** XML tags (`<context>`, `<task>`) or Markdown headings — pick one per prompt.
3. **Prioritize critical instructions.** Place role, constraints, and output format in System Instruction or at the start.
4. **Structure for long contexts.** Supply all context first, then place instructions at the end.
5. **Anchor context.** After large data blocks, use: "Based on the information above..."
6. **Don't force CoT on reasoning models.** Gemini 3 does internal chain-of-thought. Over-prompting degrades performance.
7. **Temperature:** Keep at default 1.0 for Gemini 3. Lowering may cause loops or degraded reasoning.

**Gemini 3 structured prompting template:**
```xml
<role>
You are an economic analyst specializing in macroeconomic indicators.
</role>

<constraints>
1. Respond only in valid JSON matching the provided schema.
2. Base analysis exclusively on the provided data — no external knowledge.
3. Flag anomalies using the criteria defined in the data section.
</constraints>

<context>
{indicator_data}
</context>

<task>
Analyze the provided indicator data and produce a structured insight.
</task>
```

**Structured output (Schema-First with Pydantic):**
```python
from google import genai
from pydantic import BaseModel, Field
from typing import Literal

class IndicatorInsight(BaseModel):
    """Schema for Step 1: per-indicator analysis."""
    indicator_code: str = Field(description="World Bank indicator code")
    country_code: str = Field(description="ISO2 country code")
    trend: Literal["improving", "stable", "declining"]
    yoy_change_pct: float = Field(description="Year-over-year change %")
    is_anomaly: bool = Field(description="True if change exceeds threshold")
    narrative: str = Field(description="2-3 sentence analysis")
    confidence: Literal["high", "medium", "low"]

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_json_schema": IndicatorInsight.model_json_schema(),
    },
)
insight = IndicatorInsight.model_validate_json(response.text)
```

> **Key insight:** Gemini's structured output is schema-constrained at the token level — it is mathematically impossible for the model to violate the JSON schema. This is superior to prompt-based JSON enforcement.

### 1.2 OpenAI (Fallback — via API)

**Current approach (2026):**
- Use `response_format` with `json_schema` type and `strict: true`
- Define schemas with Pydantic (Python) or Zod (TypeScript)
- Legacy "JSON Mode" is deprecated — always use Strict Mode

**Critical differences from Gemini:**
| Aspect | Gemini | OpenAI |
|--------|--------|--------|
| Schema enforcement | `response_json_schema` | `response_format.json_schema` with `strict: true` |
| Refusal handling | Check `finish_reason` | Check `message.refusal` field |
| CoT behaviour | Internal (don't force it) | Reasoning models also have internal CoT |
| Temperature default | 1.0 (keep it) | Varies by model |

**OpenAI structured output pattern:**
```python
from openai import OpenAI
from pydantic import BaseModel

class IndicatorInsight(BaseModel):
    indicator_code: str
    trend: str
    narrative: str
    is_anomaly: bool

client = OpenAI()
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    response_format=IndicatorInsight,
)
insight = response.choices[0].message.parsed

# Always check for refusal
if response.choices[0].message.refusal:
    raise ValueError(f"Model refused: {response.choices[0].message.refusal}")
```

---

## 2. Prompt Architecture for World Analyst

### 2.1 Two-Step Chain Design

The project uses a deliberate two-step agentic chain where Pandas handles the math and the LLM writes the narrative:

```
Step 1: Per-Indicator Analysis (6 calls, parallelizable)
  Input: Statistical summary from analyser.py (YoY change, Z-scores, trend)
  Output: Structured IndicatorInsight per country-indicator pair
  Model: gemini-3-flash-preview (speed matters, 90 calls)

Step 2: Macro Synthesis (15 calls, sequential)
  Input: All 6 IndicatorInsight objects for one country
  Output: MacroSynthesis (executive summary + risk flags + outlook)
  Model: gemini-3-pro-preview (depth matters, 15 calls)
```

### 2.2 System Instruction Template (Step 1)

```
You are an economic data analyst producing structured insights for a global
economic intelligence dashboard.

Rules:
1. You receive pre-computed statistical data from Pandas. Trust the numbers.
2. Your job is NARRATIVE interpretation, not mathematical computation.
3. Flag anomalies only when the data explicitly marks them (is_anomaly=true).
4. Write for a professional audience: concise, specific, no filler.
5. Never fabricate data points. If data is missing, say so.
6. Respond exclusively in JSON matching the provided schema.

Tone: Reuters wire service — authoritative, neutral, data-driven.
```

### 2.3 System Instruction Template (Step 2)

```
You are a senior macroeconomic strategist synthesizing individual indicator
analyses into a country-level intelligence briefing.

You receive 6 structured indicator insights for a single country. Your task:
1. Identify the dominant macroeconomic narrative (e.g., stagflation, recovery).
2. Flag the top 2-3 risk factors with supporting data.
3. Write an executive summary suitable for a policy brief.
4. Assign an overall outlook: bullish, cautious, or bearish.

Rules:
- Cross-reference indicators (e.g., rising debt + weak GDP = fiscal stress).
- Be specific — cite exact figures from the input, not generalities.
- If indicators conflict, acknowledge the tension explicitly.
- Maximum 200 words for the executive summary.

AI Disclaimer: Your output will be displayed with the note "AI-generated content
may contain inaccuracies. Verify before acting."
```

---

## 3. Prompt Engineering Best Practices

### 3.1 Universal Rules (Both Providers)

1. **Schema-First, Not Prompt-First.** Define the Pydantic model before writing the prompt. The schema IS the specification.
2. **Static content at the start.** System instructions → schema → few-shot examples → variable data. This maximizes cache hits.
3. **Use delimiters.** XML tags or Markdown headings to separate instructions, context, and data. Prevents injection.
4. **Positive instructions.** "Write concisely" not "Don't be verbose."
5. **Version control prompts.** Treat prompts as code — store as `.txt` or `.py` constants with commit messages.
6. **Test on diverse inputs.** Nigeria's data patterns differ wildly from Germany's. Test both.

### 3.2 Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Fix |
|---|---|---|
| "Think step by step" on Gemini 3 | Interferes with native reasoning | Remove — let the model reason internally |
| Prompt-based JSON enforcement | Unreliable across runs | Use `response_json_schema` instead |
| Overstuffing context | Drowns the signal | Pre-filter data in Pandas, pass only the summary |
| Hardcoded model names | Breaks when updated | Use `ai_client.py` abstraction layer |
| No fallback on refusal | Silent failure | Check `finish_reason` / `message.refusal` |

### 3.3 Prompt Audit Checklist

Before a prompt goes to production:

- [ ] Does it use schema-constrained structured output (not prompt-based JSON)?
- [ ] Is the system instruction stable and cacheable?
- [ ] Is the Pydantic model defined and tested independently?
- [ ] Has it been tested on ≥3 countries with different economic profiles?
- [ ] Does it handle edge cases (missing data, all-null indicators)?
- [ ] Is the temperature at default (1.0 for Gemini, model-default for OpenAI)?
- [ ] Does the prompt avoid mathematical computation (deferred to Pandas)?
- [ ] Is the response validated with `model_validate_json()` after generation?

---

## 4. LLM-as-Judge Evaluation Framework

### 4.1 Why LLM-as-Judge?

Traditional metrics (BLEU, ROUGE) measure word overlap, not reasoning quality. For economic analysis, we need to evaluate:
- **Factual grounding:** Does the narrative cite the correct numbers from the input?
- **Anomaly correctness:** Are flagged anomalies justified by the data?
- **Cross-indicator coherence:** Does the synthesis connect related indicators?
- **Actionability:** Is the insight useful for decision-making?

### 4.2 Evaluation Dimensions

| Dimension | Weight | What It Measures |
|---|---|---|
| **Groundedness** | 30% | Every claim traces to the input data |
| **Accuracy** | 25% | Numbers, trends, and anomaly flags are correct |
| **Coherence** | 20% | Logical flow, no contradictions |
| **Specificity** | 15% | Cites exact figures, not vague generalities |
| **Conciseness** | 10% | No filler, stays within word limits |

### 4.3 LLM-as-Judge Implementation

```python
"""LLM-as-Judge evaluator for World Analyst insights.

Uses a stronger model (gemini-3-pro) to evaluate outputs from
the production model (gemini-3-flash).
"""

from google import genai
from pydantic import BaseModel, Field
from typing import Literal

class EvaluationScore(BaseModel):
    """Structured evaluation output from the judge LLM."""
    groundedness: int = Field(ge=1, le=10, description="Every claim traces to input data")
    accuracy: int = Field(ge=1, le=10, description="Numbers and trends are correct")
    coherence: int = Field(ge=1, le=10, description="Logical flow, no contradictions")
    specificity: int = Field(ge=1, le=10, description="Cites exact figures")
    conciseness: int = Field(ge=1, le=10, description="No filler, within limits")
    overall: int = Field(ge=1, le=10, description="Weighted overall score")
    reasoning: str = Field(description="Brief explanation of scores")
    passes: bool = Field(description="True if overall >= 7")


JUDGE_SYSTEM_PROMPT = """
You are a quality evaluator for an economic intelligence system.
You will receive:
1. The INPUT DATA that was given to the production model.
2. The MODEL OUTPUT that was generated.

Your task is to evaluate the model output on the dimensions below.
Score each dimension from 1-10 and provide a brief reasoning.

Dimensions:
- Groundedness (30%): Does every claim in the output trace back to the input?
- Accuracy (25%): Are numbers, trends, and anomaly flags factually correct?
- Coherence (20%): Is the narrative logically consistent?
- Specificity (15%): Does it cite exact figures, not vague statements?
- Conciseness (10%): Is it within word limits with no padding?

Calculate overall = (groundedness*0.3 + accuracy*0.25 + coherence*0.2
                   + specificity*0.15 + conciseness*0.1)
Round to nearest integer. Set passes=true if overall >= 7.
"""


def evaluate_insight(
    input_data: str,
    model_output: str,
    judge_model: str = "gemini-3-pro-preview",
) -> EvaluationScore:
    """Evaluate a single model output using LLM-as-Judge.

    Args:
        input_data: The statistical summary given to the production model.
        model_output: The JSON insight generated by the production model.
        judge_model: The model used for evaluation (should be stronger).

    Returns:
        Structured evaluation scores with pass/fail determination.
    """
    client = genai.Client()

    user_prompt = f"""
<input_data>
{input_data}
</input_data>

<model_output>
{model_output}
</model_output>

Evaluate the model output against the input data.
"""

    response = client.models.generate_content(
        model=judge_model,
        contents=user_prompt,
        config={
            "system_instruction": JUDGE_SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "response_json_schema": EvaluationScore.model_json_schema(),
        },
    )

    return EvaluationScore.model_validate_json(response.text)
```

### 4.4 Test Harness Pattern

```python
"""Prompt regression test runner.

Run with: pytest tests/test_prompts.py -v
"""

import json
import pytest
from pathlib import Path

# Golden test cases: known input → expected traits
GOLDEN_CASES = [
    {
        "name": "ZA GDP decline",
        "input_file": "tests/fixtures/za_gdp_decline.json",
        "expected_trend": "declining",
        "expected_anomaly": True,
        "min_score": 7,
    },
    {
        "name": "DE stable growth",
        "input_file": "tests/fixtures/de_stable_growth.json",
        "expected_trend": "stable",
        "expected_anomaly": False,
        "min_score": 7,
    },
    {
        "name": "NG missing data",
        "input_file": "tests/fixtures/ng_missing_data.json",
        "expected_trend": None,  # Should acknowledge missing data
        "expected_anomaly": False,
        "min_score": 6,  # Lower bar for edge case
    },
]


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda c: c["name"])
def test_prompt_quality(case):
    """Verify prompt output quality with LLM-as-Judge."""
    input_data = Path(case["input_file"]).read_text()

    # Generate insight with production prompt
    insight = generate_indicator_insight(input_data)

    # Validate schema compliance
    assert insight.indicator_code is not None
    assert insight.narrative is not None

    # Validate expected traits
    if case["expected_trend"]:
        assert insight.trend == case["expected_trend"]
    if case["expected_anomaly"] is not None:
        assert insight.is_anomaly == case["expected_anomaly"]

    # LLM-as-Judge evaluation
    score = evaluate_insight(
        input_data=input_data,
        model_output=insight.model_dump_json(),
    )

    assert score.overall >= case["min_score"], (
        f"Quality score {score.overall} < {case['min_score']}: "
        f"{score.reasoning}"
    )
```

### 4.5 Evaluation Tools Comparison

| Tool | Type | Best For | Install |
|---|---|---|---|
| **DeepEval** | Framework (OSS) | CI/CD unit tests, 14+ metrics, pytest-like | `pip install deepeval` |
| **Promptfoo** | CLI (OSS) | Prompt variant sweeps, red-teaming, Node.js | `npx promptfoo@latest` |
| **Braintrust** | Platform | Full lifecycle, team collaboration, traceability | SaaS |
| **LangSmith** | Platform | LangChain ecosystem, tracing + eval | SaaS |

**For World Analyst:** Start with the custom LLM-as-Judge pattern above (lightweight, no extra dependencies). Graduate to DeepEval when CI/CD is set up.

---

## 5. Prompt File Organisation

```
pipeline/
├── prompts/
│   ├── step1_indicator_analysis.py   # System + user prompt templates
│   ├── step2_macro_synthesis.py      # System + user prompt templates
│   ├── schemas.py                    # Pydantic models (shared)
│   └── judge.py                      # LLM-as-Judge evaluator
├── ai_client.py                      # Provider abstraction (Gemini/OpenAI)
└── tests/
    ├── test_prompts.py               # Golden test cases
    └── fixtures/                     # Sample input data per scenario
        ├── za_gdp_decline.json
        ├── de_stable_growth.json
        └── ng_missing_data.json
```

---

## 6. Quick Reference

### Temperature Settings
| Task | Gemini 3 | OpenAI | Why |
|------|----------|--------|-----|
| Structured analysis | 1.0 (default) | 0.0–0.3 | Gemini degrades below 1.0; OpenAI is fine low |
| Creative narrative | 1.0 (default) | 0.7–1.0 | Both benefit from some variance |
| Evaluation (judge) | 1.0 (default) | 0.0 | Deterministic scoring needed |

### Schema Best Practices
1. Use `Field(description=...)` on every field — this is prompt engineering inside the schema
2. Use `Literal` for enums — constrains the output space
3. Use `ge=`/`le=` for numeric bounds — prevents wild values
4. Always validate with `model_validate_json()` after generation
5. Schemas with tool use require Gemini 3.1 Pro Preview

### Prompt Versioning Convention
```
# v1.0.0 — Initial indicator analysis prompt
# v1.1.0 — Added anomaly threshold context
# v1.1.1 — Fixed Gemini 3 CoT interference (removed "think step by step")
STEP1_VERSION = "1.1.1"
```
