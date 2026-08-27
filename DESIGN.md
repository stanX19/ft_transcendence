---
name: LibraryOS
description: A calm, practical interface for discovering and managing a shared library.
colors:
  canvas: "#F6F8FB"
  surface: "#FBFDFF"
  ink: "#0F172A"
  ink-soft: "#1E293B"
  muted: "#475569"
  line: "#CBD5E1"
  accent-50: "#F0F9FF"
  accent-100: "#E0F2FE"
  accent-700: "#0369A1"
  accent-800: "#075985"
  accent-900: "#0C4A6E"
  danger-50: "#FFF1F2"
  danger-700: "#BE185D"
  danger-900: "#881337"
  success-50: "#ECFDF5"
  success-700: "#047857"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 3.75rem)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.75
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.5
rounded:
  control: "12px"
  panel: "24px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-accent:
    backgroundColor: "{colors.accent-700}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "20px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  badge:
    backgroundColor: "{colors.accent-50}"
    textColor: "{colors.accent-900}"
    rounded: "{rounded.pill}"
---

# Design System: LibraryOS

## 1. Overview

**Creative North Star: “The Reading Room, Made Practical”**

LibraryOS should feel like a well-kept reading room: quiet, legible, welcoming,
and arranged around the next useful action. The interface uses generous white
space, a cool neutral canvas, and one restrained blue accent so catalog content
and account state remain easy to scan.

The visual language is deliberately practical rather than ornamental. Panels
provide gentle structure, controls have clear focus and disabled states, and
status messages explain what happened. The system rejects noisy dashboards,
neon color, decorative gradients, and dense controls that make a library feel
like an operations console.

**Key Characteristics:**

- Calm, cool neutrals with a single library-blue accent.
- Short, reusable spacing and radius scales.
- Clear hierarchy with Inter and familiar system fallbacks.
- Semantic states for loading, empty, success, and error feedback.

## 2. Colors

The palette keeps most of each screen neutral and reserves the blue accent for
navigation, primary actions, focus, and catalog context.

### Primary

- **Library Blue** (#0369A1): Primary actions, focus rings, links, and the catalog eyebrow.
- **Deep Library Blue** (#0C4A6E): Hover text and high-contrast accent content.

### Neutral

- **Canvas** (#F6F8FB): Page background and low-emphasis asset surfaces.
- **Surface** (#FBFDFF): Cards, forms, navigation, and other readable surfaces.
- **Ink** (#0F172A): Main headings and high-priority actions.
- **Soft Ink** (#1E293B): Supporting headings and long-form content.
- **Muted** (#475569): Descriptions, metadata, labels, and secondary navigation.
- **Line** (#CBD5E1): Borders and dividers.

### Named Rules

**The Quiet Accent Rule.** Keep accent color purposeful. It should guide action
and orientation, not become a background for every surface.

## 3. Typography

**Display Font:** Inter (with ui-sans-serif and system-ui fallbacks)

**Body Font:** Inter (with ui-sans-serif and system-ui fallbacks)

**Character:** Compact, familiar, and highly legible. Weight and spacing create
hierarchy; decorative type treatments are unnecessary.

### Hierarchy

- **Display** (600, `clamp(2.25rem, 5vw, 3.75rem)`, 1.1): Landing statements and major product moments.
- **Headline** (600, `2.25rem`, 1.2): Page titles and feature entry points.
- **Title** (600, `1.125rem`, 1.5): Cards, sections, and book titles.
- **Body** (400, `1rem`, 1.75): Descriptions and explanatory content, ideally no wider than 65ch.
- **Label** (500, `0.875rem`, 1.5): Form labels and metadata; uppercase tracking is reserved for small eyebrows.

### Named Rules

**The Readable Measure Rule.** Keep explanatory copy comfortable to read and
let whitespace separate ideas before adding more decoration.

## 4. Elevation

LibraryOS uses a hybrid of tonal layering and very soft ambient elevation.
Surfaces are primarily distinguished by the canvas/surface contrast and a
single line border; the shared panel shadow adds depth without making cards
float above the catalog.

### Shadow Vocabulary

- **Panel** (`0 1px 2px rgb(var(--color-ink) / 0.04), 0 8px 24px rgb(var(--color-ink) / 0.04)`): Default cards, forms, and route messages.

### Named Rules

**The Soft Landing Rule.** Use the panel shadow once per meaningful container;
do not stack shadows on every nested element.

## 5. Components

The shared vocabulary lives in `frontend/src/shared/components/ui.tsx` and is
exported from the local index. Components own interaction states and semantic
tokens so feature pages can focus on behavior.

### Buttons

- **Shape:** 12px control radius with compact, medium, and large spacing.
- **Primary:** Ink background with surface text for the strongest action.
- **Accent:** Library Blue background for catalog and contextual actions.
- **Secondary / Ghost / Danger:** Line-backed secondary action, quiet navigation action, and clearly tinted destructive action.
- **Hover / Focus:** 200ms color transition and a visible accent focus ring; loading disables the action and shows a Lucide spinner.

### Chips

- **Style:** `Badge` uses a pill shape with neutral, accent, success, and danger semantic variants.
- **State:** Badges describe status; they are not used as buttons or as decoration without meaning.

### Cards / Containers

- **Corner Style:** 24px panel radius; use the tinted tone for an intentional form or contextual block.
- **Background:** Surface by default, canvas/accent tint only for supporting context.
- **Shadow Strategy:** Use the shared panel elevation and line border.
- **Internal Padding:** 20px as the common card rhythm, with 32px on focused account panels.

### Inputs / Fields

- **Style:** Surface fill, line border, 12px radius, and 10px vertical padding.
- **Focus:** Accent border and a soft accent ring with the global visible outline preserved.
- **Error / Disabled:** ErrorAlert carries the message; controls use reduced opacity and a disabled cursor.

### Navigation

Navigation stays inline and wraps on narrow screens. Links use muted text at rest,
ink on hover, and the shared button vocabulary for the strongest account action.

### Feedback States

`LoadingState`, `EmptyState`, `ErrorAlert`, and `Notice` give every server-backed
view a predictable status treatment with appropriate ARIA roles.

## 6. Do's and Don'ts

### Do:

- **Do** use semantic tokens (`bg-canvas`, `bg-surface`, `text-ink`, `text-muted`, `border-line`) instead of inventing one-off palette values.
- **Do** reuse `Button`, `Card`, field controls, and feedback states before writing a new local pattern.
- **Do** preserve the 12px control radius, 24px panel radius, and visible accent focus ring.
- **Do** keep actions explicit, labels associated with inputs, and loading/empty/error states intentional.

### Don't:

- **Don't** replace the quiet palette with neon accents, decorative gradients, or a dark operations-console aesthetic.
- **Don't** stack shadows, add heavy borders, or turn every piece of metadata into a badge.
- **Don't** use raw color utilities when a semantic token already expresses the role.
- **Don't** hide disabled, loading, empty, or error states behind a blank screen.
