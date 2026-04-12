# PRD: World Analyst V2 Product Upgrade

**Status:** Draft  
**Purpose:** Upgrade World Analyst from a competent dashboard into a sharper economic intelligence product with better interaction, better historical context, and a stronger demo story.

---

## 1. Goal

Make World Analyst feel like a premium macro intelligence terminal for finance professionals and reviewers.

The product should:

1. deliver a real global read quickly on the Overview page
2. make Country Intelligence directly accessible and historically rich
3. explain the system visually and clearly on How It Works
4. support both truthful real runs and reliable demo walkthroughs on Pipeline Trigger

---

## 2. Users

### Primary users

1. **Finance professionals** reviewing countries, regions, and macro risk signals
2. **Reviewers and evaluators** judging product quality, clarity, and engineering discipline
3. **Presenters** who need the product to hold up in a live demo

### Product standard

This should not feel like an internal dashboard or a challenge prototype. It should feel like a credible macro product built for a user who wants direction of travel, risk concentration, and fast access to the right market context.

---

## 3. Problem Statement

The current product works, but several important surfaces still behave like internal system pages rather than polished analyst tools.

### Current issues

#### Global Overview

- The map is visually dominant but behaviorally weak.
- Hover behavior is limited, click behavior is not strong enough, and click-away reset is unclear.
- The right rail becomes weak or empty when no market is selected.
- The space below the map feels underused and awkward.
- Labels such as "live", "current slice", "pending", and "on demand" sound too operational and are often semantically wrong.

#### Country Intelligence

- Country access is too dependent on the Overview page.
- The page is too latest-year-centric and does not provide enough historical context.
- The product already fetches a long historical window, but the UI collapses that richness into a near-snapshot experience.

#### How It Works

- The page is informative but too static, too text-heavy, and too architecture-like.
- It explains mechanics more than it explains value.

#### Pipeline Trigger

- Real runs can feel slow or hung during demos.
- The experience lacks a clean separation between proving the system works and presenting the system clearly.

---

## 4. Product Principles

1. **Lead with decision value, not system state**
2. **Show direction of travel, not just latest snapshot**
3. **Make interactions earn their screen space**
4. **Keep language direct, credible, and finance-relevant**
5. **Separate real execution from simulation honestly**
6. **Preserve the World Analyst design system**
7. **Ship in phases that keep the product strong at every step**

---

## 5. Scope

## In scope

### A. Global Overview rework

- stronger map interaction
- better default global state when no country is selected
- better use of space below and around the map
- cleaner copy and labeling
- stronger global intelligence framing

### B. Country Intelligence upgrade

- direct country directory and access
- historical timeline view
- regime labeling
- region and panel comparison context

### C. How It Works redesign

- visual walkthrough of the pipeline
- clearer story of how data becomes insight
- more design-forward explanation for finance and demo audiences

### D. Pipeline Trigger redesign

- split into **Real run** and **Demo walkthrough**
- keep demo mode frontend-only
- share the same walkthrough model with How It Works

### E. Data foundation

- persist historical series, targeting `2010–2024`
- expose history inline in existing API responses
- add deterministic regime labels

## Out of scope

- BigQuery migration
- real-time streaming infrastructure
- full observability platform
- arbitrary scenario sandbox
- auth redesign
- major backend architecture changes beyond what timeline support requires

---

## 6. Page-by-Page Requirements

## 6.1 Global Overview

### Product goal

Make the Overview page feel like a **global macro command surface**, not a static landing page.

### Requirements

1. **Upgrade map interaction**
   - add hover preview for markets
   - keep click-to-pin behavior
   - add clear click-away reset
   - make selected state obvious
   - improve popover quality with stronger context

2. **Strengthen the default no-selection state**
   - when no country is selected, the right rail should remain useful
   - show global content such as:
     - top current risks
     - strongest improving markets
     - weakest markets
     - regional divergence
     - notable anomalies

3. **Use the space below the map properly**
   - replace or redesign the current chip strip
   - that area should become:
     - a compact market tape, or
     - leaders / laggards / anomalies, or
     - a stronger region summary layer

4. **Clean the language**
   - remove misleading operational labels such as:
     - live coverage
     - current slice
     - pending
     - on demand
   - replace them with clearer product terms such as:
     - latest update
     - tracked markets
     - global pulse
     - market briefing
     - regional picture

5. **Reduce dependency on Overview for country access**
   - Overview should help discovery, not act as the only way into country detail

### Acceptance criteria

- Hovering a market gives useful immediate feedback
- Clicking a market pins it and updates the right rail
- Clicking away resets focus cleanly
- The page is still useful when no market is selected
- The lower map area feels intentional and information-dense
- Copy reads like a finance product rather than an internal tool

---

## 6.2 Country Intelligence

### Product goal

Turn Country Intelligence into a real destination and give it the historical depth expected from a macro product.

### Requirements

#### A. Country directory

- `/country` becomes a real landing page
- show all tracked countries directly
- support:
  - search
  - region filter
  - direct links to `/country/:id`

#### B. Historical timeline

- add multi-year timeline support targeting **2010–2024**
- use the same tracked indicator set already in the product
- make the timeline analytical, not decorative
- support anomaly markers and useful reference lines where appropriate

#### C. Regime label

- add a deterministic `regime_label`
- initial labels can include:
  - recovery
  - expansion
  - overheating
  - contraction
  - stagnation
- this should be rule-based, not LLM-derived

#### D. Relative context

