# PRD: How It Works and architecture explainability

## 1. Product overview

### 1.1 Document title and version
How It Works and architecture explainability
Version: 0.1
Date: 2026-04-10
Status: Draft for approval

### 1.2 Product summary
World Analyst needs one place where the technical argument is clear enough for a reviewer to understand the system quickly and challenge it intelligently. That place is the How It Works page. Right now that page is still a placeholder, which means one of the most important product surfaces does not yet explain the core things the challenge is actually evaluating: push-based data flow, the split between statistical analysis and LLM reasoning, durable storage boundaries, and the thinking behind the architecture choices.

This PRD defines the explainability layer for World Analyst. Its main output is the How It Works page, supported by tightly bounded alignment with review-facing documentation where needed. The page should explain the current system honestly, show the intended target architecture where that target is already committed in adjacent PRDs, and make the reasoning behind key decisions easy to follow. It must not overcomplicate the product with a fake observability console or inflated technical claims. It should make the real system legible.

This PRD follows a simple rule: every architecture claim shown on the page must either map to a real part of the codebase or be clearly presented as a planned target owned by another approved PRD. The page should help a reviewer understand what exists now, what comes next, and why the system is shaped this way.

## 2. Goals

### 2.1 Business goals
- Make the product's technical story clear, defensible, and easy to present in an ML6 review.
- Turn the How It Works page into a real product asset rather than a placeholder or decorative architecture diagram.
- Increase trust by making key design decisions explicit instead of leaving them buried in code or ADRs.
- Support later live-data, live-AI, and cloud-runtime phases without forcing another rewrite of the explanation layer.

### 2.2 User goals
- As an ML6 evaluator, I want to understand the system quickly so I can see that the engineering choices are deliberate.
- As a finance reviewer, I want a clear high-level explanation of how the dashboard is produced without reading backend code.
- As an engineer, I want the explanation layer to stay truthful and easy to maintain as the system evolves.

### 2.3 Non-goals (explicit out-of-scope)
- Rebuilding the visual shell or page layout beyond what is already owned by the frontend-fidelity PRD.
- Making the cloud runtime fully real. That belongs to the cloud deployment, scheduling, and runtime topology PRD.
- Replacing placeholder data with final live data. That belongs to the Live data integration PRD.
- Replacing provisional AI output with final provider behavior. That belongs to the Live AI integration PRD.
- Building a full telemetry, tracing, or observability platform.
- Writing a full README overhaul or presentation deck as part of this phase.
- Explaining every internal implementation detail on the page. The goal is clarity, not exhaustiveness.

## 3. User personas

### 3.1 Key user types
- ML6 evaluator reviewing the solution for architecture quality and agentic thinking.
- Finance reviewer wanting a credible high-level explanation of how the intelligence is produced.
- Engineer maintaining the page and keeping it aligned with the real system.

### 3.2 Basic persona details
- ML6 evaluator: wants concise but defensible explanation of system design, trade-offs, and runtime flow.
- Finance reviewer: wants to understand the chain from raw data to analyst output without getting lost in implementation trivia.
- Engineer: needs a page and supporting copy that stay synchronized with the actual repo and adjacent PRDs.

### 3.3 Role-based access (if applicable)
- No new role model is introduced in this PRD.
- The explanation layer is part of the shared product surface available to current users.
- Operator-only cloud tooling remains outside the frontend.

## 4. Functional requirements

- **Architecture narrative surface** (Priority: High)
  - The How It Works page must explain the end-to-end system flow from World Bank data fetch through analysis, AI synthesis, persistence, API serving, and frontend display.
  - The explanation must remain readable to a non-specialist reviewer without flattening the real architecture into vague marketing copy.
  - The page must help a reviewer understand the product in a few minutes.

- **Current-state versus target-state clarity** (Priority: High)
  - The page must distinguish between what exists now and what is part of the approved target architecture.
  - If a target-state element is shown before implementation is complete, it must be clearly framed as planned and traceable to an approved PRD.
  - The page must avoid presenting future architecture as already live.

