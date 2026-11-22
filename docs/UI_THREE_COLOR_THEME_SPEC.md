# CampusMate 2.0 — 3-Color UI Theme & Design System Specification
> **Status:** Design Architecture Specification Only (**NOT IMPLEMENTED YET** — zero UI files modified)  
> **Role:** Principal Product Designer & UI Systems Architect  
> **Target Codebase:** [`src/index.css`](CampusMate_2-main/src/index.css), [`App.jsx`](CampusMate_2-main/src/App.jsx), [`Navbar.jsx`](CampusMate_2-main/src/components/Navbar.jsx), [`Hero.jsx`](CampusMate_2-main/src/components/Hero.jsx), [`Login.jsx`](CampusMate_2-main/src/components/Login.jsx), [`StudentDashboard.jsx`](CampusMate_2-main/src/components/StudentDashboard.jsx), [`ChatSidebar.jsx`](CampusMate_2-main/src/components/chat/ChatSidebar.jsx), [`ChatContainer.jsx`](CampusMate_2-main/src/components/chat/ChatContainer.jsx), [`ChatMessage.jsx`](CampusMate_2-main/src/components/chat/ChatMessage.jsx), [`ChatInput.jsx`](CampusMate_2-main/src/components/chat/ChatInput.jsx), [`ChatEmptyState.jsx`](CampusMate_2-main/src/components/chat/ChatEmptyState.jsx), [`SourceModal.jsx`](CampusMate_2-main/src/components/chat/SourceModal.jsx), [`MarkdownRenderer.jsx`](CampusMate_2-main/src/components/chat/MarkdownRenderer.jsx), [`AdminDashboard.jsx`](CampusMate_2-main/src/components/AdminDashboard.jsx).  
> **Brand Constraint:** Strictly preserves the existing **Nexus Prism** SVG identity in [`CampusLogo.jsx`](CampusMate_2-main/src/components/brand/CampusLogo.jsx).

---

## 1. Visual Diagnosis: Why the Current UI Feels "Basic White"

Inspecting the live student chat screenshot alongside CSS and JSX source files reveals **four concrete design failures** causing the flat, generic Tailwind-default look:

