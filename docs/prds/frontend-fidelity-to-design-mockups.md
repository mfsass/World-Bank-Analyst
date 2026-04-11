# PRD: Frontend fidelity to design mockups

## 1. Product overview

### 1.1 Document title and version

Frontend fidelity to design mockups
Version: 0.1
Date: 2026-04-10
Status: Draft for approval

### 1.2 Product summary

World Analyst already has the beginnings of a working frontend: the route structure exists, the main pages are wired, the dashboard can read live API responses, and the design token layer is in place. What it does not yet have is the visual authority, shared shell, component discipline, and page composition shown in the finalized mockups. Right now the frontend feels like a functional local slice. The target is a coherent economic intelligence terminal.

This PRD turns the finalized design mockups into an implementation-ready frontend scope. The mockups are the visual source of truth for page composition, hierarchy, and interaction intent. The design system remains the hard implementation guardrail for tokens and rules: dark canvas, orange restraint, 8px radius, no shadows, no blur, Inter plus Commit Mono, and tonal depth only. Where the mockup HTML and the design system disagree, the design system wins.

This PRD focuses on UX and UI. It covers all four pages, the shared application shell, page-level layout parity, reusable components, interaction fidelity, and bounded polish such as feedback states, tactile controls, and smoother loading behavior. It does not own live data, live AI, or cloud runtime truthfulness, but it must create the frontend structure that those later PRDs can plug into without redesigning the product. This work can begin after the landing-dashboard baseline and does not need durable storage, live data, or cloud deployment to be complete, but the resulting page structures must remain compatible with those later integrations. Before implementation starts, the mockup HTML must be audited for design-system conflicts such as non-token spacing, shadow usage, or radius drift so the implementation team does not discover those conflicts halfway through the build.

## 2. Goals

### 2.1 Business goals

- Make the product look and feel like the intended World Analyst terminal rather than an early technical slice.
- Increase review and presentation quality by aligning the shipped frontend with the finalized mockups and the ML6-facing product brief.
- Create a frontend surface that is visually credible enough to carry the later live-data, live-AI, and cloud-runtime work.
- Reduce UX drift by establishing clear component, layout, and state-handling rules before further frontend growth.

### 2.2 User goals

- As a finance reviewer, I want the dashboard to feel intentional, dense, and trustworthy so I can scan signals quickly.
- As an ML6 evaluator, I want the frontend to reflect strong product craft rather than a generic dashboard template.
- As an engineer, I want a reusable frontend structure so later data and runtime work can slot in without rewriting the page layouts.

### 2.3 Non-goals (explicit out-of-scope)

- Replacing placeholder or local-slice data with final live-data sources.
- Replacing deterministic or provisional AI text with final live-AI quality and provider behavior.
- Making the How It Works page fully truthful to final cloud runtime behavior. That belongs to the How It Works and architecture explainability PRD and the cloud deployment, scheduling, and runtime topology PRD.
- Adding new frontend routes beyond the current four-page structure.
- Reworking the backend API contract solely for visual convenience unless a separate ADR-backed decision is made.
- Introducing Tailwind, a CSS framework, or a separate design system technology stack.

## 3. User personas

### 3.1 Key user types

- Finance reviewer using the dashboard as a macro-risk terminal.
- ML6 evaluator assessing end-to-end product quality, design discipline, and presentation readiness.
- Engineer implementing and maintaining the React frontend against the existing API.

### 3.2 Basic persona details

- Finance reviewer: expects dense, legible layouts, fast scanning, clear hierarchy, and credible status feedback. They do not need consumer-style onboarding.
- ML6 evaluator: cares about whether the frontend looks deliberate, consistent, and aligned with the architecture story rather than assembled from templates.
- Engineer: needs a component and layout structure that keeps styling, state handling, and page composition maintainable as the product evolves.

### 3.3 Role-based access (if applicable)

