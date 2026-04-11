---
name: design-taste-frontend
description: Senior UI/UX design engineering philosophy — anti-AI-slop patterns, high-agency frontend architecture, creative proactivity, and metric-driven design decisions. Use this skill when building any frontend component, page, or layout from scratch, reviewing frontend code for design quality, choosing between design approaches, or whenever the output risks looking like "generic AI-generated UI." This skill is the taste filter — it catches the patterns that make AI-built interfaces feel cheap and replaces them with craft. Works alongside project-specific design systems (like world-analyst-design-system) by providing the philosophy layer those systems don't cover.
---

# High-Agency Frontend — Design Taste and Anti-AI-Slop

This skill provides the design engineering philosophy, creative proactivity, and anti-slop guardrails that elevate frontend work from "functional" to "feels like a real product." It complements project-specific design systems by providing the *thinking* layer — those systems define tokens and rules; this skill defines judgment and taste.

## Relationship to Project Design Systems

This skill has two modes:

**When a project design system is active** (e.g., `world-analyst-design-system`): The project design system's tokens, fonts, colors, spacing, and structural rules take absolute precedence. This skill's Section 2 defaults (framework, fonts, colors) yield entirely. What remains active: the philosophy (Section 3), creative proactivity (Section 4), performance guardrails (Section 5), AI tells (Section 7), creative arsenal (Section 8), and motion paradigm (Section 9).

**When no project design system is active**: This skill's Section 2 defaults apply in full.

## 1. Active Baseline Configuration

These are dials, not binary switches. They shape every decision in Sections 3–7.

* **DESIGN_VARIANCE: 8** (1=Perfect Symmetry, 10=Artsy Chaos)
* **MOTION_INTENSITY: 6** (1=Static/No movement, 10=Cinematic/Magic Physics)
* **VISUAL_DENSITY: 4** (1=Art Gallery/Airy, 10=Pilot Cockpit/Packed Data)

Adapt these dynamically based on the user's explicit requests. These baselines drive the logic in subsequent sections.

## 2. Default Architecture & Conventions

These defaults apply when no project-specific design system overrides them. If a design system is active, defer to it for visual decisions and use only the structural/safety rules below.

### Always-Active Rules (regardless of design system)

* **DEPENDENCY VERIFICATION:** Before importing any 3rd-party library, check `package.json`. If missing, output the install command before providing code. Never assume a library exists.
* **RSC SAFETY:** In Next.js, global state works only in Client Components. Wrap providers in `"use client"` components.
* **INTERACTIVITY ISOLATION:** Interactive UI components with motion or state must be extracted as isolated leaf components with `'use client'` at the top. Server Components render static layouts exclusively.
* **Viewport Stability:** Never use `h-screen` for full-height sections. Always use `min-h-[100dvh]` to prevent layout jumping on mobile (iOS Safari).
* **Grid over Flex-Math:** Never use complex flexbox percentage math (`w-[calc(33%-1rem)]`). Use CSS Grid for reliable multi-column structures.
* **ANTI-EMOJI POLICY:** Never use emojis in code, markup, text content, or alt text. Replace with high-quality icons or clean SVG primitives.

### Defaults (yield to active design system)

* **Framework:** React or Next.js. Default to Server Components.
* **Styling:** Tailwind CSS for rapid prototyping. *If the project uses CSS custom properties instead, follow that convention.*
* **State Management:** Local `useState`/`useReducer` for isolated UI. Global state strictly for deep prop-drilling avoidance.
* **Icons:** `@phosphor-icons/react` or `@radix-ui/react-icons`. Standardize `strokeWidth` globally.
* **Responsiveness:** Standardize breakpoints. Contain layouts using `max-w-[1400px] mx-auto` or equivalent.

## 3. Design Engineering Directives (Bias Correction)

LLMs have statistical biases toward specific UI cliche patterns. These rules proactively construct premium interfaces:

### Rule 1: Deterministic Typography

* **Display/Headlines:** Tight tracking, bold weight, controlled line height.
  * **ANTI-SLOP:** If the project design system doesn't specify fonts, avoid `Inter` for premium/creative vibes. Use `Geist`, `Outfit`, `Cabinet Grotesk`, or `Satoshi`.
  * **TECHNICAL UI:** Serif fonts are banned for Dashboard/Software UIs. Use exclusively high-end Sans-Serif pairings (or whatever the design system specifies).
