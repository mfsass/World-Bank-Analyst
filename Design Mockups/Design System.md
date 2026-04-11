# Design System Document: Engineering Intelligence

## 1. Overview & Creative North Star
**Creative North Star: "The Tactical Command Center"**
This design system is built for the high-stakes environment of global analysis. It moves away from the "softness" of consumer web design toward a high-density, engineering-grade aesthetic. We achieve a premium feel not through decoration, but through extreme precision, rigorous vertical rhythm, and an authoritative use of color. 

The experience should feel like a high-end physical hardware interface—utilitarian, high-contrast, and unapologetically digital. We break the "template" look by utilizing a strict 32px vertical rhythm and specialized monospaced metrics that evoke the feeling of real-time data processing.

---

## 2. Colors & Surface Architecture

### Palette Definition
We utilize a monochromatic base to ensure that tactical accents carry maximum functional weight.

*   **Background (Core):** `#0E0E0E` (Surface-lowest)
*   **Surface (Cards):** `#1A1A1A` (Surface-container)
*   **Border (Structural):** `#262626` (Outline-variant)
*   **Primary Accent:** `#FF4500` (International Orange) – Reserved for AI insights and primary CTAs.
*   **Semantic Accents:** 
    *   Success: `#22C55E`
    *   Warning: `#F59E0B`
    *   Critical: `#EF4444`

### The "Engineering-Grade" Rules
*   **No-Glassmorphism Policy:** Shadows, blurs, and transparencies are prohibited. Depth is achieved via tonal shifts and strict borders only.
*   **Surface Hierarchy:** Use `#0E0E0E` for the canvas. Use `#1A1A1A` for cards. If a nested container is required (e.g., an inner data table), shift to `#201F1F`.
*   **The Signature Border:** All interactive cards must use a 1px solid border of `#262626`. For "Active" or "Focused" states, the border may transition to the Primary Accent (`#FF4500`).

---

## 3. Typography: The Dual-Font Strategy

This system uses a tension between a clean Neo-Grotesque (Inter) and a high-precision Monospace (Commit Mono) to separate narrative from data.

| Level | Token | Font | Size | Weight | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-md` | Inter | 2.75rem | 700 | Large dashboard headers |
| **Headline** | `headline-sm` | Inter | 1.5rem | 600 | Section titles |
| **Title** | `title-sm` | Inter | 1.0rem | 600 | Card titles |
| **Body** | `body-md` | Inter | 0.875rem | 400 | General descriptions |
| **Metric** | `custom-mono` | Commit Mono | 1.125rem | 500 | Dynamic data & KPI values |
| **Micro** | `label-sm` | Commit Mono | 0.6875rem | 700 | Labels, timestamps, footer |

**Editorial Note:** Always use `uppercase` with 0.05em letter-spacing for `label-sm` to maintain a "technical spec" look.

---

## 4. Vertical Rhythm & Layout Patterns

### The 32px Rhythm
The vertical spacing between major sections, card groupings, and header-to-body transitions is locked at **32px**. This creates a breathable yet structured cadence that signals professional engineering.

### The 4-KPI Executive Row
The top of the interface must feature a 4-column KPI layout. 
*   **Structure:** Each KPI is a `#1A1A1A` card with a top-aligned `label-sm` (Secondary Text) and a large `custom-mono` value (Primary Text).
*   **Indicator:** A 2px bottom-accent bar using the semantic colors (Orange, Green, Amber, Red) can be used to indicate status trends.

---

## 5. Signature Pattern: AI-Generated Insights

The "AI-Generated Insights" pattern is the crown jewel of this system. It must be treated with more visual "energy" than standard data.

*   **Header:** Features the `auto_awesome` icon in `#FF4500`.
*   **Background:** Use a subtle vertical gradient: `linear-gradient(180deg, #1A1A1A 0%, #0E0E0E 100%)`.
*   **Border:** The left border of the insight card is thickened to 4px and colored `#FF4500`.
*   **Typography:** Insights use `title-md` for the summary and `body-md` for the breakdown. Actionable intelligence should be highlighted using `Commit Mono` in the Primary Accent color.

---

## 6. Component Specifications

*   **Buttons (Primary):** Background `#FF4500`, Text `#FFFFFF`. Sharp 8px corners. No gradients.
*   **Buttons (Ghost):** Background `transparent`, Border 1px `#262626`, Text `#F5F5F5`.
*   **KPI Cards:** Must include a `Commit Mono` label at the bottom right indicating the "Data Freshness" (e.g., `LATENCY: 24MS`).
*   **Footer Disclaimer:** Locked to the bottom of the viewport or container. 
    *   **Style:** `label-sm` in `#737373`.
    *   **Content:** "SYSTEM CLASSIFICATION: PROPRIETARY // DATA SOURCE: KINETIC ENGINEERING ANALYTICS // [TIMESTAMP]"
*   **Inputs:** Background `#0E0E0E`, Border 1px `#262626`. On focus, the border glows `#FF4500` with 0px blur—a hard, 1px offset.

---

## 7. Do's and Don'ts

### Do
*   **DO** use Commit Mono for any text that changes frequently (numbers, IDs, timestamps).
*   **DO** maintain strict 32px margins between the 4-KPI row and the main content area.
*   **DO** use high contrast. If a piece of text is secondary, drop it to `#737373` immediately.

### Don't
*   **DON'T** use border-radius larger or smaller than 8px. Consistency is vital for the "Engineering" look.
*   **DON'T** use soft shadows. If you need to separate an element, use a 1px border or a darker background shade.
*   **DON'T** use icons for decoration. Icons must only be used as functional cues (e.g., the orange `auto_awesome` for AI).

---

## 8. Elevation & Depth
Depth is purely Tonal. 
1.  **Level 0 (Canvas):** `#0E0E0E`
2.  **Level 1 (Card):** `#1A1A1A`
3.  **Level 2 (Nested Input/Inner Card):** `#201F1F`
4.  **Level 3 (Popovers/Tooltips):** `#262626` (Use a Primary Orange top-border to indicate "Active" layer status).
