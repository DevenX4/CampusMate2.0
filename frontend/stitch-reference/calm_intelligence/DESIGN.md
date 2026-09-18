---
name: Calm Intelligence
colors:
  surface: '#faf9f7'
  surface-dim: '#dadad8'
  surface-bright: '#faf9f7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f1'
  surface-container: '#efeeec'
  surface-container-high: '#e9e8e6'
  surface-container-highest: '#e3e2e0'
  on-surface: '#1a1c1b'
  on-surface-variant: '#444651'
  inverse-surface: '#2f3130'
  inverse-on-surface: '#f1f1ef'
  outline: '#757682'
  outline-variant: '#c5c5d3'
  surface-tint: '#4059aa'
  primary: '#00236f'
  on-primary: '#ffffff'
  primary-container: '#1e3a8a'
  on-primary-container: '#90a8ff'
  inverse-primary: '#b6c4ff'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fc'
  on-secondary-container: '#57657a'
  tertiary: '#4b1c00'
  on-tertiary: '#ffffff'
  tertiary-container: '#6e2c00'
  on-tertiary-container: '#f39461'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b6c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#264191'
  secondary-fixed: '#d5e3fc'
  secondary-fixed-dim: '#b9c7df'
  on-secondary-fixed: '#0d1c2e'
  on-secondary-fixed-variant: '#3a485b'
  tertiary-fixed: '#ffdbcb'
  tertiary-fixed-dim: '#ffb691'
  on-tertiary-fixed: '#341100'
  on-tertiary-fixed-variant: '#773205'
  background: '#faf9f7'
  on-background: '#1a1c1b'
  surface-variant: '#e3e2e0'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '500'
    lineHeight: 56px
    letterSpacing: -0.03em
  headline-xl-mobile:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '500'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '500'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 26px
    fontWeight: '500'
    lineHeight: 34px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Geist
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 17px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Geist
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-sm:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  label-md:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: -0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system delivers a calm, hyper-minimal environment engineered for focused synthesis, deep knowledge retrieval, and fluid human-AI collaboration. Drawing inspiration from the quiet restraint of Notion, the micro-precision of Linear, and the fluid simplicity of modern AI engines, the design prioritizes raw content and cognitive flow over extraneous decoration.

### Aesthetics & Tone
- **Atmospheric & Restrained:** Surfaces feel like warm architectural parchment rather than cold digital screens.
- **Content-Centric:** Chrome and scaffolding disappear into the background; interactive triggers reveal themselves contextually.
- **Confident Subtlety:** Hierarchy is established through whitespace, precise weight transitions, and scale rather than loud color fills or thick dividers.
- **Unobtrusive Intelligence:** Conversational states, streaming tokens, and cited sources feel seamless, grounded, and authoritative.

## Colors

The palette operates on a principle of monastic restraint: 95% neutral surfaces and ink tones, accented sparingly by a collegiate sapphire blue reserved solely for intent, focus states, and verified source provenance.

### Light Mode Surfaces
- **Canvas Base:** `#F9F8F6` (Warm Stone / Alabaster)
- **Surface Elevated:** `#FFFFFF` (Pure White layer for cards, floating menus, and input blocks)
- **Hairline Border:** `rgba(28, 25, 23, 0.06)`

### Dark Mode Surfaces
- **Canvas Base:** `#0F1115` (Deep Void Charcoal)
- **Surface Elevated:** `#181B20` (Subtle Ink Tone)
- **Hairline Border:** `rgba(255, 255, 255, 0.08)`

### Text & Ink Hierarchy
- **Ink Primary:** Light `#18181B` / Dark `#F4F4F5` (High-clarity reading tone)
- **Ink Secondary:** Light `#52525B` / Dark `#A1A1AA` (Contextual descriptors, metadata, subheaders)
- **Ink Muted:** Light `#71717A` / Dark `#71717A` (Timestamps, keyboard shortcuts, disabled cues)

### Accent Roles
- **Sapphire Accent (`#1E3A8A` light / `#60A5FA` dark):** Restricted strictly to the primary submission trigger, system status indicators, interactive citation badges, and accessible focus rings. Never used for decorative card backgrounds or multi-colored tags.

## Typography

Typography acts as the primary architectural element of the system. `Geist` provides an impeccably engineered grotesque skeleton with clean optical tracking, neutral terminals, and balanced numerals suited for synthesis and deep prose.