- **Claim-to-code or claim-to-plan traceability** (Priority: High)
  - Every architecture claim presented on the page must map either to a real implementation boundary in the codebase or to a later approved PRD.
  - In implementation, each architecture section must cite its source of truth in adjacent code comments or content notes by file path, ADR number, or later PRD so a reviewer can trace the claim within two navigation steps.
  - Traceability should be implemented as inline JSX comments in `HowItWorks.jsx` or a structured content manifest co-located with the page component.
  - The explanation layer must be maintainable by tying claims to stable concepts such as pipeline stages, repository boundaries, and service responsibilities.
  - The page should not invent technical layers that do not exist in code or planning.

- **Two-step AI chain explainability** (Priority: High)
  - The page must explain the difference between statistical analysis and LLM reasoning.
  - It must explain the two-step chain clearly: per-indicator analysis first, macro synthesis second.
  - It must explain why that structure is used instead of a single-pass prompt in language suitable for review and Q&A.

- **Architecture decision visibility** (Priority: High)
  - The page must make the important design choices legible at a high level: push not pull, Firestore plus GCS roles, Connexion/OpenAPI-first API design, and the separation between pipeline execution and dashboard serving.
  - It must explain why those choices were made, not just list the components.
  - The explanations must stay short and specific rather than reading like a long architecture document.

- **Truthful telemetry and examples** (Priority: Medium)
  - Telemetry-style numbers, pipeline timings, or architectural metrics shown on the page must be truthful where the underlying system supports them.
  - Where the system does not yet support live values, the page may use clearly labeled illustrative placeholders only if they are easy to replace and do not misrepresent system maturity.
  - This PRD must not introduce telemetry collection, metrics aggregation, or log parsing just to populate the page. Frontend fidelity may use visibly controlled placeholders for layout, but this PRD owns the final decision on whether a metric or claim is truthful enough to ship or must remain labeled as illustrative.
  - Example input and output blocks must be representative of the real system contracts and data flow.

- **How It Works page content structure** (Priority: High)
  - The page must include a clear architecture flow, prompt strategy section, input/output explanation, and technical responsibility breakdown.
  - The page must support the visual structure already owned by the frontend-fidelity PRD.
  - The content structure should help the reviewer move from high-level system shape to specific design choices without friction.

- **Documentation alignment** (Priority: Medium)
  - Key claims on the How It Works page must remain consistent with the project brief, ADRs, and the architecture sections of `Project Context/WORLD_ANALYST_PROJECT.md`.
  - Supporting documentation edits are limited to `docs/DECISIONS.md` and the relevant architecture sections of `Project Context/WORLD_ANALYST_PROJECT.md` when contradiction would otherwise remain visible.
  - If alignment would require changes to more than three supporting files or a broad README rewrite, that work must be split out.

- **Simplicity and proportionality** (Priority: High)
  - The explanation layer must keep the architecture legible and proportional to the challenge scope.
  - The page must avoid fake complexity, decorative telemetry, or enterprise-style explanation patterns that the product does not need.
  - The content should make the code easier to understand, not compensate for confusing code structure.

## 5. User experience

### 5.1 Entry points and first-time user flow
A reviewer opens the How It Works page from the main navigation and immediately sees a concise explanation of the pipeline. They should understand what data enters the system, what the code does to it, where AI is used, where results are stored, and how the dashboard is ultimately fed. The page should feel like a guided walkthrough of the product rather than a wall of technical text.

### 5.2 Core experience
The page should answer four questions in order. First: where does the data come from. Second: how is it processed before AI sees it. Third: how does the two-step AI chain work. Fourth: where does the result go and how does the user see it. Once those are clear, the page should make the major design decisions easy to scan so the reviewer can connect implementation choices to product goals.

### 5.3 Advanced features and edge cases
If parts of the target architecture are still pending later PRDs, the page should still present the intended direction without implying it already exists, for example Cloud Run Job execution owned by the cloud deployment PRD or live provider-backed AI behavior owned by the live AI integration PRD. If runtime metrics are not yet live, the interface should prefer clear labels and controlled placeholders over invented precision. If the implementation evolves, the page structure should make it easy to update one section without rewriting the whole narrative.

