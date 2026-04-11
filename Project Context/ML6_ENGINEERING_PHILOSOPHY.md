# ML6 — Engineering Philosophy & Way of Working

**Document Type:** Background Intelligence File  
**Purpose:** Understanding ML6's actual engineering culture — how they think about AI-assisted development, what they value in engineers, and what vocabulary they use internally  
**Source:** "Balancing Speed and Quality in AI-Native Engineering" — Georges Lorré, ML6 (Feb 2026)  
**Last Updated:** April 2026

---

## Overview

ML6 has a formally articulated engineering philosophy they call the **AI Native Way of Working (WoW)**. This is not aspirational — it is the internal operating standard they hold themselves and their hires to.

The core thesis: AI-native engineering is not about maximum velocity. It is about **disciplined, intent-driven development** where humans remain accountable for every decision the AI makes.

This document captures their published principles, vocabulary, and the friction points they have observed in practice — all directly relevant to how the World Analyst challenge will be evaluated.

---

## The Core Problem ML6 Has Identified

As AI tools increase development speed, teams hit a predictable set of failure modes:

**Review Overload**  
Senior engineers become "human compilers" — reviewing AI-generated pull requests faster than they can safely understand them. They spend more time reverse-engineering the AI's logic than they would have spent writing the feature themselves.

**Shared Context Collapse**  
The "why" behind code disappears when AI generates it. Without the "why," the review process becomes circular and exhausting. Reviewers become detectives, not mentors.

**Knowledge Atrophy**  
Junior engineers skip the mental struggle that builds deep understanding. They can produce working code they cannot explain. This is what ML6 calls the "superficial comprehension trap."

**The Productionization Gap**  
AI generates polished UIs fast, creating the optical illusion that a project is 90% done. In reality, the hard foundational work (cloud infrastructure, logging, databases) hasn't started. Projects built on "vibe coding" require significant refactoring before they can ship as enterprise-grade products.

---

## ML6's Internal Vocabulary

Understanding these terms is essential for communicating fluently with ML6 engineers:

| Term | Meaning |
|---|---|
| **AI Native WoW** | AI Native Way of Working — ML6's engineering operating model |
| **Intent-First Development** | Defining the "why" and trade-offs before generating any code |
| **PaperTrail** | Lightweight, version-controlled context files (agent.md, README.md) that make intent visible |
| **Visible Intent** | Moving context from private LLM chats into the codebase itself |
| **Spec-Driven Development (SDD)** | Defining the spec before prompting the AI — intent lives alongside code |
| **Absolute Ownership** | Every developer is responsible for every line they commit, regardless of who generated it |
| **Business-Driven Testing** | Tests driven by business requirements, not coverage metrics |
| **Review Overload** | When AI velocity outpaces human review capacity |
| **Knowledge Atrophy** | Skill degradation from blindly accepting AI output |
| **Superficial Comprehension** | Shipping code you cannot explain or defend |
| **Productionization Gap** | The gap between a working UI prototype and a production-ready system |
| **Vibe Coding** | Generating code without making architectural decisions — ML6's term for what they do NOT do |
| **Human Compilers** | What senior engineers become when review discipline breaks down |
| **Context Fatigue** | Senior engineers exhausted from reverse-engineering AI logic instead of doing real engineering |
| **Software Factory** | Traditional linear model: analyst → developer → QA; context lost at each handover |
| **Software Studio** | ML6's preferred model: cross-pollinated team where functional and technical roles overlap |
| **Black Box Effect** | Critical context lost in ephemeral LLM chats; the risk that Visible Intent prevents |

---

## The Four Principles (ML6's WoW)

### 1. Intent-First Development

Before a single line of code is generated, the engineer must align with the team on the "why" and the trade-offs of the chosen solution.

This is not a heavy bureaucratic process. It is making the decision-making process visible. By the time prompting starts, the implementation should be a predictable result of a well-defined plan.

