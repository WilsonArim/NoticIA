---
name: UI/UX Pro Max
description: Design systems, design tokens, layout patterns, and interaction states
phase: 4
---

# UI/UX Pro Max -- Design Systems, Tokens, and Layouts

## Design Token Structure

Design tokens are the atomic values that define the visual language of your system. They are organized in layers of abstraction.

### Token Layers

```
Primitive Tokens  -->  Semantic Tokens  -->  Component Tokens
(raw values)          (contextual meaning)   (specific usage)

blue-500: #3b82f6     primary: blue-500      button-bg-primary: primary
gray-100: #f3f4f6     muted: gray-100        card-bg: muted
```

### Color Tokens

```css
/* Primitive (never reference directly in components) */
--blue-50: #eff6ff;
--blue-500: #3b82f6;
--blue-600: #2563eb;
--gray-50: #f9fafb;
--gray-200: #e5e7eb;
--gray-900: #111827;

/* Semantic (use these in component styles) */
--color-primary: var(--blue-500);
--color-primary-hover: var(--blue-600);
--color-background: var(--gray-50);
--color-surface: #ffffff;
--color-border: var(--gray-200);
--color-text-primary: var(--gray-900);
--color-text-secondary: var(--gray-600);
--color-destructive: var(--red-500);
--color-success: var(--green-500);

/* Dark mode overrides swap semantic values */
[data-theme="dark"] {
  --color-background: var(--gray-900);
  --color-surface: var(--gray-800);
  --color-border: var(--gray-700);
  --color-text-primary: var(--gray-50);
}
```

### Spacing Tokens

```css
--space-0: 0;
--space-px: 1px;
--space-0.5: 2px;
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
```

### Typography Tokens

```css
--font-sans: "Inter", system-ui, sans-serif;
--font-mono: "JetBrains Mono", monospace;

--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
--text-2xl: 1.5rem;    /* 24px */
--text-3xl: 1.875rem;  /* 30px */

--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.625;

--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Shadow Tokens

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);

/* Elevation system (prefer named elevations over raw shadows) */
--elevation-raised: var(--shadow-sm);   /* cards, buttons */
--elevation-overlay: var(--shadow-md);  /* dropdowns, popovers */
--elevation-modal: var(--shadow-xl);    /* modals, dialogs */
```

## Component Library Patterns

### Compound Component Pattern

Use compound components for complex UI elements that share implicit state.

```tsx
// Usage
<Select value={value} onValueChange={setValue}>
  <Select.Trigger>
    <Select.Value placeholder="Choose..." />
  </Select.Trigger>
  <Select.Content>
    <Select.Item value="a">Option A</Select.Item>
    <Select.Item value="b">Option B</Select.Item>
  </Select.Content>
</Select>
```

### Variant Pattern with CVA

Use `class-variance-authority` to manage component variants systematically.

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-input bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);
```

## Layout System

### Grid Patterns

```tsx
// Standard content grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {items.map((item) => <Card key={item.id} {...item} />)}
</div>

// Sidebar layout
<div className="grid grid-cols-[280px_1fr] gap-0">
  <aside className="border-r h-screen sticky top-0">Sidebar</aside>
  <main className="p-8">Content</main>
</div>

// Holy grail layout
<div className="grid grid-rows-[auto_1fr_auto] min-h-screen">
  <header>Header</header>
  <main>Content</main>
  <footer>Footer</footer>
</div>
```

### Flexbox Patterns

```tsx
// Centered content (horizontal and vertical)
<div className="flex items-center justify-center min-h-screen" />

// Space between header items
<header className="flex items-center justify-between px-6 h-16" />

// Stack with consistent gap
<div className="flex flex-col gap-4" />

// Inline list that wraps
<div className="flex flex-wrap gap-2" />
```

## Micro-Interactions

Micro-interactions provide feedback and make the interface feel responsive. Keep them subtle and purposeful.

```css
/* Button press feedback */
.button:active {
  transform: scale(0.97);
}

/* Smooth state transitions */
.interactive {
  transition: background-color 150ms ease, color 150ms ease, border-color 150ms ease;
}

/* Entrance animation for new content */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeInUp 200ms ease-out; }
```

**Rules for micro-interactions:**
- Duration should be 100-300ms. Anything longer feels sluggish.
- Use `ease-out` for entrances, `ease-in` for exits.
- Always respect `prefers-reduced-motion` by disabling or simplifying animations.
- Never animate layout properties (width, height, top, left) -- use transform and opacity.

## Loading Patterns

### Skeleton Loading

```tsx
function PostCardSkeleton() {
  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
      <div className="h-3 w-full rounded bg-muted animate-pulse" />
      <div className="h-3 w-5/6 rounded bg-muted animate-pulse" />
      <div className="h-3 w-2/3 rounded bg-muted animate-pulse" />
    </div>
  );
}
```

Skeleton loaders should mirror the exact shape and layout of the content they replace. This prevents layout shift when real content loads.

### Shimmer Effect

```css
.shimmer {
  background: linear-gradient(90deg, var(--muted) 25%, var(--muted-light) 50%, var(--muted) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

## Empty States

Every list, table, and data view must have a designed empty state. An empty state includes:

1. **Illustration or icon** -- a visual cue that the area is intentionally empty.
2. **Headline** -- what the user is looking at ("No projects yet").
3. **Description** -- brief explanation or guidance ("Create your first project to get started").
4. **Action** -- a primary button to resolve the empty state ("Create Project").

```tsx
function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Icon className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
```

## Error States

### Error State Hierarchy

1. **Field-level errors** -- inline, directly below the input, red text with icon.
2. **Form-level errors** -- banner at top of form summarizing issues.
3. **Section-level errors** -- error boundary replacing the failed section with retry option.
4. **Page-level errors** -- full-page error with navigation back to safety.

### Error State Component Pattern

```tsx
function SectionError({ title, message, onRetry }: SectionErrorProps) {
  return (
    <div role="alert" className="rounded-lg border border-destructive/20 bg-destructive/5 p-6 text-center">
      <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
      <h3 className="font-semibold text-destructive">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-4 text-sm font-medium text-primary hover:underline">
          Try again
        </button>
      )}
    </div>
  );
}
```

**Rules:**
- Error messages should be human-readable, never raw error codes.
- Always provide a recovery path (retry, go back, contact support).
- Log the technical error details to your monitoring system, not to the user.
