---
name: cal-design
description: Cal.com Design System & UI/UX Standards. Use when designing, building, styling, auditing, or refactoring UI components, templates, and styles according to the official Cal.com design language (Cal Sans typography, monochrome high-contrast, #111111 primary CTAs, 8px/12px/16px radius hierarchy, #101010 dark footer, and in-card product UI fragments).
---

# Cal.com Design System Specification & Engineering Guidelines

Official design specification derived from Cal.com's marketing and product surface (`DESIGN.md`).

## Core Design Principles

1. **Monochrome Primary Action Layer:**
   - Primary CTAs and h1/h2 headlines are near-black `#111111` (`colors.primary`). Never use blue or green on primary buttons.
   - Button press state shifts to `#242424` (`colors.primary-active`). Disabled state uses `#e5e7eb` (`colors.primary-disabled`).
   - Text on primary CTAs is always `#ffffff` (`colors.on-primary`).

2. **Typography Role Split:**
   - **Display Typeface:** `Cal Sans` (or `Inter` weight 600 with `-0.04em` tracking fallback). Used strictly for h1, h2, h3, and marquee display headlines. Weight must remain 600 across all sizes (never 700 or 800).
   - **Letter Spacing:** Mandatory negative letter spacing (`-0.5px` to `-2.0px` or `-0.02em` to `-0.04em`) on display headlines.
   - **Body & UI Typeface:** `Inter` (or `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`). Weight 400-500, letter spacing `0`.
   - **Boundary Invariant:** Never put body copy in Cal Sans; never put display headlines in plain un-tracked Inter.

3. **Color Tokens:**
   - `canvas`: `#ffffff` (default page background)
   - `surface-soft`: `#f8f9fa` (nav-pill wrapper, dividers)
   - `surface-card`: `#f5f5f5` (light-gray cards for feature cards, testimonials, pricing)
   - `surface-dark`: `#101010` (footer background and featured pricing card only)
   - `surface-dark-elevated`: `#1a1a1a`
   - `hairline`: `#e5e7eb` (1px subtle border)
   - `hairline-soft`: `#f3f4f6`
   - `ink`: `#111111` (primary text)
   - `body`: `#374151` (standard paragraph text)
   - `muted`: `#6b7280` (subheads, captions, metadata)
   - `accent`: `#3b82f6` (brand accent used sparely for inline links / badges, never primary CTA)
   - `success`: `#10b981` (status indicators, checkmarks)
   - `warning`: `#f59e0b`
   - `error`: `#ef4444`

4. **Component Geometry & Radii Scale:**
   - Small inline items / dropdowns: `6px` (`rounded.sm`)
   - Standard buttons, inputs, tabs: `8px` (`rounded.md`)
   - Feature cards, tool containers, modals: `12px` (`rounded.lg`)
   - Hero app mockup containers: `16px` (`rounded.xl`)
   - Nav pill wrappers & badges: `9999px` (`rounded.pill`)
   - Avatars & circular icon buttons: `9999px` (`rounded.full`, 36px diameter)
   - **Invariant:** Never use border radius > 16px on content cards.

5. **Signature Components:**
   - **Top Nav:** 64px height, `#ffffff` canvas, Cal Sans logo, 14px/500 Inter links, `#111111` primary button.
   - **Nav-Pill-Group:** `#f8f9fa` pill wrapper with 6px padding; active segment renders with `#ffffff` background and subtle shadow (`0 1px 2px rgba(0,0,0,0.05)`).
   - **In-Card Product UI Fragments:** Cards display real interactive product UI (form inputs, sliders, result monitors) directly inside the card rather than abstract marketing illustrations.
   - **Footer Closing Band:** `#101010` dark navy footer with `#a1a1aa` soft white text, 64px padding. The only dark band on standard pages.

6. **Strict Don'ts:**
   - Do NOT use accent colors (blue/green/purple) on primary CTAs.
   - Do NOT bold display headlines to 700 or 800.
   - Do NOT use font sizes < 10px anywhere in CSS.
   - Do NOT repeat the same card surface across consecutive page bands.
