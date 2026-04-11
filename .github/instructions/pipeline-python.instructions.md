---
name: Pipeline Rules
description: "Use when editing Python files under pipeline/ so data processing, LLM calls, and storage responsibilities stay separated."
applyTo: pipeline/**/*.py
---

- Keep responsibilities explicit: World Bank fetching in `fetcher.py`, math in `analyser.py`, model abstraction in `ai_client.py`, persistence in `storage.py`.
- Pandas should calculate trends and anomalies before the LLM writes narrative text.
- Keep provider-specific LLM details inside `ai_client.py`; callers should depend on stable interfaces.
- Persist processed insights to Firestore and raw backups to GCS only.
- Add concise inline comments where pipeline orchestration, business rules, or data-shaping decisions would otherwise be hard to explain from the code alone.
- Use [world-bank-api](../skills/world-bank-api/SKILL.md), [llm-prompting-and-evaluation](../skills/llm-prompting-and-evaluation/SKILL.md), and [world-analyst-engineering](../skills/world-analyst-engineering/SKILL.md) when changing pipeline behavior.