### 5.4 UI and UX highlights
- The page should feel like technical explanation, not marketing copy.
- The two-step AI chain should be one of the clearest and strongest elements on the page.
- Input and output examples should make the system concrete.
- The architecture flow should show responsibility boundaries cleanly.
- The page should reduce reviewer questions by answering likely architecture challenges before they are asked.

## 6. Narrative

World Analyst does not need a flashy architecture page. It needs a truthful one. This PRD turns the How It Works surface into the place where the product explains itself clearly: raw data in, analysis and AI reasoning in the middle, durable storage and API serving underneath, and a dashboard on top. It also makes the reasoning behind those choices visible, so the system can be defended by someone reading the product rather than only by someone who built it.

## 7. Success metrics

### 7.1 User-centric metrics
- A reviewer can understand the system flow from source data to dashboard output in one page visit.
- A reader can tell which parts of the architecture are current versus planned.
- The page reduces confusion about where AI is used and what the code does before the LLM step.

### 7.2 Business metrics
- The product is easier to present and defend in an ML6-style review.
- The architecture story aligns with the challenge brief and project brief rather than drifting into generic platform language.
- The How It Works page becomes a meaningful differentiator instead of a placeholder.

### 7.3 Technical metrics
- Claims on the page remain consistent with the codebase and approved PRDs.
- Example input and output representations align with real or planned system contracts.
- The page content can evolve without large structural rewrites as later PRDs land.
- Frontend implementation of the page remains clear enough that the explanation content is easy to maintain.

## 8. Technical considerations

### 8.1 Integration points
- How It Works page implementation in `frontend/src/pages/HowItWorks.jsx`.
- Shared shell and visual structure from the frontend-fidelity PRD.
- Pipeline orchestration and stage boundaries in `pipeline/main.py`.
- Storage responsibilities in `pipeline/storage.py` and shared repository adapters.
- API contract and serving model in `api/openapi.yaml`, `api/app.py`, and relevant handlers.
- Architecture guidance and review story in `Project Context/WORLD_ANALYST_PROJECT.md` and `docs/DECISIONS.md`.

### 8.2 Data storage and privacy
- The page should explain Firestore and GCS roles accurately at a product level.
- Example payloads or architecture explanations must not expose secrets or imply sensitive client-side behavior.
- The explanation layer should describe storage boundaries without leaking operational detail that the UI does not need.

### 8.3 Scalability and performance
- This PRD optimizes for clarity and maintainability, not dynamic documentation complexity.
- Architecture explanation should stay simple enough that it can be maintained alongside the code.
- Live metrics or dynamic explanatory content should only be introduced when they reduce confusion rather than add moving parts.

### 8.4 Potential challenges
- The mockup encourages a visually rich explanation page, but the product still needs truthfulness over spectacle.
- Some target architecture elements are approved but not yet implemented, so the page must handle staged maturity carefully.
- It is easy to drift into either oversimplification or unnecessary technical detail; this PRD has to stay between those extremes.
- The page must stay aligned with later PRDs as live data, live AI, and cloud runtime capabilities become real.

## 9. Milestones and sequencing

### 9.1 Project estimate
This is a medium-sized explanation and content-architecture PRD. It is smaller than the frontend-fidelity PRD in raw UI work, but it requires disciplined thinking about truthfulness, scope boundaries, and maintainable architecture communication. Estimated scope is one to two implementation days across the How It Works page and, at most, a small number of supporting architecture-doc alignments.

### 9.2 Team size and composition
- One implementation lane covering page content structure, explanation logic, and content-to-system alignment.
- One review lane checking truthfulness, ADR alignment, challenge-fit clarity, and drift between page claims and real implementation.