- No new role model is introduced in this PRD.
- The current authenticated product surface remains the working assumption.
- Navigation, page shell, and UI states are shared across all current users.

## 4. Functional requirements

- **Shared application shell** (Priority: High)
  - The frontend must implement a consistent top navigation and footer across the four-page experience.
  - Active route state, shared labels, responsible-AI messaging, and page spacing must remain consistent across the app.
  - The shell must support desktop and smaller-screen fallback layouts without becoming visually fragile or introducing duplicate navigation systems.

- **Design-system enforcement** (Priority: High)
  - All frontend implementation must follow the World Analyst design system and existing token layer.
  - The mockups define composition and interaction intent, but the design system defines implementation rules for color usage, spacing, radius, borders, typography, and depth.
  - Styling must remain based on React plus vanilla CSS and CSS custom properties.
  - Before implementation starts, each mockup page must be checked for conflicts with the design system. If a conflict changes a meaningful design choice, it must be logged as an implementation note or ADR before code is written.

- **Reusable frontend component structure** (Priority: High)
  - Repeated interface patterns must be implemented as reusable components rather than duplicated per page.
  - A pattern should only become a shared component when it appears in at least two pages or when it materially clarifies ownership of the shared shell.
  - The component layer must at minimum support navigation chrome, KPI cards, AI insight panels, and status pills. Terminal panels and execution-step cards may stay page-local unless duplication is proven.
  - Page files should become composition layers rather than owning all visual structure directly.

- **Global Overview mockup fidelity** (Priority: High)
  - The landing page must implement the mockup's macro scanning structure: hero AI insight area, anomaly banner, executive KPI row, map-led risk overview, regional breakdown, and market depth section.
  - The map must support point-based drill-in so a reviewer can click a market, read a compact summary, and move directly into the country page.
  - Empty, loading, and failed states must remain intentional rather than collapsing into generic cards.

- **Country Intelligence mockup fidelity** (Priority: High)
  - The country page must implement the mockup's deep-dive structure: breadcrumb, market switcher, elevated AI analyst summary, country identity block, KPI row, current risk signal pack, and risk or outlook surfaces.
  - Historical charts are optional in this phase and should only appear when they add real value instead of reserving placeholder space.
  - Country switching controls and analyst panels must feel like part of a coherent terminal, not isolated widgets.

- **How It Works mockup fidelity** (Priority: Medium)
  - The architecture page must implement the intended visual structure: live pipeline CTA, telemetry row, architecture diagram area, input versus output comparison, prompt strategy, and technical spec strip.
  - This PRD owns the visual container, layout fidelity, and UX clarity for the page, not the final truthfulness of every metric or architecture claim.
  - Any placeholder or illustrative content on this page must be visibly controlled and easy to replace in later PRDs.
  - The page structure must not need to be reworked when the How It Works and architecture explainability PRD replaces placeholders with truthful content.

- **Pipeline Trigger mockup fidelity** (Priority: High)
  - The trigger page must implement the intended showcase layout: KPI row, strong trigger CTA, execution sequence, and terminal panel.
  - The page must represent running, complete, idle, failed, and pending states with clear visual differences aligned to the design system.
  - Trigger feedback should feel responsive and controlled, including loading protection, disabled states, and post-run navigation affordances.

- **Interaction fidelity and bounded polish** (Priority: Medium)
  - The frontend must implement the key interaction cues implied by the mockups, including hover states, active pills, selected navigation items, button feedback, and status transitions.
  - Optimistic or near-immediate feedback is encouraged where it improves perceived responsiveness without misrepresenting backend state.
  - Motion and interactivity must remain purposeful and restrained rather than decorative.
  - Allowed polish is limited to token-based hover, focus, active, and state transitions of 200ms or less. Decorative entrances, long-running animations, blur, and shadow-based effects remain out of scope.

