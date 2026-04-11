---
name: Frontend Design Rules
description: "Use when editing frontend/src so components stay aligned with the World Analyst design system and React conventions."
applyTo: frontend/src/**
---

- Preserve the design system: `#0E0E0E` canvas, `#1A1A1A` cards, `#FF4500` primary accent, `8px` radius, no shadows, no blur.
- Use CSS custom properties and existing tokens instead of hardcoding new visual values in components.
- Prefer functional components and named exports that keep `pages/` route-level and `components/` reusable.
- Add concise comments when derived state, polling, or data orchestration would otherwise be difficult to follow during review.
- Keep UI changes consistent with [Design Mockups/Design System.md](../../Design%20Mockups/Design%20System.md).
- Use [world-analyst-design-system](../skills/world-analyst-design-system/SKILL.md) for any meaningful UI or CSS change.