### Rules of Engagement
- **Headline Rhythm:** Headings rely on tight tracking (`-0.03em` to `-0.01em`) and restrained medium (`500`) weights. Avoid heavy bold or black weights.
- **Prose Breathing Room:** Paragraphs utilize an open line height (`1.6x` to `1.65x`) to preserve optical stamina during long conversational streams or research syntheses.
- **Monospace Integration:** `JetBrains Mono` is utilized strictly for raw markdown expressions, prompt tokens, source index keys, and technical outputs.

## Layout & Spacing

The layout philosophy centers on focused reading canals rather than sprawling dashboards. The interface shifts fluidly between a single-column, centered reading river and an expansive dual-pane workspace.

### Grid & Form Factors
- **The Reading Canal:** AI responses, documents, and chat streams are capped at a maximum width of `720px` (`45rem`) to ensure optimal measure for reading comprehension.
- **The Canvas (Desktop):** A dynamic split: an optional collapsible navigation rail (`240px`), the central conversational column (`720px` centered), and an contextual artifact/inspector pane (`420px` fixed or fluid).
- **Tablet / Small Viewports (768px - 1024px):** Artifact panels fold into sliding bottom sheets or overlays. Outer margins adjust to `1.5rem`.
- **Mobile (< 768px):** Single-column layout. Margin resets to `1rem`. The omnibar input sticks to the viewport base with safe-area insets.

## Elevation & Depth

Visual hierarchy is maintained through subtle, warm-tinted ambient shadows and tonal separation, eschewing aggressive drop shadows and heavy borders.

### Depth Hierarchy
1. **Flat Base (Canvas):** Ground layer (`#F9F8F6` light / `#0F1115` dark). Receives zero shadow.
2. **Layered Tile (Cards & Code Blocks):** Elevated base with a single hairline border (`1px solid rgba(28, 25, 23, 0.06)`). Shadow is whisper-light: `0 1px 2px rgba(0, 0, 0, 0.03)`.
3. **Floating Interactive (Input Omnibar & Dropdowns):** Centered floating bar elevated above scrolling content. Shadow: `0 12px 32px -8px rgba(0, 0, 0, 0.06), 0 4px 12px -2px rgba(0, 0, 0, 0.03)`. 
4. **Modals & Command Palettes:** High-elevation popover with a diffuse spread: `0 24px 48px -12px rgba(0, 0, 0, 0.12)`. Supported by a soft, warm frosted overlay (`backdrop-filter: blur(8px); background: rgba(249, 248, 246, 0.7)`).

## Shapes

The shape system employs geometric precision: smooth, balanced corners that soften digital interaction without veering into toy-like circularity.

- **Primary Components (Inputs, Cards, Panels):** Built with `0.5rem` (`8px`) radii for structured utility.
- **Large Overlays & Modals:** Scaled to `1rem` (`16px`) for an organic, tactile presence.
- **Compact Badges & Micro-Pills:** Use `9999px` strictly for citation tags, status capsules, and quick-prompt pills to distinguish them from actionable square inputs.

## Components

### Buttons
- **Primary:** Solid dark ink background (`#18181B` in light mode, `#F4F4F5` in dark mode) with contrasting text. No gradients. Hover state brings a subtle 4% brightness shift.
- **Secondary / Ghost:** Transparent background with subtle hover reveal (`rgba(0, 0, 0, 0.04)` in light mode). No idle border.
- **Action Triggers:** Sapphire accent is reserved exclusively for system execution states (e.g., "Run Analysis" or "Send Prompt").

### Omnibar & Input Fields
- **Floating Conversational Input:** Expands vertically with text length. Features an interior hairline border, elevated white surface, and nested inline tool actions (voice, file upload, model toggle).
- **Focus States:** Focused inputs transition their hairline border to a discrete sapphire ring (`box-shadow: 0 0 0 1.5px #1E3A8A`).

### Citation Badges & Sourcing
- **Micro-Badges:** Rounded pill format (`roundedness: 9999px`), height `20px`. Subtle sapphire background tint (`rgba(30, 58, 138, 0.06)`), sapphire text (`#1E3A8A`), displaying source index or favicon.
- **Popover Preview:** Hovering a citation surfaces an ambient card with source title, snippet, and domain authority without leaving the context canal.

### Cards & Artifacts
- **AI Output Artifacts:** Code sandboxes, markdown synthesis summaries, and table previews render in minimal containers bound by hairline borders. No outer card wrapping for plain conversational text.
- **Checkboxes & Radios:** Minimal geometric markers. Subtle grey hairline in neutral state; fills with sapphire accent only when selected.

### Lists & Key-Value Syntheses
- Lists discard classic bullets in favor of soft dash glyphs or clean numeric counters. Data grids avoid full-cell gridlines, relying on balanced vertical tracking and subtle horizontal divider hairlines (`rgba(0, 0, 0, 0.04)`).