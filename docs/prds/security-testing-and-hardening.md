# PRD: Security, testing, and hardening

## 1. Product overview

### 1.1 Document title and version
Security, testing, and hardening
Version: 0.1
Date: 2026-04-10
Status: Draft for approval

### 1.2 Product summary
World Analyst can already define its target architecture, data path, AI path, and frontend surface, but the final review bar is not met until the product proves that those parts are protected, validated, and believable as one system. The remaining gap is not broad enterprise security work. It is the bounded hardening needed to stop obvious trust failures: browser-visible secrets, weak release confidence, untested failure paths, and documentation that claims a safer deployment posture than the implementation actually enforces.

This PRD defines the final hardening phase for the bounded World Analyst scope. It owns the browser-facing authentication boundary, secret hygiene, origin and request hardening, business-driven validation across the stack, and the minimum release-readiness checks that make the live demo defensible. It does not replace the earlier PRDs for storage, live data, live AI, cloud runtime, frontend fidelity, or architecture explanation. Instead, it closes those PRDs by deciding how the browser reaches the API safely enough for the challenge and by defining the proof that the system works end to end.

The hardening posture in this PRD stays proportional to the product. The project still targets 15 countries, 6 indicators, one Cloud Run Job, one Firestore collection, and one live demo URL. That means the right outcome is a small set of real controls and real tests, not a large security program. The product should be simple enough to explain and strong enough that a reviewer cannot immediately find an avoidable trust gap.

## 2. Goals

### 2.1 Business goals
- Remove obvious deployment trust gaps before the product is presented as review-ready.
- Finalize the browser-to-API authentication story so the live demo does not depend on a secret embedded in frontend code.
- Prove the product's key business flows through tests and deployment smoke checks rather than relying on manual confidence.
- Keep hardening proportional to the challenge scope instead of drifting into enterprise-scale security work.

### 2.2 User goals
- As an ML6 evaluator, I want the deployed product to show deliberate security and validation choices rather than demo shortcuts.
- As a finance reviewer, I want the live dashboard to feel trustworthy and stable even if I never see the underlying controls.
- As an engineer, I want one clear release gate that tells me whether the bounded system is safe and ready enough to present.

### 2.3 Non-goals (explicit out-of-scope)
- Adding OAuth, SSO, IAP, or a user-account system for the dashboard.
- Building a full CI/CD platform, security-operations workflow, or centralized alerting stack.
- Performing penetration testing, formal compliance work, or large-scale load and chaos testing.
- Replacing the existing OpenAPI security scheme with a new backend auth model unrelated to the bounded demo needs.
- Reworking earlier PRD scope such as live data, live AI, or Cloud Run Job dispatch.
- Introducing a separate backend-for-frontend service unless implementation evidence proves the frontend proxy cannot satisfy the auth boundary.

## 3. User personas

### 3.1 Key user types
- ML6 evaluator reviewing whether the system is secure enough and validated enough to trust.
- Finance reviewer opening the live dashboard and expecting a clean, stable experience.
- Engineer or operator responsible for deploying, verifying, and troubleshooting the bounded production setup.

### 3.2 Basic persona details
- ML6 evaluator: looks for obvious trust failures first, especially exposed secrets, weak auth boundaries, and untested critical flows.
- Finance reviewer: does not need to see security mechanics, but does notice unstable failures, inconsistent state, or obviously fake protections.
- Engineer or operator: needs a small, repeatable set of checks that prove the live system is still behaving as designed.

### 3.3 Role-based access (if applicable)
- No end-user role model is added in this PRD.
- Public users continue to access one dashboard URL.
- Service-to-service trust remains a backend concern controlled by runtime configuration and secrets.

## 4. Functional requirements

- **Browser-facing auth hardening** (Priority: High)
  - The deployed browser must not hold the API secret in JavaScript source, build artifacts, or request configuration.
  - The production frontend must call the API through a same-origin `/api/v1` proxy path served by the frontend runtime.
  - The frontend runtime must inject the required `X-API-Key` header server-side when proxying requests to the API service.
  - The browser-facing application should continue to present one live URL while the API retains its header-based protection behind that proxy boundary.
  - Local development may keep the current direct-header pattern for simplicity, but production behavior must not rely on that shortcut.