- **State completeness across the four pages** (Priority: High)
  - Each page must define intentional loading, empty, ready, running, and failure states where relevant.
  - The UI must never fall back to unstyled raw error output or visually broken partial states.
  - Where API-served or provider-backed content is not yet available, placeholder or interim content must still preserve the final page structure.

- **Responsive presentation quality** (Priority: Medium)
  - The frontend must work well on desktop and remain usable on smaller screens.
  - Desktop remains the presentation-first target, but mobile and tablet layouts must not break the shell, typography, or main content flow.
  - The primary audit breakpoints are 1440px, 768px, and 375px.
  - The top-level shell, dense tables, and map or terminal surfaces must have clear fallback behavior on reduced screen widths: navigation collapse, KPI reflow, and scroll or aspect-ratio preservation for dense visual surfaces.

## 5. User experience

### 5.1 Entry points and first-time user flow

A reviewer lands on the dashboard and immediately sees a product surface that feels finished: strong navigation, a credible hero state, structured KPIs, and clear pathways into the country, pipeline, and architecture views. The user should not need explanation to understand that this is an economic intelligence terminal with a live workflow behind it.

### 5.2 Core experience

The product should support two main behaviors. The first is macro scanning: the user reads the global overview, identifies a risk signal, and opens a country page. The second is demo validation: the user opens the trigger page, starts or monitors a run, and then returns to inspect the updated dashboard. Across both flows, the shell, component language, and state feedback should feel consistent and deliberate.

### 5.3 Advanced features and edge cases

If API-served content is not yet materialized, the page should still preserve the intended structure and show a controlled empty or pending state rather than collapsing into minimal placeholder blocks. If data is loading, the page should provide feedback that fits the terminal feel. If a trigger call fails, the interface should surface that clearly while keeping the rest of the page legible. If charts, maps, or telemetry are still partly illustrative in this phase, the UI should make room for later real data without redesign.

### 5.4 UI and UX highlights

- The mockups are the visual reference for composition, density, and hierarchy.
- The design system remains the implementation rulebook.
- The app should feel like one cohesive terminal rather than four separate pages.
- Interactions should feel tactile and confident through stateful buttons, active navigation, selected pills, and clear status styling.
- The responsible-AI disclaimer remains visible and consistent.

## 6. Narrative

World Analyst should look like the product it claims to be. This PRD closes the gap between a technically functional frontend and a review-ready analyst terminal. It uses the finalized mockups as visual direction, preserves the design system as the implementation guardrail, and introduces the shared shell, reusable components, and page-level structure needed to make the product visually credible before the deeper live-data and cloud-runtime phases land.

## 7. Success metrics

### 7.1 User-centric metrics

- A first-time reviewer can understand the product structure and navigate between the four pages without guidance.
- The frontend communicates loading, running, complete, failed, and empty states clearly without generic placeholder UX.
- The product feels visually cohesive across all pages rather than assembled incrementally.

### 7.2 Business metrics

- The shipped frontend is recognizably aligned with the finalized mockups and the World Analyst design language.
- The visual quality strengthens demo and review impact without requiring a new frontend redesign later.
- The product presentation supports the ML6 evaluation story of end-to-end product engineering, not just backend competence.

### 7.3 Technical metrics

- Shared navigation chrome and common UI patterns are implemented as reusable React components.
- All styling remains within the existing React plus vanilla CSS approach and uses CSS custom properties.
- The four current routes render high-fidelity layouts without adding route sprawl.
- Frontend lint and build continue to pass after the UI refactor.
- The page structure is ready for later live-data, live-AI, and cloud-runtime integration without major layout replacement.
- A manual QA checklist passes at 1440px, 768px, and 375px for navigation, layout integrity, and visible state handling.
- New shared components avoid hardcoded color and spacing values outside the token system.

## 8. Technical considerations

### 8.1 Integration points