* **Body/Paragraphs:** Comfortable reading width (`max-width: 65ch`), relaxed line height.

### Rule 2: Color Calibration

* Max 1 accent color. Saturation < 80%.
* **THE LILA BAN:** The "AI Purple/Blue" aesthetic is banned. No purple button glows, no neon gradients. Use neutral bases with high-contrast, singular accents.
* **COLOR CONSISTENCY:** One palette for the entire output. Don't fluctuate between warm and cool grays.

### Rule 3: Layout Diversification

* **ANTI-CENTER BIAS:** When `DESIGN_VARIANCE > 4`, centered Hero sections are banned. Use split-screen (50/50), left-aligned content/right-aligned asset, or asymmetric white-space structures.

### Rule 4: Materiality and Anti-Card Overuse

* **For high VISUAL_DENSITY:** Generic card containers are banned. Use logic-grouping via border-top, divide-y, or negative space. Data metrics should breathe without being boxed in unless elevation is functionally required.
* Use cards only when elevation communicates hierarchy. When a shadow is used (and the design system allows it), tint it to the background hue.

### Rule 5: Interactive UI States

LLMs naturally generate "static" success states. You must implement full interaction cycles:

* **Loading:** Skeletal loaders matching layout sizes (avoid generic circular spinners).
* **Empty States:** Beautifully composed empty states indicating how to populate data.
* **Error States:** Clear, inline error reporting.
* **Tactile Feedback:** On `:active`, use `-translate-y-[1px]` or `scale(0.98)` to simulate a physical push.

### Rule 6: Data & Form Patterns

* **Forms:** Label sits above input. Helper text is optional but should exist in markup. Error text below input. Standard gap between input blocks.

## 4. Creative Proactivity (Anti-Slop Implementation)

To actively combat generic AI designs, systematically implement these high-end coding concepts as your baseline:

* **Magnetic Micro-physics (if MOTION_INTENSITY > 5):** Implement buttons that pull slightly toward the cursor. **Never use React `useState` for magnetic hover or continuous animations.** Use exclusively `useMotionValue` and `useTransform` outside the React render cycle to prevent performance collapse on mobile.
* **Perpetual Micro-Interactions:** When `MOTION_INTENSITY > 5`, embed continuous, infinite micro-animations (Pulse, Typewriter, Float, Shimmer) in standard components. Apply premium Spring Physics (`type: "spring", stiffness: 100, damping: 20`) to all interactive elements.
* **Layout Transitions:** Utilize Framer Motion's `layout` and `layoutId` props for smooth re-ordering, resizing, and shared element transitions.
* **Staggered Orchestration:** Don't mount lists or grids instantly. Use `staggerChildren` or CSS cascade (`animation-delay: calc(var(--index) * 100ms)`) to create sequential waterfall reveals. **The parent variants and children must reside in the identical Client Component tree.**

## 5. Performance Guardrails

* **DOM Cost:** Apply grain/noise filters exclusively to fixed, pointer-event-none pseudo-elements. Never apply to scrolling containers.
* **Hardware Acceleration:** Never animate `top`, `left`, `width`, or `height`. Animate exclusively via `transform` and `opacity`.
* **Z-Index Restraint:** Never use arbitrary z-index values. Use z-indexes strictly for systemic layer contexts (sticky navbars, modals, overlays).
* **Perpetual Motion Isolation:** Any perpetual motion or infinite loop must be memoized (`React.memo`) and completely isolated in its own microscopic Client Component. Never trigger re-renders in the parent layout.

## 6. Technical Reference (Dial Definitions)

### DESIGN_VARIANCE (1–10)

| Range | Behavior |
| --- | --- |
| 1–3 (Predictable) | Centered layouts, strict 12-column symmetrical grids, equal paddings |
| 4–7 (Offset) | Overlapping margins, varied aspect ratios, left-aligned headers over center-aligned data |
| 8–10 (Asymmetric) | Masonry layouts, CSS Grid with fractional units (`2fr 1fr 1fr`), large empty zones |

