---
name: Frontend Design
description: UI guidelines, visual hierarchy, spacing systems, and accessibility standards
phase: 4
---

# Frontend Design -- UI Guidelines and Aesthetics

## Visual Hierarchy Principles

Visual hierarchy directs the user's eye through content in order of importance. Apply these rules consistently:

1. **Size:** larger elements draw attention first. Use a clear size progression for headings, body, and captions.
2. **Weight:** bold text commands more attention than regular weight at the same size.
3. **Color and contrast:** high-contrast elements stand out. Use accent colors sparingly for calls to action.
4. **Spacing:** more whitespace around an element increases its visual importance and separates content groups.
5. **Position:** top-left is read first in LTR languages. Place primary actions in expected scan paths (F-pattern, Z-pattern).

**Practical rule:** every screen should have exactly one primary focal point. If everything is emphasized, nothing is.

## Spacing System (4px / 8px Grid)

All spacing values should derive from a base-4 or base-8 scale. This creates visual rhythm and consistency.

| Token     | Value | Usage                                    |
|-----------|-------|------------------------------------------|
| `space-1` | 4px   | Tight inline spacing, icon gaps          |
| `space-2` | 8px   | Default gap between related elements     |
| `space-3` | 12px  | Input padding, small card padding        |
| `space-4` | 16px  | Standard card padding, section gaps      |
| `space-5` | 20px  | Medium section separation                |
| `space-6` | 24px  | Large section padding                    |
| `space-8` | 32px  | Section dividers, layout gaps            |
| `space-10`| 40px  | Major section separation                 |
| `space-12`| 48px  | Page-level vertical rhythm               |
| `space-16`| 64px  | Hero spacing, large layout gaps          |

**Rules:**
- Never use arbitrary pixel values. Always reference the spacing scale.
- Padding inside a container should be consistent on all sides (or symmetric horizontal/vertical).
- Spacing between sibling elements should use `gap` rather than margins on individual items.

## Color Theory Basics

### Functional Color Palette Structure

```
Primary      -- Brand identity, primary CTAs, active states
Secondary    -- Supporting actions, secondary navigation
Accent       -- Highlights, badges, notifications
Destructive  -- Errors, delete actions, warnings
Muted        -- Backgrounds, disabled states, borders
Foreground   -- Text colors (primary, secondary, muted)
Background   -- Surface colors (page, card, elevated)
```

### Color Usage Guidelines

- **Primary color** appears on no more than 10-15% of the visible screen area.
- **Neutral tones** (grays, muted backgrounds) should dominate at 60-70%.
- **Accent and destructive colors** are used for 5% or less, only where they need immediate attention.
- Always define both light and dark variants for every semantic color.
- Test colors against real content, not empty mockups.

## Typography Scale

Use a modular scale (ratio 1.25 or 1.333) for consistent type sizing:

| Level    | Size   | Line Height | Weight   | Usage                     |
|----------|--------|-------------|----------|---------------------------|
| `xs`     | 12px   | 16px        | Regular  | Captions, helper text     |
| `sm`     | 14px   | 20px        | Regular  | Secondary text, labels    |
| `base`   | 16px   | 24px        | Regular  | Body text (default)       |
| `lg`     | 18px   | 28px        | Medium   | Lead paragraphs           |
| `xl`     | 20px   | 28px        | Semibold | Card titles, sub-headings |
| `2xl`    | 24px   | 32px        | Semibold | Section headings (h3)     |
| `3xl`    | 30px   | 36px        | Bold     | Page headings (h2)        |
| `4xl`    | 36px   | 40px        | Bold     | Hero headings (h1)        |

**Rules:**
- Limit to 2 font families maximum (one for headings, one for body, or a single versatile family).
- Body text line length should be 45-75 characters for readability.
- Paragraph spacing should be 1.5x the line height of the text.

## Responsive Design Breakpoints

Adopt a mobile-first approach. Define breakpoints at content-driven thresholds:

| Name   | Min Width | Typical Devices             |
|--------|----------|-----------------------------|
| `sm`   | 640px    | Large phones (landscape)    |
| `md`   | 768px    | Tablets (portrait)          |
| `lg`   | 1024px   | Tablets (landscape), laptops|
| `xl`   | 1280px   | Desktops                    |
| `2xl`  | 1536px   | Large desktops              |

**Guidelines:**
- Design for mobile first, then progressively add layout complexity at wider breakpoints.
- Navigation should collapse into a hamburger/drawer below `lg`.
- Grid layouts should reduce columns: 4 cols at `xl`, 3 at `lg`, 2 at `md`, 1 at `sm`.
- Touch targets must be at least 44x44px on mobile.
- Test at real device widths, not just browser resize.

## Accessibility (WCAG 2.1 AA)

### Contrast Ratios

| Content Type             | Minimum Ratio | Recommended |
|--------------------------|---------------|-------------|
| Normal text (< 18px)     | 4.5:1         | 7:1         |
| Large text (>= 18px bold or >= 24px) | 3:1 | 4.5:1    |
| UI components and icons  | 3:1           | 4.5:1       |
| Decorative elements      | No requirement| --          |

Tools to verify contrast: WebAIM Contrast Checker, Chrome DevTools Accessibility pane, Figma plugins (Stark, A11y).

### Focus Management

- Every interactive element must have a visible focus indicator.
- Focus indicator should have at least 3:1 contrast against the surrounding background.
- Use `focus-visible` (not `focus`) to show focus rings only for keyboard navigation.
- Implement logical tab order that follows visual reading order.
- When opening modals, move focus to the modal. On close, return focus to the triggering element.
- Skip-to-content links should be the first focusable element on every page.

### Essential Accessibility Checklist

1. All images have descriptive `alt` text (or `alt=""` if purely decorative).
2. Form inputs have associated `<label>` elements (not just placeholder text).
3. Error messages are announced to screen readers via `aria-live="assertive"` or `role="alert"`.
4. Color is never the sole means of conveying information (add icons, text, or patterns).
5. Page has a single `<h1>`, and heading levels are sequential (no skipping from h1 to h3).
6. Interactive elements are reachable and operable with keyboard alone.
7. Motion and animation respect `prefers-reduced-motion`.
8. Touch targets are at minimum 44x44 CSS pixels with adequate spacing.

## Design Review Checklist

Before shipping any UI, verify the following:

- [ ] Visual hierarchy is clear -- one primary action per view
- [ ] Spacing follows the 4px/8px grid consistently
- [ ] Typography uses the defined scale, no arbitrary sizes
- [ ] Color contrast passes WCAG AA for all text and interactive elements
- [ ] Responsive layout tested at all defined breakpoints
- [ ] Focus states are visible and logical
- [ ] Loading, empty, and error states are designed
- [ ] Animations respect `prefers-reduced-motion`