- **Secret hygiene and configuration safety** (Priority: High)
  - Secrets must come from Secret Manager or equivalent runtime configuration and must not be committed to source control.
  - Production services must fail fast when required secrets or mandatory runtime variables are missing rather than silently falling back to development defaults.
  - Frontend build-time variables must be limited to non-secret values such as public API base paths.
  - API keys, provider credentials, and any proxy-injection secret must remain server-side only.

- **Origin and request-boundary hardening** (Priority: High)
  - The API must not continue to allow wildcard CORS in deployed mode.
  - Allowed origins, methods, and headers must be explicitly configured for local versus deployed environments.
  - Health endpoints may remain unauthenticated, but protected business endpoints must continue to require valid auth.
  - Unauthorized requests must return clear `401` responses without leaking secret values or internal stack details.

- **Business-driven automated validation** (Priority: High)
  - The repo must define and run automated tests that prove the core product flows, not only helper behavior.
  - Validation must cover at least auth enforcement, durable status behavior, live-data partial-success rules, live-AI degraded fallback behavior, and frontend rendering of ready or failed states.
  - Tests should favor business outcomes such as "blocked unauthenticated access" or "partial live run preserves successful records" over implementation trivia.
  - Existing local-mode and deterministic test seams should remain usable so the suite stays fast and explainable.

- **Release-readiness smoke gate** (Priority: High)
  - The product must define a small manual or scripted smoke checklist for the deployed environment.
  - The smoke gate must cover one authenticated dashboard read path, one pipeline trigger flow, one terminal status check, and one verification that the browser bundle does not expose the API secret.
  - The smoke gate must be short enough to run before a demo or deployment update without becoming a separate operations project.
  - A failed smoke check must block the system from being described as review-ready.

- **Contract and failure-path verification** (Priority: Medium)
  - Hardening work must preserve the existing API contract and the frontend route structure.
  - The system must validate failure paths that a reviewer is likely to probe, including invalid API key, duplicate trigger while running, failed pipeline run, and incomplete AI or source coverage.
  - Error responses shown to the browser must stay honest and bounded rather than exposing raw internal exceptions.
  - The hardening phase should close the most visible trust gaps without expanding into a large exception-handling rewrite.

- **Documented operator checklist** (Priority: Medium)
  - The repo must document the required validation sequence for local and deployed verification.
  - The checklist must name the commands, environment variables, and success criteria needed to approve a release candidate for demo use.
  - Documentation should be concise enough that another engineer can run it without chat context.

- **Minimum viable auditability** (Priority: Medium)
  - Logs and responses must make it possible to distinguish auth failures, validation failures, and pipeline execution failures.
  - Secret values must never appear in logs.
  - Run identifiers should remain the main cross-service trace key for failure diagnosis.
  - This PRD does not require full audit logging or forensic tooling.

## 5. User experience

### 5.1 Entry points and first-time user flow
A reviewer opens the live dashboard and uses it normally. They do not need to manage API keys in the browser or work around exposed configuration. The product should feel like one coherent surface, with the protection happening behind the scenes rather than through a brittle manual setup step.

### 5.2 Core experience
The frontend keeps one live URL and the same visible route structure. Reads and trigger actions still work through the existing API contract, but the deployed browser no longer sends a secret header itself. If a request is unauthorized or the backend is unavailable, the product should fail clearly rather than exposing raw request machinery.

### 5.3 Advanced features and edge cases
If the frontend proxy is misconfigured, the user should see a controlled failure rather than silent broken requests. If a reviewer probes the API directly without the required header, the response should be correctly unauthorized. If a deployment is missing a required secret, the affected service should fail fast during startup or smoke validation instead of drifting into partial unsafe operation.

### 5.4 UI and UX highlights
- No new page is required for this PRD.
- The responsible-AI disclaimer remains visible on human-facing surfaces.
- Auth and security cues should remain subtle and credible rather than turning the UI into a control panel.
- User-visible error handling should favor short, honest failure states over raw technical output.

## 6. Narrative

World Analyst does not need heavyweight security theater. It needs to stop doing the few things that would immediately undermine trust. This PRD closes the last obvious gap by moving the API secret out of the browser, tightening deployed request boundaries, and defining the tests that prove the system still works after those changes. The result is a product that remains simple to explain, but no longer relies on the kind of shortcut a reviewer would challenge within minutes.