- Route structure and app composition in `frontend/src/App.jsx`.
- Shared styling and tokens in `frontend/src/index.css`.
- Page implementations in `frontend/src/pages/GlobalOverview.jsx`, `frontend/src/pages/CountryIntelligence.jsx`, `frontend/src/pages/HowItWorks.jsx`, and `frontend/src/pages/PipelineTrigger.jsx`.
- Existing frontend API integration in `frontend/src/api.js`.
- Frontend build configuration in `vite.config.js` and environment-specific API base URL handling aligned with ADR-023 and the cloud deployment PRD.
- Design references in `docs/design-mockups/Global Overview Finalized.html`, `docs/design-mockups/Country Intelligence Finalized.html`, `docs/design-mockups/How It Works Finalized.html`, `docs/design-mockups/Pipeline Trigger Finalized.html`, and `docs/design-mockups/Design System.md`.

### 8.2 Data storage and privacy

- This PRD does not introduce new storage requirements.
- The frontend should continue to consume the existing API without requiring sensitive data in the client bundle beyond the current development assumptions.
- Placeholder or illustrative content on the UI should not imply the existence of stored data that the backend does not actually provide.

### 8.3 Scalability and performance

- The component structure should reduce duplication and make future frontend changes cheaper.
- Layout fidelity should not depend on heavyweight libraries unless they are clearly justified by an existing planned surface such as charts or maps.
- Static SVG or lightweight placeholder implementations are acceptable for charts and maps in this phase if they preserve the final page structure without forcing premature library choices.
- This PRD optimizes for product fidelity and maintainable frontend structure, not premature frontend complexity.

### 8.4 Potential challenges

- The mockup HTML is a visual artifact, not implementation-ready code, and some details will need to be translated into the stricter repo design system.
- The current frontend lacks a reusable component layer, so visual fidelity work will also require structural cleanup.
- Some mockup surfaces imply richer live data than the current backend provides, so placeholder policy must be explicit.
- The boundary between frontend fidelity and architecture truthfulness must stay clear, especially on the How It Works page.
- Recreating polish without slipping into decorative motion, shadow usage, or generic dashboard patterns will require discipline.
- The first implementation task must include a mockup audit that flags any design-system conflicts before coding starts.

## 9. Milestones and sequencing

### 9.1 Project estimate

This is a medium-sized frontend foundation PRD. It is larger than a styling pass because it includes shell architecture, component extraction, page composition, interaction states, and responsive behavior, but it remains bounded because it does not own live-data or runtime truthfulness.

### 9.2 Team size and composition

- One implementation lane covering shell, components, page fidelity, and state treatment.
- One review lane checking design-system drift, mockup fidelity, interaction completeness, responsive behavior, and frontend maintainability.

### 9.3 Suggested phases

0. Before implementation kickoff, audit the mockups against the design system and record any meaningful conflicts before code changes begin.
1. Finalize the shared shell, page scaffolding, and reusable component inventory.
2. Implement Global Overview and Country Intelligence fidelity with live-compatible states.
3. Implement the visual structure of How It Works with controlled placeholder policy. This phase owns the container and layout only; the How It Works and architecture explainability PRD owns the final architecture claims, examples, and telemetry truthfulness.
4. Implement Pipeline Trigger as the presentation centerpiece, then audit any new UI patterns before deciding whether they become shared components.
5. Audit responsive behavior, interaction polish, token compliance, and the manual QA checklist across all pages.

## 10. User stories

### 10.1 Build a shared terminal shell

- **ID**: US-1
- **Description**: As a reviewer, I want the app to have a consistent terminal-like shell so that the product feels coherent across all four pages.
- **Acceptance criteria**:
  - [ ] The frontend renders a shared top navigation and footer across the four existing routes.
  - [ ] Active route state is visually clear in the shared navigation without a second competing nav surface.
  - [ ] The shared shell passes a design-system checklist covering canvas color, border treatment, 8px radius, typography, and spacing rhythm.

### 10.2 Match the Global Overview composition