1. **Zero Tonal Separation Between Canvas & Chrome:** [`App.jsx#L28`](CampusMate_2-main/src/App.jsx#L28) defaults to `'light'`, where `--bg-page` (`#F8FAFC`), `--bg-surface` (`#FFFFFF`), and `--bg-elevated` (`#FFFFFF`) in [`src/index.css#L63-L71`](CampusMate_2-main/src/index.css#L63-L71) sit within 2% luminance of pure white. The sidebar, message cards, header, and canvas blur together into one bright sheet.
2. **90/10 White + Generic Cobalt Ratio (Missing Secondary Mass):** Nearly 90% of pixels are white/near-white and ~10% are default Tailwind `#2563EB` blue buttons/bubbles. Without a deliberate **30% dark structural counterbalance**, there is no editorial hierarchy.
3. **Hardcoded Utility Color Leaks Bypassing `@theme` Tokens:** Even though `src/index.css` defines semantic CSS variables, multiple components bypass them with raw Tailwind utility classes:
   * [`ChatMessage.jsx#L92-L197`](CampusMate_2-main/src/components/chat/ChatMessage.jsx#L92-L197): Hardcodes `bg-blue-600`, `bg-white`, `border-slate-200`, `text-slate-800`, `bg-blue-50`, `bg-emerald-50`, `bg-rose-50`, and `bg-slate-50`.
   * [`ChatContainer.jsx#L526-L578`](CampusMate_2-main/src/components/chat/ChatContainer.jsx#L526-L578): Hardcodes the Thinking Pipeline card to `bg-white border-slate-200 text-slate-800` with `bg-blue-600` and `bg-emerald-50`.
   * [`ChatSidebar.jsx#L130,L202,L230,L248`](CampusMate_2-main/src/components/chat/ChatSidebar.jsx#L130): Hardcodes `hover:bg-white` and `from-blue-600 to-indigo-600`.
   * [`MarkdownRenderer.jsx#L14-L29`](CampusMate_2-main/src/components/chat/MarkdownRenderer.jsx#L14-L29): Hardcodes `#090D1A` / `#060A14` / `slate-*`.
4. **4th/5th/6th Rainbow Chromatic Drift:** [`ChatInput.jsx#L13-L29`](CampusMate_2-main/src/components/chat/ChatInput.jsx#L13-L29) introduces cyan, indigo, fuchsia, rose, and purple gradients on model cards; [`Login.jsx#L16,L335`](CampusMate_2-main/src/components/Login.jsx#L16) mixes electric sky-blue aurora blobs with `purple-500/600` admin buttons; [`Hero.jsx#L110`](CampusMate_2-main/src/components/Hero.jsx#L110) hardcodes `rgba(59,130,246,0.12)` glow.

---

## 2. The Selected 3-Color System: **"Scholarly Studio"**

Rather than returning *another* off-white + cobalt blue template, CampusMate 2.0 adopts an unmistakable, university-grade **3-Color Architectural System** governed by strict **60–30–10 perceptual weighting**:

| Allocation | Color Name | Primary Base Hex | Tonal Steps (Strictly Same Hue/Neutral Family) | Design Role Across App |
| :---: | :--- | :---: | :--- | :--- |
| **60%** | **Warm Alabaster** *(Archival Reading Paper)* | **`#F5F1E8`** (`HSL 41° 38% 94%`) | • Raised Card: **`#FBF9F4`**<br>• Pressed / Inset / Code Pill: **`#EAE4D7`**<br>• Hairline Border: **`#D8D0C0`**<br>• Strong Border: **`#BEB39E`** | Main reading canvas, AI assistant cards, input box, empty state, right login panel, documentation & admin surfaces. Eliminates harsh `#FFFFFF` eye fatigue. |
| **30%** | **Midnight Inkwell** *(Structural Obsidian Navy)* | **`#141B29`** (`HSL 220° 34% 12%`) | • Elevated Ink Surface: **`#1D273B`**<br>• Ink Hover / Border: **`#2A364F`**<br>• Body Text Ink: **`#3E4656`**<br>• Muted Caption Ink: **`#5A6375`** | **Active 30% UI surfaces:** Collapsible Left Sidebar (`ChatSidebar`), User Message Bubbles, Markdown Code Terminals, `Login` Left Branding Panel, plus crisp primary typography. |
| **10%** | **Deep Veridian** *(Authoritative Signal Teal)* | **`#0D6E6E`** (`HSL 180° 79% 24%`) | • Hover / Active Press: **`#0A5858`**<br>• Luminous Dark Accent: **`#2DD4BF`** (Dark Mode only)<br>• Soft Tint Wash: **`rgba(13, 110, 110, 0.10)`**<br>• Tint Border: **`rgba(13, 110, 110, 0.28)`** | Primary CTAs (`Send`, `New chat`, `Log in`), focus rings, active chat highlight rail, `[1]` inline citations, `DOC #1` badges, grounding indicator, active category pills. |

> **Why Not Cobalt Blue + White, or Orange + White?**
> * Keeping Cobalt Blue fails the brief — the user already sees generic white + blue.
> * **Deep Veridian (`#0D6E6E`)** gives crisp academic authority while sitting harmonically adjacent to the cyan/indigo prism edges of the preserved [`Nexus Prism`](CampusMate_2-main/src/components/brand/CampusLogo.jsx) SVG logo — especially when `CampusLogo` sits on top of the **Midnight Inkwell (`#141B29`)** sidebar header where its subtle prism luminescence reads effortlessly!

### Dark Mode ("Nocturne Ink") — Exact Same 3 Hues Inverted (Zero Extra Colors)
When the student toggles Dark Mode, the theme **does not invent neon blues or grays** — it inverts the exact 3 chromatic families:
* **60% Ground:** `#0E141F` (Deepest Nocturne Inkwell) | Surfaces: `#141B29` / `#1D273B` | Borders: `#2A364F`
* **30% Contrast Typography & Secondary Anchors:** `#F5F1E8` (Warm Alabaster ink — glare-free off-white!) & `#9CA8BA` secondary copy
* **10% Signal Accent:** `#2DD4BF` (Luminous Veridian, hover `#14B8A6`) with **`#0E141F` dark ink text** inside solid accent buttons (`9.91:1` contrast vs washed-out white-on-bright-teal!)

### Strict Rule on 4th+ Colors ("Functional Micro-Telemetry Only")
* Zero decorative purple, fuchsia, rose, orange, or rainbow gradients anywhere in cards, hero blobs, or model selectors.
* Semantic danger (`#B91C1C`) and warning (`#B45309`) appear **strictly** inside destructive delete buttons, password validation errors, and offline/outage alerts — **never** as ambient badges (even `"Grounding Verified"` switches from green `emerald-500` to **Veridian Signal `#0D6E6E`** to maintain strict 3-color discipline).

---

## 3. Mathematically Verified WCAG Contrast Matrix

All foreground/background token combinations were computed directly from sRGB relative luminance:

| Pair | Light / Dark Surface | Contrast Ratio | WCAG 2.1 Rating | Usage |
| :--- | :--- | :---: | :---: | :--- |
| Inkwell `#141B29` on Alabaster `#F5F1E8` | Light Ground | **15.29 : 1** | **AAA** | Primary page & heading text |
| Inkwell `#141B29` on Raised Card `#FBF9F4` | Light Card | **16.38 : 1** | **AAA** | Assistant message & stat cards |
| Slate Ink `#3E4656` on Alabaster `#F5F1E8` | Light Ground | **8.41 : 1** | **AAA** | Body paragraphs & snippets |
| Muted Ink `#5A6375` on Alabaster `#F5F1E8` | Light Ground | **5.36 : 1** | **AA+** | Captions, timestamps, placeholders |
| Veridian `#0D6E6E` on Alabaster `#F5F1E8` | Light Ground | **5.36 : 1** | **AA+** | Links, badge labels, active tabs |
| Crisp White `#FFFFFF` on Veridian `#0D6E6E` | Light CTA Fill | **6.05 : 1** | **AA+** | Primary buttons & send action |
| Alabaster `#F5F1E8` on Inkwell `#141B29` | Sidebar & User Bubble | **15.29 : 1** | **AAA** | Sidebar links, user prompts, code blocks |
| Luminous Veridian `#2DD4BF` on Inkwell `#141B29` | Dark / Sidebar | **9.26 : 1** | **AAA** | Dark-surface active highlights |
| Alabaster `#F5F1E8` on Nocturne `#0E141F` | Dark Ground | **16.36 : 1** | **AAA** | Dark mode primary reading copy |
| Inkwell `#141B29` on Luminous `#2DD4BF` | Dark CTA Fill | **9.26 : 1** | **AAA** | Dark mode primary button text |

---

## 4. Target CSS Token Architecture (`src/index.css`)

When ready to implement, replace the `:root`, `.light`, and `@theme` blocks in [`src/index.css`](CampusMate_2-main/src/index.css#L5-L149) with this unified 3-color token table (adding explicit sidebar tokens so Light Mode showcases the 30% Inkwell structural anchor cleanly):

```css
/* =========================================================
   LIGHT MODE (DEFAULT): "Scholarly Studio" (60-30-10)
   60% Alabaster #F5F1E8 | 30% Inkwell #141B29 | 10% Veridian #0D6E6E
   ========================================================= */
:root.light, .light {
  /* 60% Primary Ground & Warm Tonal Surfaces */
  --bg-page: #F5F1E8;
  --bg-surface: #FBF9F4;
  --bg-surface-hover: #EAE4D7;
  --bg-elevated: #FBF9F4;

  /* 30% Dedicated Structural Contrast (Sidebar, User Bubbles, Code Blocks, Split Auth) */
  --bg-structural: #141B29;
  --bg-structural-hover: #1D273B;
  --border-structural: #2A364F;
  --text-on-structural: #F5F1E8;
  --text-on-structural-muted: #9CA8BA;

  /* Typography on 60% Ground */
  --text-primary: #141B29;
  --text-secondary: #3E4656;
  --text-muted: #5A6375;

  /* Borders (Tonal Paper Depth, Zero Muddy Drop Shadows) */
  --border: #D8D0C0;
  --border-strong: #BEB39E;

  /* 10% Single Signal Accent — Deep Veridian Teal */
  --accent: #0D6E6E;
  --accent-hover: #0A5858;
  --accent-text-on-fill: #FFFFFF;
  --accent-cyan: #0D6E6E;        /* mapped to single signal hue */
  --accent-indigo: #141B29;      /* mapped to structural inkwell */
  --accent-muted: #E2F1EF;
  --accent-glow: rgba(13, 110, 110, 0.16);
  --accent-gradient: linear-gradient(135deg, #141B29 0%, #0D6E6E 100%);
  --accent-gradient-vertical: linear-gradient(180deg, #141B29 0%, #0D6E6E 100%);

  /* Glassmorphism Surfaces */
  --bg-glass-navbar: rgba(245, 241, 232, 0.90);
  --bg-glass-panel: rgba(251, 249, 244, 0.96);
  --bg-glass-card: rgba(251, 249, 244, 0.94);

  /* Functional Micro-Telemetry Only (Never Decorative) */
  --status-success: #0D6E6E;
  --status-warning: #B45309;
  --status-danger: #B91C1C;
  --status-info: #0D6E6E;
}

/* =========================================================
   DARK MODE: "Nocturne Ink" (Exact Same 3 Colors Inverted)
   60% Nocturne #0E141F | 30% Slate Ink #141B29 & Alabaster #F5F1E8 | 10% Luminous Veridian #2DD4BF
   ========================================================= */
:root {
  --bg-page: #0E141F;
  --bg-surface: #141B29;
  --bg-surface-hover: #1D273B;
  --bg-elevated: #1D273B;

  --bg-structural: #141B29;
  --bg-structural-hover: #243047;
  --border-structural: #2A364F;
  --text-on-structural: #F5F1E8;
  --text-on-structural-muted: #9CA8BA;

  --text-primary: #F5F1E8;
  --text-secondary: #C4CCDA;
  --text-muted: #8B96A9;

  --border: #253047;
  --border-strong: #364666;

  --accent: #2DD4BF;
  --accent-hover: #14B8A6;
  --accent-text-on-fill: #0E141F;
  --accent-cyan: #2DD4BF;
  --accent-indigo: #1D273B;
  --accent-muted: rgba(45, 212, 191, 0.14);
  --accent-glow: rgba(45, 212, 191, 0.22);
  --accent-gradient: linear-gradient(135deg, #1D273B 0%, #0D6E6E 65%, #2DD4BF 100%);
  --accent-gradient-vertical: linear-gradient(180deg, #1D273B 0%, #0D6E6E 65%, #2DD4BF 100%);

  --bg-glass-navbar: rgba(14, 20, 31, 0.86);
  --bg-glass-panel: rgba(20, 27, 41, 0.94);
  --bg-glass-card: rgba(29, 39, 59, 0.78);

  --status-success: #2DD4BF;
  --status-warning: #F59E0B;
  --status-danger: #EF4444;
  --status-info: #2DD4BF;
}
```

### `@theme` Exposure Additions (for Tailwind v4 Utility Classes)
Expose the structural tokens inside `@theme` so components can write clean utilities without raw hex values:
* `--color-structural: var(--bg-structural);`
* `--color-structural-hover: var(--bg-structural-hover);`
* `--color-border-structural: var(--border-structural);`
* `--color-on-structural: var(--text-on-structural);`
* `--color-on-structural-muted: var(--text-on-structural-muted);`
* `--color-on-accent: var(--accent-text-on-fill);`

---

## 5. Component-by-Component Implementation Plan

### A. Global Shell & Theme Switching
* **[`src/index.css`](CampusMate_2-main/src/index.css)**:
  * Update `.hero-section` light gradient (`#L400-L405`) from `#E0EEFF / #F8FAFC` to subtle warm parchment vignette: `radial-gradient(ellipse 1100px 700px at 50% -10%, rgba(13,110,110,0.08) 0%, #EAE4D7 42%, #F5F1E8 100%)`.
  * Update `.btn-primary-gradient` and `.btn-primary-flat` (`#L415-L438`) to use `color: var(--accent-text-on-fill)` so dark mode crisp `#0E141F` text renders over Luminous `#2DD4BF`, and light mode `#FFFFFF` renders over `#0D6E6E`.
  * Replace `.hover-glass-card` blue glow shadows (`rgba(37, 99, 235, ...)`) with subtle warm ink elevation (`0 2px 10px rgba(20, 27, 41, 0.05)` resting, `0 10px 24px rgba(13, 110, 110, 0.12)` hover).

### B. Student Chat Workspace (High-Impact 60–30–10 Overhaul)
* **[`ChatSidebar.jsx`](CampusMate_2-main/src/components/chat/ChatSidebar.jsx)** *(Becomes the **30% Structural Anchor**)*:
  * **Surface Swap:** Convert `<aside>` from `bg-surface` (white) to `bg-structural text-on-structural border-r border-border-structural`.
  * **Header + Logo:** [`CampusLogo`](CampusMate_2-main/src/components/brand/CampusLogo.jsx) sits directly on `#141B29` Inkwell (ensure brand text uses `text-on-structural` so "CampusMate" stays crisp Parchment while keeping Nexus Prism untouched).
  * **Search Box (`L121`):** `bg-structural-hover border border-border-structural focus:border-accent text-on-structural placeholder-on-structural-muted`.
  * **New Chat CTA (`L130`):** Remove hardcoded `hover:bg-white` -> solid Veridian CTA `bg-accent text-on-accent hover:bg-accent-hover` (single calm signal action!).
  * **Active Conversation Pill (`L301`):** `bg-accent/18 border-accent/50 text-on-structural border-l-3 border-l-accent`.
  * **User Initial Avatar (`L202, L248`):** Replace `from-blue-600 to-indigo-600` with clean Veridian fill `bg-accent text-on-accent`.
* **[`ChatMessage.jsx`](CampusMate_2-main/src/components/chat/ChatMessage.jsx)** *(Fixes Worst Hardcoded White/Blue Leaks)*:
  * **User Bubble (`L92`):** Replace `bg-blue-600 text-white` with **Structural Inkwell** `bg-structural text-on-structural border border-border-structural rounded-2xl rounded-tr-xs`. Looks distinctly scholarly and creates crisp contrast against Parchment!
  * **User Avatar (`L77`):** `bg-structural text-on-structural ring-1 ring-border-strong`.
  * **Assistant Bubble (`L93, L101`):** Replace `bg-white border-slate-200 text-slate-800` with **`bg-surface border border-border-default text-text-primary`** (`#FBF9F4` card over `#F5F1E8` paper — crisp `16.38:1` contrast!).
  * **Retrieved Campus Database Cards (`L129-L202`):** Replace `bg-slate-50 / hover:bg-white / blue-50 / blue-200 / emerald-600` with **`bg-page border-border-default hover:border-accent/50 hover:bg-surface`**:
    * `DOC #1` pill & Database icon: `bg-accent-muted text-accent border-accent/25`.
    * `Grounding Verified` badge (`L144-L147`): Veridian signal `text-accent` with `bg-accent` pulse dot (eliminates 4th green hue!).
    * Inline citations `[1]`, `[2]` rendered inside text styled as monospace chips in `bg-accent-muted text-accent`.
  * **Action Toolbar (`L209-L284`):** Replace `bg-slate-100 / text-slate-500` with `bg-surface border-border-default text-text-muted`; `thumbs-up` highlights Veridian (`text-accent bg-accent-muted`); `thumbs-down` retains subtle micro-telemetry danger (`text-status-danger`).
* **[`ChatContainer.jsx`](CampusMate_2-main/src/components/chat/ChatContainer.jsx)**:
  * **Thinking Indicator Card (`L526-L581`):** Replace hardcoded `bg-white border-slate-200 text-slate-800` and `blue-600`/`emerald-50` pills with `bg-elevated border-border-default text-text-primary`, shimmer bar `bg-accent` on `bg-surface-hover` track, completed stage pills in `bg-accent-muted text-accent border-accent/30`, active stage in `bg-structural text-on-structural border-accent`.
  * **Header RAG Status Pill (`L477-L480`):** Swap `bg-emerald-500` dot to `bg-accent`.
* **[`ChatInput.jsx`](CampusMate_2-main/src/components/chat/ChatInput.jsx)**:
  * **Input Card (`L82`):** `bg-surface border-border-strong/80 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/15` with soft warm backdrop.
  * **Send Button (`L116`):** Solid Veridian `bg-accent hover:bg-accent-hover text-on-accent`.
  * **Model Picker Cards (`L13-L29`):** Strip cyan/fuchsia/rose/purple multi-color gradients! Style the 3 engine badges strictly with the 3-color hierarchy:
    * `direct` (Hybrid RAG Core): `bg-accent-muted text-accent border-accent/30` (Signal Veridian)
    * `groq` (Groq LLaMA-3.3 70B): `bg-structural text-on-structural border-border-structural` (Structural Inkwell)
    * `n8n` (Agentic Flow): `bg-surface-hover text-text-primary border-border-strong` (Tonal Paper)
* **[`ChatEmptyState.jsx`](CampusMate_2-main/src/components/chat/ChatEmptyState.jsx) & [`SourceModal.jsx`](CampusMate_2-main/src/components/chat/SourceModal.jsx)**:
  * Switch `bg-emerald-500` online dot (`L82`) to `bg-accent`.
  * Empty-state prompt cards (`L150`) sit cleanly as `#FBF9F4` cards (`bg-surface`) over `#F5F1E8` Parchment (`bg-page`) with monospace query previews in `text-text-muted` and Veridian category tags.
* **[`MarkdownRenderer.jsx`](CampusMate_2-main/src/components/chat/MarkdownRenderer.jsx)**:
  * Code blocks (`L14-L29`) use `bg-structural` header (`#141B29`) + darker `#0E141F` body with `#F5F1E8` code text (matches Dark Mode ground automatically!).
  * Inline `` `code` `` chips (`L194`) use `bg-surface-hover border-border-default text-accent font-mono` (subtle warm parchment pill with sharp Veridian text — ideal for `2CEIT601`, `ROOM-DA-202`, `75%`).

### C. Auth, Marketing Landing & Admin Surfaces
* **[`Login.jsx`](CampusMate_2-main/src/components/Login.jsx)** *(True 30/60/10 Editorial Split)*:
  * **Left 40% Panel (`L199`):** Convert from `bg-page` to **Structural Inkwell `bg-structural text-on-structural`**, replacing `AuroraBlob()` (`L16` `#1D4ED8/#3B82F6/#38BDF8`) with a restrained deep Veridian ambient radial wash (`rgba(13, 110, 110, 0.28)`).
  * **Right 60% Form Canvas:** Clean `#F5F1E8` Parchment with `#FBF9F4` inputs (`bg-surface border-border-default`) replacing broken `bg-white/5` (`L357, L391` — note `bg-white/5` was invisible on white in light mode!).
  * Remove `purple-500/600` on Admin demo pill (`L335`) -> style with `bg-structural text-on-structural`.
* **[`Hero.jsx`](CampusMate_2-main/src/components/Hero.jsx), [`Navbar.jsx`](CampusMate_2-main/src/components/Navbar.jsx), [`ProductShowcase.jsx`](CampusMate_2-main/src/components/ProductShowcase.jsx), [`TechPipeline.jsx`](CampusMate_2-main/src/components/TechPipeline.jsx), [`TechStackDeck.jsx`](CampusMate_2-main/src/components/TechStackDeck.jsx), [`Footer.jsx`](CampusMate_2-main/src/components/Footer.jsx)**:
  * Replace hardcoded `rgba(59,130,246,0.12)` cursor glow (`Hero.jsx#L110`) with `var(--accent-glow)`.
  * Once `src/index.css` maps `--accent`, `--accent-cyan`, and `--accent-indigo` to our 3-color system, SVG connection lines and particle rings in `TechPipeline.jsx` (`L10-L48`, `L216-L278`) and cards in `TechStackDeck.jsx` automatically harmonize cleanly with Inkwell & Veridian without editing SVG coordinates!
* **[`AdminDashboard.jsx`](CampusMate_2-main/src/components/AdminDashboard.jsx)**:
  * Stat cards (`L53-L60`) remain crisp `#FBF9F4` cards on `#F5F1E8` Parchment; keep `status-warning` and `status-danger` solely for unverified user counts & error alerts while `verified` and `indexed` telemetry converge onto Veridian (`--accent`).

---

## 6. Typography & Micro-Surface Hierarchy (No Color Bloat Required)

To make a 3-color palette feel **bespoke and expensive**, contrast must come from **type weight, spacing, and hairline geometry** rather than adding 4th/5th accent colors:
1. **Mono Metadata Discipline:** Course codes (`2CEIT601`), room IDs (`ROOM-DA-202`), document tags (`DOC #1`), latency telemetry (`42ms`), and citation markers `[1]` consistently render in monospace (`font-mono text-[11px] tracking-tight`) inside `#EAE4D7` or Veridian-tinted chips.
2. **Hairline Border Architecture:** Prefer `1px solid var(--border)` (`#D8D0C0`) + crisp `border-t`/`border-r` dividers over heavy diffused CSS drop shadows. Warm paper + dark ink needs minimal shadow to establish clear Z-axis elevation.
3. **Reserved Gradient Usage:** Ban rainbow text/button gradients across standard dashboard chrome (`ChatSidebar`, `ChatMessage`, `ChatInput`, `AdminDashboard`); reserve `--accent-gradient` **solely** for the Hero headline accent word (`Hero.jsx#L134`) and Landing CTA button (`Hero.jsx#L156`) plus the preserved SVG prism mark (`CampusLogo.jsx`).

---

## 7. Pre-Implementation Checklist (When Approved to Build)
1. **Phase 1 — Token Foundation:** Update [`src/index.css`](CampusMate_2-main/src/index.css) with the Scholarly Studio (Light) & Nocturne Ink (Dark) CSS variables + Tailwind `@theme` utilities.
2. **Phase 2 — Purge Hardcoded Overrides:** Refactor [`ChatMessage.jsx`](CampusMate_2-main/src/components/chat/ChatMessage.jsx), [`ChatContainer.jsx`](CampusMate_2-main/src/components/chat/ChatContainer.jsx), [`ChatSidebar.jsx`](CampusMate_2-main/src/components/chat/ChatSidebar.jsx), [`ChatInput.jsx`](CampusMate_2-main/src/components/chat/ChatInput.jsx), [`MarkdownRenderer.jsx`](CampusMate_2-main/src/components/chat/MarkdownRenderer.jsx), and [`Login.jsx`](CampusMate_2-main/src/components/Login.jsx) so 0 hardcoded `bg-white` / `bg-blue-*` / `bg-slate-*` / `purple-*` / `fuchsia-*` overrides remain.
3. **Phase 3 — Contrast & Visual Verification:** Test Light Mode (`#F5F1E8` / `#141B29` / `#0D6E6E`) and Dark Mode (`#0E141F` / `#F5F1E8` / `#2DD4BF`) across `/`, `/login`, `/dashboard/student`, and `/dashboard/admin` at desktop + mobile widths, verifying `npm run build` passes cleanly with zero broken classes.
