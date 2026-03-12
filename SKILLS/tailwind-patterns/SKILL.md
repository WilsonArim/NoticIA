---
name: Tailwind Patterns
description: Tailwind CSS v4 patterns, utility conventions, and component styling approaches
phase: 4
---

# Tailwind Patterns -- Tailwind CSS v4

## Tailwind v4 Key Changes

Tailwind v4 moves from JavaScript config to a CSS-first configuration model. The `tailwind.config.js` file is replaced by CSS directives.

### CSS-First Configuration with @theme

```css
/* app/globals.css */
@import "tailwindcss";

@theme {
  /* Colors */
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-primary-foreground: #ffffff;
  --color-secondary: #6b7280;
  --color-destructive: #ef4444;
  --color-background: #ffffff;
  --color-foreground: #0a0a0a;
  --color-muted: #f5f5f5;
  --color-muted-foreground: #737373;
  --color-border: #e5e5e5;
  --color-ring: #3b82f6;

  /* Typography */
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", monospace;

  /* Border radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);

  /* Custom spacing if needed beyond defaults */
  --spacing-18: 4.5rem;
  --spacing-88: 22rem;
}
```

### What Changed from v3 to v4

| Aspect              | v3                              | v4                              |
|---------------------|--------------------------------|---------------------------------|
| Configuration       | `tailwind.config.js`           | `@theme` in CSS                 |
| Import              | `@tailwind base/components/utilities` | `@import "tailwindcss"`    |
| Custom colors       | JS config `theme.extend.colors`| `--color-*` in `@theme`        |
| Plugins             | JS plugin API                  | CSS `@plugin` directive         |
| Container queries   | Plugin required                | Built-in `@container`           |
| CSS variables       | Manual setup                   | Native throughout               |
| Dark mode           | `darkMode: "class"`            | Automatic via `prefers-color-scheme` or `@variant dark` |

## Utility Patterns

### Layout Utilities

```html
<!-- Centered page content with max width -->
<main class="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">

<!-- Full-height page with sticky footer -->
<div class="grid min-h-screen grid-rows-[auto_1fr_auto]">

<!-- Responsive card grid -->
<div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">

<!-- Sidebar layout -->
<div class="flex">
  <aside class="w-64 shrink-0 border-r">Sidebar</aside>
  <main class="flex-1 p-6">Content</main>
</div>
```

### Typography Utilities

```html
<!-- Heading with proper tracking and weight -->
<h1 class="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">

<!-- Body text with constrained width -->
<p class="max-w-prose text-base leading-relaxed text-muted-foreground">

<!-- Truncated text (single line) -->
<span class="truncate block max-w-xs">

<!-- Clamped text (multi-line) -->
<p class="line-clamp-3">
```

### Spacing Utilities

```html
<!-- Consistent vertical stack spacing -->
<div class="space-y-4">

<!-- Card with balanced padding -->
<div class="p-4 sm:p-6">

<!-- Inline items with gap -->
<div class="flex items-center gap-2">
```

## Responsive Design Utilities

Use mobile-first breakpoints. Write the mobile style first, then override at larger sizes.

```html
<!-- Responsive text sizing -->
<h1 class="text-2xl sm:text-3xl lg:text-4xl">

<!-- Responsive grid -->
<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">

<!-- Responsive padding -->
<section class="px-4 py-8 sm:px-6 sm:py-12 lg:px-8 lg:py-16">

<!-- Show/hide based on viewport -->
<nav class="hidden lg:flex">Desktop Nav</nav>
<button class="lg:hidden">Menu</button>

<!-- Responsive flex direction -->
<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
```

## Dark Mode Setup

### Tailwind v4 Dark Mode

In v4, dark mode uses `prefers-color-scheme` by default. For manual toggle support, use the `dark` variant with a class-based strategy.

```css
/* Enable class-based dark mode in v4 */
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --color-background: #ffffff;
  --color-foreground: #0a0a0a;
  --color-surface: #ffffff;
  --color-muted: #f5f5f5;
}

/* Override tokens for dark mode */
.dark {
  --color-background: #0a0a0a;
  --color-foreground: #fafafa;
  --color-surface: #171717;
  --color-muted: #262626;
}
```

```html
<!-- Components automatically adapt via semantic tokens -->
<div class="bg-background text-foreground">
  <div class="bg-surface border border-border rounded-lg p-4">
    <p class="text-muted-foreground">This adapts to dark mode automatically.</p>
  </div>
</div>
```

## Component Patterns

### Card

```html
<div class="rounded-lg border border-border bg-surface p-6 shadow-sm">
  <h3 class="text-lg font-semibold text-foreground">Card Title</h3>
  <p class="mt-2 text-sm text-muted-foreground">Card description text.</p>
  <div class="mt-4 flex gap-2">
    <button class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary-hover">
      Action
    </button>
  </div>
</div>
```

### Button Variants

```html
<!-- Primary -->
<button class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50">
  Primary
</button>

<!-- Outline -->
<button class="inline-flex items-center justify-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
  Outline
</button>

<!-- Ghost -->
<button class="inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
  Ghost
</button>
```

### Form Input

```html
<div class="space-y-2">
  <label for="email" class="text-sm font-medium text-foreground">Email</label>
  <input
    id="email"
    type="email"
    placeholder="you@example.com"
    class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
  />
  <p class="text-xs text-muted-foreground">We will never share your email.</p>
</div>
```

## Custom Utilities

### The `cn()` Helper Pattern

The `cn()` utility merges Tailwind classes intelligently, resolving conflicts (e.g., `px-2` and `px-4` collapse to `px-4`).

```ts
// lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Usage:**

```tsx
// Merge base styles with conditional and override classes
<div className={cn(
  "rounded-lg border p-4",
  isActive && "border-primary bg-primary/5",
  className // allow consumer overrides
)} />
```

**Why both `clsx` and `twMerge`?**
- `clsx` handles conditional class joining (booleans, arrays, objects).
- `twMerge` resolves Tailwind-specific conflicts (`p-2 p-4` becomes `p-4`).

## Class Organization Convention

Order Tailwind classes consistently for readability. Follow this grouping convention:

```
1. Layout       -- display, position, grid, flex, float
2. Box model    -- width, height, margin, padding, border
3. Typography   -- font, text, leading, tracking
4. Visual       -- background, shadow, opacity, rounded
5. Interactivity-- cursor, pointer-events, select
6. Transitions  -- transition, duration, ease
7. State        -- hover:, focus:, active:, disabled:
8. Responsive   -- sm:, md:, lg:, xl:
```

Example with organized classes:

```html
<button class="
  inline-flex items-center justify-center
  h-10 px-4 rounded-md border
  text-sm font-medium text-foreground
  bg-background shadow-sm
  cursor-pointer
  transition-colors duration-150
  hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50
">
  Button
</button>
```

**Tip:** Use the `prettier-plugin-tailwindcss` plugin to automatically sort classes in a consistent order across the project. This eliminates debates about class ordering.

```bash
npm install -D prettier-plugin-tailwindcss
```