### 9.3 Suggested phases
1. At implementation kickoff, confirm the architecture story and the current-versus-target boundary rules before the first code change.
2. Define the minimal set of claims, examples, and decisions the page must explain.
3. Implement the content structure inside the frontend layout already owned by the frontend-fidelity PRD.
4. Align supporting documentation only where the page would otherwise contradict repo docs or ADRs.
5. Review the page against real code boundaries and later approved PRDs.

### 9.4 Dependencies
- The frontend-fidelity PRD must establish the shared shell and complete the How It Works visual structure from the mockup before this PRD finalizes page content.
- The cloud deployment, scheduling, and runtime topology PRD may proceed in parallel, but this PRD must label any not-yet-live runtime element as target state.
- The Live data integration and Live AI integration PRDs may refine examples later, but they must not require a structural rewrite of the page.

## 10. User stories

### 10.1 Explain the end-to-end system clearly
- **ID**: US-1
- **Description**: As an ML6 evaluator, I want the How It Works page to explain the full system flow so that I can understand the product without reading backend code first.
- **Acceptance criteria**:
  - [ ] The page explains the flow from World Bank data fetch to dashboard display.
  - [ ] The explanation includes data fetch, statistical processing, AI analysis, persistence, API serving, and frontend display.
  - [ ] The explanation is concise enough to scan but specific enough to defend in review.

### 10.2 Distinguish current system from planned target state
- **ID**: US-2
- **Description**: As a reviewer, I want the page to show what exists now versus what is planned so that the product does not overclaim maturity.
- **Acceptance criteria**:
  - [ ] Architecture elements that are not yet implemented are clearly framed as planned target state.
  - [ ] The page does not present future runtime behavior as already live.
  - [ ] Current-versus-target distinctions remain understandable without requiring the reader to open PRD files.

### 10.3 Make the two-step AI chain understandable
- **ID**: US-3
- **Description**: As an evaluator, I want the page to explain the two-step AI chain so that I can see the project's agentic-thinking rationale.
- **Acceptance criteria**:
  - [ ] The page explains the per-indicator analysis step and the macro synthesis step separately.
  - [ ] The page explains why two-step prompting is used instead of one large prompt.
  - [ ] The explanation distinguishes what pandas computes from what the LLM writes.

### 10.4 Surface key architecture decisions
- **ID**: US-4
- **Description**: As a reviewer, I want the page to summarize the key architecture decisions so that I can understand why the system is shaped this way.
- **Acceptance criteria**:
  - [ ] The page explains the roles of Firestore and GCS.
  - [ ] The page explains the push model and runtime separation at a high level.
  - [ ] The page explains why the API is OpenAPI-first and how that supports reviewable engineering.

### 10.5 Keep the explanation truthful and maintainable
- **ID**: US-5
- **Description**: As an engineer, I want architecture claims on the page to map to real code or approved plans so that the explanation layer stays honest over time.
- **Acceptance criteria**:
  - [ ] Each architecture section in the page implementation references its source of truth in inline JSX comments or a co-located content manifest by file path, ADR number, or later PRD.
  - [ ] Illustrative metrics or example content are controlled and easy to replace when live values become available.
  - [ ] Updating the page does not require reworking unrelated frontend structures.

### 10.6 Keep telemetry and examples honest
- **ID**: US-6
- **Description**: As a reviewer, I want telemetry-style values and example payloads on the page to be truthful or clearly illustrative so that the architecture page does not overclaim maturity.
- **Acceptance criteria**:
  - [ ] Live values are only shown where the current implementation can support them.
  - [ ] Illustrative values are clearly labeled and do not require telemetry infrastructure to exist.
  - [ ] Example input and output blocks remain representative of real or approved target contracts.

### 10.7 Keep the explanation surface bounded
- **ID**: US-7
- **Description**: As an engineer, I want this PRD to stay page-first and documentation-light so that architecture explainability does not expand into a repo-wide content rewrite.
- **Acceptance criteria**:
  - [ ] The How It Works page includes a clear architecture flow, prompt strategy section, input/output explanation, and technical responsibility breakdown.
  - [ ] Any supporting documentation alignment stays within the bounded files named in this PRD.
  - [ ] The implementation does not require a broad README or presentation rewrite.