## 7. Success metrics

### 7.1 User-centric metrics
- A reviewer can use the live dashboard without any manual browser-side secret handling.
- The product fails clearly on unauthorized or broken requests instead of exposing raw internal behavior.
- The visible product experience remains stable after auth hardening.

### 7.2 Business metrics
- The live demo no longer depends on a browser-exposed shared secret.
- The team can show a bounded but credible validation story across backend, pipeline, and frontend.
- Reviewers can challenge the security and testing posture without immediately finding an avoidable gap.

### 7.3 Technical metrics
- Deployed browser assets do not contain the production API key.
- Deployed API CORS configuration does not allow wildcard origins.
- Automated tests cover the critical business outcomes named in this PRD.
- The release smoke checklist passes against the deployed environment before review use.
- Auth, trigger, and pipeline failures remain distinguishable through status or logs.

## 8. Technical considerations

### 8.1 Integration points
- Frontend request boundary in `frontend/src/api.js`.
- Frontend deployment or proxy configuration in the nginx-served Cloud Run frontend runtime. Cloud deployment owns getting that runtime live, and this PRD owns hardening it into the same-origin API proxy boundary.
- Production proxy shape: nginx should own a `location /api/v1/` block that forwards requests with `proxy_pass ${WORLD_ANALYST_API_UPSTREAM};`, where `WORLD_ANALYST_API_UPSTREAM` includes scheme, host, and the upstream base path with trailing slash, for example `https://world-analyst-api-xyz.run.app/api/v1/`. With that shape, a browser request to `/api/v1/countries` is proxied to `${WORLD_ANALYST_API_UPSTREAM}countries`. The proxy must inject `X-API-Key` from `${WORLD_ANALYST_PROXY_API_KEY}` before the request reaches the API service. Deployed frontend builds should set `VITE_API_BASE_URL=/api/v1` so browser calls target that proxy path and do not need the upstream service URL directly. `WORLD_ANALYST_PROXY_API_KEY` is injected into the frontend runtime from Secret Manager.
- API auth validation in `api/handlers/auth.py`.
- API middleware and CORS configuration in `api/app.py`.
- API contract in `api/openapi.yaml`.
- Pipeline and status behavior in `pipeline/main.py`, `pipeline/storage.py`, and relevant handlers.
- Deployment and operator documentation in `README.md`, `docs/DECISIONS.md`, and the relevant project-context sections when needed.

### 8.2 Data storage and privacy
- No new product data store is introduced in this PRD.
- Secrets remain in Secret Manager or equivalent runtime configuration, not in Firestore, GCS, or frontend bundles.
- Smoke checks may validate that no secret appears in built assets or runtime responses, but they must not print secrets into logs during that verification.

### 8.3 Scalability and performance
- The same-origin proxy adds a small extra hop, but that overhead is acceptable for a bounded, read-heavy dashboard.
- Hardening must not add heavyweight auth infrastructure or long-running security scans that do not match the product scope.
- The automated validation suite should stay fast enough for frequent local and pre-demo use.

### 8.4 Potential challenges
- The current frontend request helper assumes direct browser ownership of the API key, so the production path needs a clean split from local development behavior.
- The intended production mechanism is an nginx reverse proxy inside the Cloud Run frontend service, so the hardening work must update that runtime configuration rather than inventing a separate auth service.
- Wildcard CORS is easy for local development but too loose for the deployed system.
- It is easy to overbuild security posture for a bounded demo unless the phase stays focused on the most visible real gaps.
- Smoke validation needs to prove meaningful outcomes without growing into a fragile end-to-end test harness.

## 9. Milestones and sequencing

### 9.1 Project estimate
This is a medium-sized closing PRD. The code changes should stay narrower than the cloud runtime or frontend-fidelity phases, but they cut across frontend configuration, API middleware, auth handling, and test coverage. The main difficulty is choosing one clean boundary and then validating it thoroughly.

### 9.2 Team size and composition
- One implementation lane covering frontend proxy behavior, auth configuration, test additions, and operator documentation.
- One review lane checking secret exposure risk, CORS drift, contract preservation, and whether the tests actually prove the important business outcomes.