**MOBILE OVERRIDE:** For levels 4–10, any asymmetric layout must aggressively fall back to single-column on viewports < 768px to prevent horizontal scrolling.

### MOTION_INTENSITY (1–10)

| Range | Behavior |
| --- | --- |
| 1–3 (Static) | No automatic animations. CSS `:hover` and `:active` states only |
| 4–7 (Fluid CSS) | `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`. `animation-delay` cascades. Strictly `transform` and `opacity`. Sparing `will-change: transform` |
| 8–10 (Choreography) | Complex scroll-triggered reveals or parallax. Framer Motion hooks. Never `window.addEventListener('scroll')` |

### VISUAL_DENSITY (1–10)

| Range | Behavior |
| --- | --- |
| 1–3 (Gallery) | Generous white space. Huge section gaps. Expensive and clean |
| 4–7 (Daily App) | Normal spacing for standard web apps |
| 8–10 (Cockpit) | Tight paddings. No card containers; 1px lines to separate data. Everything packed. Monospace for all numbers |

## 7. AI Tells (Forbidden Patterns)

These are the patterns that instantly mark output as "AI-generated." Avoid them unless explicitly requested:

### Visual & CSS

* **NO Neon/Outer Glows:** No default `box-shadow` glows. Use inner borders or subtle tinted shadows (if design system allows shadows).
* **NO Pure Black:** Never use `#000000`. Use off-black, the design system's darkest surface, or zinc-950.
* **NO Oversaturated Accents:** Desaturate accents to blend with neutrals.
* **NO Excessive Gradient Text:** No text-fill gradients for large headers.
* **NO Custom Mouse Cursors:** Outdated and ruin performance/accessibility.

### Typography

* **NO Oversized H1s:** Control hierarchy with weight and color, not just massive scale.
* **Serif Constraints:** Serif only for creative/editorial designs. Never on dashboards.

### Layout & Spacing

* **Align & Space Perfectly:** Padding and margins must be mathematically consistent.
* **NO 3-Column Card Layouts:** The generic "3 equal cards horizontally" feature row is banned. Use 2-column zig-zag, asymmetric grid, or horizontal scrolling.

### Content & Data (The "Jane Doe" Effect)

* **NO Generic Names:** "John Doe", "Sarah Chan" are banned. Use creative, realistic names.
* **NO Generic Avatars:** No standard SVG "egg" icons. Use creative photo placeholders or specific styling.
* **NO Fake Numbers:** Avoid `99.99%`, `50%`. Use organic data (`47.2%`, `+1 (312) 847-1928`).
* **NO Startup Slop Names:** "Acme", "Nexus", "SmartFlow" are banned. Invent premium, contextual names.
* **NO Filler Words:** Avoid "Elevate", "Seamless", "Unleash", "Next-Gen". Use concrete verbs.

### External Resources

* **NO Broken Unsplash Links:** Use `https://picsum.photos/seed/{random_string}/800/600` or SVG placeholders.
* **shadcn/ui Customization:** Never use shadcn/ui in its default state. Customize radii, colors, and shadows to match the project aesthetic.

## 8. The Creative Arsenal (High-End Inspiration)

Don't default to generic UI. Pull from this library of advanced concepts. When appropriate, use GSAP (ScrollTrigger/Parallax) for scrolltelling or ThreeJS/WebGL for 3D/Canvas animations. **Never mix GSAP/ThreeJS with Framer Motion in the same component tree.** Default to Framer Motion for UI/Bento interactions. Use GSAP/ThreeJS exclusively for isolated full-page scrolltelling or canvas backgrounds, wrapped in strict `useEffect` cleanup blocks.

### Navigation & Menus

* **Mac OS Dock Magnification:** Nav-bar icons scale fluidly on hover
* **Magnetic Button:** Buttons physically pull toward the cursor
* **Dynamic Island:** Pill-shaped UI morphing to show status/alerts
* **Contextual Radial Menu:** Circular menu expanding at click coordinates
* **Mega Menu Reveal:** Full-screen dropdowns with stagger-faded content

### Layout & Grids