- show comparison against:
  - region median or average
  - tracked panel median or average

#### E. Country page behavior

- keep the current synthesis and risk-flag story
- add historical context without overwhelming the page
- make the page feel like a macro workstation, not a single-year sheet

### Acceptance criteria

- Users can enter Country Intelligence without using Overview
- Country pages show meaningful history, not only current values
- Regime labels appear consistently and credibly
- Relative comparison helps interpretation without adding clutter

---

## 6.3 How It Works

### Product goal

Explain the system visually enough that a first-time reviewer understands the product quickly.

### Requirements

1. Reframe the page around the transformation:
   - source data
   - signal layer
   - country synthesis
   - global synthesis
   - stored outputs

2. Replace static explanation blocks with:
   - a visual step flow
   - example inputs and outputs
   - staged explanation of the value created at each step

3. Keep the page honest about:
   - what is deterministic
   - what is model-generated
   - where responsible-AI caveats apply

4. Reuse the shared walkthrough model with Pipeline Trigger

### Acceptance criteria

- A first-time viewer can explain the pipeline after one pass
- The page feels like product explanation, not internal documentation
- The visuals clarify the system more than the text alone

---

## 6.4 Pipeline Trigger

### Product goal

Make Pipeline Trigger strong both as an operational page and as a demo page.

### Requirements

1. Add two modes:
   - **Real run**
   - **Demo walkthrough**

2. **Real run mode**
   - keep using real backend endpoints
   - improve clarity around stage progress
   - explain why longer stages take time
   - keep state truthful

3. **Demo walkthrough mode**
   - must be frontend-only
   - must be clearly labeled simulated
   - must not write fake state into backend status
   - must use the same stage model and visual language as real mode

4. **Shared walkthrough system**
   - same stages across How It Works and Pipeline Trigger
   - same step names
   - same core business explanations
   - separate adapters for live vs simulated progress

### Acceptance criteria

- Users can instantly tell which mode they are in
- Demo mode is polished, replayable, and fast
- Real mode remains available and trustworthy
- How It Works and Pipeline Trigger tell the same product story

---

## 7. Technical Implications

## Frontend

Likely files to touch:

- `frontend/src/pages/GlobalOverview.jsx`
- `frontend/src/pages/CountryIntelligence.jsx`
- `frontend/src/pages/HowItWorks.jsx`
- `frontend/src/pages/PipelineTrigger.jsx`
- shared components and CSS
- likely new shared pipeline walkthrough config/components

## API and backend

Needed for timeline work:

- extend country payloads inline rather than introducing a separate history endpoint
- update `api/openapi.yaml` first
- update handlers and tests to match the contract
- preserve Firestore document storage

## Pipeline and storage

Needed for timeline work:

- persist historical series instead of collapsing to latest-year-only shaping
- keep the storage model in Firestore documents
- use deterministic rules for regime labels

## Documentation

- append ADRs for meaningful trade-offs, especially:
  - deterministic regime labels
  - frontend-only demo walkthrough
  - inline time-series in existing API responses

---

## 8. Risks and Trade-offs

| Risk | Why it matters | Mitigation |
|---|---|---|
| Overview becomes too busy | stronger interaction can create clutter | keep one clear default state and one clear selected state |
| Timeline adds noise | more history can weaken readability | start with a small, opinionated indicator set |
| Demo mode confuses users | could weaken trust | label simulated mode clearly at all times |
| API scope expands too far | history support can sprawl | keep payloads focused and document-shaped |
| Copy drifts back to internal jargon | hurts credibility | review all UI copy against finance-first language |

---

## 9. Recommended Execution Order

## Phase 1 — Data foundation

- persist `2010–2024` historical series in Firestore
- expose time series inline in existing API responses
- add deterministic `regime_label`

**Why first:** this unlocks the strongest substantive product improvement and avoids building UI on top of missing data.

## Phase 2 — Pipeline Trigger split

- split Pipeline Trigger into **Real run** and **Demo walkthrough**
- keep demo mode frontend-only
- create a shared pipeline stage model

**Why second:** this is one of the strongest demo upgrades and can be done without waiting for the broader page rework.

## Phase 3 — Global Overview rework

- improve map interaction
- replace the weak no-selection rail state
- improve space below the map
- clean copy and labels

**Why third:** this upgrades the most visible page after the foundational work is in place.

## Phase 4 — Country Intelligence upgrade

- build real country directory
- add timeline UI
- show regime label
- add region/panel comparison context

**Why fourth:** it depends on the data foundation and deserves focused product execution.

## Phase 5 — How It Works rebuild

- rebuild as a visual walkthrough
- reuse the shared pipeline stage model from Phase 2

**Why fifth:** it benefits from the stage-model work and should reflect the improved product story, not the old one.

---

## 10. Acceptance Criteria by Phase

### Phase 1

- Historical time series is available through the API
- Regime labels are deterministic and documented
- Spec, handlers, and tests remain aligned

### Phase 2

- Pipeline Trigger supports **Real run** and **Demo walkthrough**
- Demo mode is frontend-only and explicitly labeled
- Shared stage model exists

### Phase 3

- Overview is useful with no market selected
- Map interaction feels responsive and intentional
- Copy is cleaner and less operational

### Phase 4

- `/country` is a real directory
- Country pages show multi-year history clearly
- Regime labels and peer context improve interpretation

### Phase 5

- How It Works is visual and easier to understand
- It clearly explains the transformation from raw data to final outputs
- It shares the same stage language as Pipeline Trigger