- **ID**: US-2
- **Description**: As a finance reviewer, I want the landing page to match the intended macro-scanning layout so that I can assess overall signals quickly.
- **Acceptance criteria**:
  - [ ] The page includes a hero AI insight area, anomaly banner, executive KPI row, map-led risk section, regional breakdown, and market depth section.
  - [ ] The map supports click-to-open market summaries with a direct path into country intelligence.
  - [ ] The page preserves intentional loading, empty, ready, and failure states without collapsing into generic placeholder blocks.
  - [ ] API-backed content can populate the layout without changing the page structure.
  - [ ] The implemented page matches the section structure shown in the Global Overview mockup without introducing non-token colors, spacing, or shadow effects.

### 10.3 Match the Country Intelligence composition

- **ID**: US-3
- **Description**: As a finance reviewer, I want the country page to present a clear deep-dive layout so that I can move from high-level signal to detailed country interpretation.
- **Acceptance criteria**:
  - [ ] The page includes breadcrumb context, market switcher, elevated AI analyst summary, country identity block, KPI row, current risk signal pack, and risk or outlook section.
  - [ ] Country switching controls and KPI presentation follow the visual language of the mockups and design system.
  - [ ] The page can render meaningful empty or pending states when full live content is not yet materialized.
  - [ ] The page preserves a strong narrative-first hierarchy without reserving placeholder chart space when live history visuals are not yet ready.

### 10.4 Turn the Pipeline Trigger page into the showcase surface

- **ID**: US-4
- **Description**: As an evaluator, I want the trigger page to look and feel like a deliberate live execution console so that the demo proves the product works.
- **Acceptance criteria**:
  - [ ] The page includes a KPI status row, strong trigger CTA, execution-step area, and terminal panel matching the intended layout.
  - [ ] Idle, running, complete, failed, and pending states are visually distinct and consistent with the design system.
  - [ ] Trigger controls provide clear disabled, loading, and post-run feedback without allowing accidental duplicate submissions.

### 10.5 Implement the visual structure of How It Works

- **ID**: US-5
- **Description**: As an ML6 evaluator, I want the architecture page to have a clear explanatory layout so that the product communicates engineering intent even before the final truthfulness pass.
- **Acceptance criteria**:
  - [ ] The page includes a live pipeline CTA area, telemetry strip, architecture diagram region, input versus output comparison, prompt strategy section, and technical spec strip.
  - [ ] Placeholder or illustrative content is used in a controlled way and does not block later explainability work.
  - [ ] The page follows the same shell and design language as the rest of the product.
  - [ ] The page structure can receive the truthful content owned by the How It Works PRD without requiring a structural rewrite.

### 10.6 Introduce reusable UI building blocks

- **ID**: US-6
- **Description**: As an engineer, I want recurring frontend patterns extracted into reusable components so that the UI can evolve without duplicating page logic and styling.
- **Acceptance criteria**:
  - [ ] A pattern is promoted to a shared component only when it appears in at least two pages or materially clarifies ownership of the shared shell.
  - [ ] KPI cards, AI insight panels, navigation chrome, and status pills are implemented as shared components.
  - [ ] Terminal panels and execution-step cards remain page-local unless duplication is proven by implementation.
  - [ ] Page files primarily compose shared components rather than duplicating the same visual structures inline.
  - [ ] Shared components use the existing design token system rather than hardcoded one-off visual values.

### 10.7 Preserve fidelity on smaller screens

- **ID**: US-7
- **Description**: As a user opening the app on a smaller screen, I want the interface to remain usable so that the product still reads cleanly outside the primary desktop demo view.
- **Acceptance criteria**:
  - [ ] The top-level shell, page headers, KPI rows, and primary content regions remain readable at 1440px, 768px, and 375px.
  - [ ] The top-level shell, dense tables, and map or terminal regions have defined fallback behavior for smaller screens, including navigation collapse and scroll or aspect-ratio preservation for dense visual surfaces.
  - [ ] Responsive adjustments preserve the design system rather than introducing a separate visual language.