### 9.3 Suggested phases
1. Finalize the browser-facing auth decision and record it in `docs/DECISIONS.md`.
2. Split local-development request behavior from deployed frontend proxy behavior so the browser no longer owns the production API key.
3. Tighten deployed CORS and secret-loading behavior, including fail-fast rules for required runtime configuration.
4. Add business-driven automated tests for auth, critical failure paths, and cross-layer product behavior.
5. Document and run the release smoke checklist against the deployed environment.

### 9.4 Dependencies
- Cloud deployment, scheduling, and runtime topology should be substantially in place before this PRD completes, because the final browser-facing auth pattern depends on the deployed frontend and API relationship.
- Frontend fidelity should be substantially stable before this PRD finalizes user-visible failure treatment, so hardening does not collide with large layout churn.
- Live data and live AI should already define their failure and degraded-state rules, because this PRD validates those behaviors rather than inventing them.

## 10. User stories

### 10.1 Keep the production API key out of the browser
- **ID**: US-1
- **Description**: As an evaluator, I want the deployed browser to avoid carrying the shared API key so that the live product does not expose an obvious secret-management flaw.
- **Acceptance criteria**:
  - [ ] The deployed browser no longer sends the production `X-API-Key` header directly from client-side JavaScript.
  - [ ] The production frontend calls the API through the same-origin `/api/v1` proxy path.
  - [ ] The proxy layer injects the required API key server-side.
  - [ ] The live dashboard still works from one public URL after this change.
  - [ ] The proxy behavior is defined in a checked-in frontend runtime config artifact, such as an nginx config or template, rather than only through manual console steps.

### 10.2 Reject unauthorized direct API access cleanly
- **ID**: US-2
- **Description**: As an engineer, I want protected endpoints to reject unauthenticated callers clearly so that the API boundary remains real after deployment.
- **Acceptance criteria**:
  - [ ] Protected endpoints return `401` for missing or invalid API keys.
  - [ ] The health endpoint remains callable without auth.
  - [ ] Unauthorized responses do not expose secret values or raw stack traces.
  - [ ] Automated tests cover valid-key and invalid-key behavior.

### 10.3 Tighten deployed request boundaries
- **ID**: US-3
- **Description**: As a reviewer, I want the deployed API to avoid permissive request defaults so that the production posture is stronger than local development shortcuts.
- **Acceptance criteria**:
  - [ ] Deployed configuration does not allow wildcard CORS origins.
  - [ ] Allowed origins, methods, and headers are explicitly configured for production.
  - [ ] Local development can still run with a simpler configuration without changing the deployed contract.
  - [ ] The repo documents the local-versus-production boundary clearly.

### 10.4 Prove the core product flows through tests
- **ID**: US-4
- **Description**: As an engineer, I want automated tests to prove the product's critical flows so that release confidence does not depend on memory or manual optimism.
- **Acceptance criteria**:
  - [ ] The test suite covers auth enforcement on protected endpoints.
  - [ ] The test suite covers at least one pipeline-status failure path and one duplicate-trigger protection path.
  - [ ] The test suite covers one live-data or live-AI degraded outcome using the existing deterministic seams.
  - [ ] Frontend or view-model tests cover intentional handling of ready and failed states for at least one key surface.

### 10.5 Define a short release smoke gate
- **ID**: US-5
- **Description**: As an operator, I want a short post-deploy validation checklist so that I can confirm the live system is still safe and usable before a demo.
- **Acceptance criteria**:
  - [ ] The repo documents a smoke sequence covering dashboard read, trigger start, status poll, and one failure or unauthorized probe.
  - [ ] The smoke sequence includes a check that built frontend assets do not contain the production API key.
  - [ ] The smoke sequence confirms browser requests use the same-origin proxy path without a client-side `X-API-Key` header.
  - [ ] The smoke sequence is short enough to run before a review session.
  - [ ] A failed smoke check is treated as a release blocker for demo use.

### 10.6 Fail fast on missing secrets and unsafe production config
- **ID**: US-6
- **Description**: As an engineer, I want production services to refuse unsafe startup conditions so that the system does not drift into a misleading partially configured state.
- **Acceptance criteria**:
  - [ ] Production services fail fast when required secret or runtime configuration is missing.
  - [ ] Development defaults remain allowed only in explicit local-development modes.
  - [ ] Service logs identify missing configuration by name without printing secret values.
  - [ ] The operator documentation names the required configuration for each deployed service.