* **Bento Grid:** Asymmetric, tile-based grouping (Apple Control Center style)
* **Masonry Layout:** Staggered grid without fixed row heights
* **Split Screen Scroll:** Two halves sliding in opposite directions on scroll
* **Curtain Reveal:** Hero section parting like a curtain on scroll

### Cards & Containers

* **Parallax Tilt Card:** 3D-tilting card tracking mouse coordinates
* **Spotlight Border Card:** Card borders illuminating dynamically under cursor
* **Holographic Foil Card:** Iridescent reflections shifting on hover
* **Morphing Modal:** Button seamlessly expanding into its own dialog container

### Scroll-Animations

* **Sticky Scroll Stack:** Cards sticking and physically stacking
* **Horizontal Scroll Hijack:** Vertical scroll translating into horizontal gallery pan
* **Zoom Parallax:** Background image zooming in/out with scroll
* **Scroll Progress Path:** SVG lines drawing themselves as user scrolls

### Typography & Text

* **Kinetic Marquee:** Endless text bands reversing on scroll
* **Text Mask Reveal:** Typography as transparent window to video background
* **Text Scramble Effect:** Matrix-style character decoding on load/hover
* **Gradient Stroke Animation:** Outlined text with animated gradient stroke

### Micro-Interactions

* **Particle Explosion Button:** CTAs shattering into particles on success
* **Skeleton Shimmer:** Light reflections moving across placeholder boxes
* **Directional Hover Aware Button:** Fill entering from exact mouse-entry side
* **Animated SVG Line Drawing:** Vectors drawing their own contours in real-time
* **Mesh Gradient Background:** Organic animated color blobs

## 9. The Motion-Engine Bento Paradigm

For modern SaaS dashboards or feature sections, use this "Bento 2.0" architecture. It goes beyond static cards and enforces perpetual physics.

### A. Core Design Philosophy

* **Aesthetic:** High-end, minimal, functional.
* **Surfaces:** Large border-radius for containers. Diffusion shadows (light, wide-spreading) for depth without clutter. *Adapt these to the project's design system when active.*
* **Typography:** Tight tracking for headers. Use whatever the design system specifies.
* **Labels:** Titles and descriptions placed **outside and below** cards for gallery-style presentation.
* **Pixel-Perfection:** Generous internal padding in cards.

### B. The Animation Engine Specs (Perpetual Motion)

All cards should contain perpetual micro-interactions when `MOTION_INTENSITY > 5`:

* **Spring Physics:** No linear easing. Use `type: "spring", stiffness: 100, damping: 20`.
* **Layout Transitions:** Use `layout` and `layoutId` props for smooth transitions.
* **Infinite Loops:** Cards have "Active States" that loop infinitely (Pulse, Typewriter, Float, Carousel).
* **Performance:** Wrap dynamic lists in `<AnimatePresence>`. Isolate perpetual motion in memoized Client Components.

### C. The 5-Card Archetypes

When building Bento grids, implement these micro-animation patterns:

1. **The Intelligent List:** Items auto-sort with `layoutId` transitions, simulating AI prioritization.
2. **The Command Input:** Search bar with multi-step typewriter effect, blinking cursor, shimmer loading state.
3. **The Live Status:** Breathing status indicators. Pop-up badges with overshoot spring effect.
4. **The Wide Data Stream:** Infinite horizontal carousel of metrics. Seamless `x: ["0%", "-100%"]` loop.
5. **The Contextual UI:** Document view with staggered text highlighting and floating action toolbar.

## 10. Pre-Flight Check

Before outputting frontend code, evaluate against this matrix:

- [ ] Is global state used only to avoid deep prop-drilling, not arbitrarily?
- [ ] Is mobile layout collapse guaranteed for high-variance designs?
- [ ] Do full-height sections use `min-h-[100dvh]` instead of `h-screen`?
- [ ] Do `useEffect` animations contain strict cleanup functions?
- [ ] Are empty, loading, and error states provided?
- [ ] Are cards omitted in favor of spacing where design system or density level calls for it?
- [ ] Are CPU-heavy perpetual animations isolated in their own Client Components?
- [ ] Does the output avoid every pattern listed in Section 7 (AI Tells)?
- [ ] Does the output respect the active project design system's constraints?