**What this means for World Analyst:**  
The `WORLD_ANALYST_PROJECT.md` file IS the intent document. The architectural decisions (Firestore vs BigQuery, two-step prompt chain, Connexion's OpenAPI-first contract) are documented BEFORE the build. This is Spec-Driven Development in practice.

### 2. Building a PaperTrail of Context

Use lightweight, version-controlled context files to define the spec before prompting. The "why" must live alongside the code.

ML6 specifically mentions `agent.md` and `README.md` as the vehicles for this. The README.md that ships with the World Analyst project is not documentation written after the fact — it is the spec that guided the build. That distinction is worth making explicit in the presentation.

**What this means for World Analyst:**  
The `README.md` justifying Firestore, Connexion, `europe-west1`, and the two-step prompt architecture is a direct implementation of ML6's PaperTrail principle. This is not a coincidence — it should be named as such.

### 3. Absolute Ownership

There is no such thing as "AI-generated throwaway code" at ML6. If you cannot explain a line and defend it, you cannot ship it.

**What this means for World Analyst:**  
Every architectural choice in this project must be explainable and defensible. The Q&A session is where ML6 tests this. The "why" answers — for Firestore, for Connexion, for the prompt chain structure — should be prepared and delivered without hesitation.

### 4. Business-Driven Testing

AI can write test code, but the intent of every test must come from a deep understanding of the client's problem. Tests exist to prove business requirements are met, not to inflate coverage metrics.

**What this means for World Analyst:**  
If tests are included in the project, they should test what the business cares about: does the pipeline correctly detect an anomaly? Does the AI narrative include a risk flag when GDP drops beyond a threshold? Not just "does the function return 200."

---

## The New Shape of the Team (Software Studio Model)

ML6 believes the strict wall between "Technical" and "Functional" roles is dissolving. Their preferred model:

**Software Factory (old model):**  
Analyst writes ticket → Developer builds → QA tests. Linear. Context lost at every handover.

**Software Studio (ML6's model):**  
- Functional profiles become more technical (can prototype and validate with natural language prompting)
- Technical profiles become more functional (must understand business intent to guide the AI correctly)
- Focus is on collaborative design, not ticket handover

**Implication:** An engineer who can translate between technical architecture and business stakeholder communication is exactly what ML6 values. The World Analyst presentation should demonstrate this fluency — not just "here is the tech stack" but "here is the business problem this solves, and here is how each technical decision serves that outcome."

---

## What ML6 Actually Evaluates in Engineers

Based on their published WoW and the role requirements, ML6 evaluates against these criteria:

**Can you explain the "why"?**  
Not just what you built — why you made each decision and what the trade-offs were.

**Do you understand the business problem?**  
Can you translate technical capability into business value for non-technical stakeholders?

**Can you own your output?**  
Every decision should be defensible. Uncertainty is fine; not knowing why you made a choice is not.

**Do you use AI deliberately, not blindly?**  
AI is an accelerator, not a substitute for reasoning. The structure of your prompts, your chain design, and your validation of AI output all signal engineering maturity.

**Can you think about adoption, not just implementation?**  
Building a system is not enough. Ensuring the system can be understood, used, and maintained by the team is the harder, more valuable part.

---

## The AI Native WoW Team — Internal Context

The AI Automation Engineer role sits within ML6's **Incubation unit**. The WoW Team is an internal consultancy — they identify automation opportunities across ML6's business units (Sales, Engineering, Finance) and build the systems to capture them.

This is not a client-facing engineering role in the traditional sense. It is internal product engineering for ML6 itself. The "client" is ML6's own operations.

This distinction matters: the candidate is being evaluated on whether they can operate as an internal consultant — someone who understands the business deeply enough to identify what to automate, not just someone who can execute a spec.

---

## The Blog Author's Own Words (Key Quotes)

These are ML6's exact phrases, paraphrased to avoid copyright reproduction:

On the core tension: AI moves at the speed of light; understanding still moves at the speed of thought.

On their standard: Quality engineering isn't an afterthought — it's the core of how we build.

On accountability: If you can't explain it and defend it, you can't ship it.

On their goal: They are not chasing the highest velocity. They are building for stable, safe, enterprise-grade outcomes.

---

## How This Maps to the World Analyst Challenge

| ML6 Principle | World Analyst Implementation |
|---|---|
| Intent-First Development | Architecture decisions documented in `WORLD_ANALYST_PROJECT.md` before a line of code is written |
| PaperTrail of Context | `README.md` justifies every architectural choice; this file and others are the context trail |
| Absolute Ownership | Every decision (Firestore, Connexion, europe-west1, two-step prompt chain) must be defended without notes |
| Business-Driven Testing | Pipeline tests validate business outcomes, not function signatures |
| Visible Intent | The "How It Works" pipeline page externalises the AI's reasoning chain for any reviewer to inspect |
| Avoiding Vibe Coding | Pandas handles quantitative analysis before the LLM receives data — the AI reasons over facts, not raw numbers |
| Productionization Gap awareness | Cloud Run, Secret Manager, Connexion OpenAPI spec — production infrastructure applied to a demo context |

---

*This file is background context for the World Analyst build and presentation.*  
*Source: ML6 blog — "Balancing Speed and Quality in AI-Native Engineering" by Georges Lorré, February 2026*
