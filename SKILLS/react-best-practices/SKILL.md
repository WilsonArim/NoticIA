---
name: React Best Practices
description: React and Next.js performance optimization patterns and state management guidelines
phase: 4
---

# React Best Practices -- Performance Optimization

## Memoization Guidelines: When NOT to Use

Memoization (memo, useMemo, useCallback) has a cost. It consumes memory, adds code complexity, and can mask real performance issues. Follow these rules.

### Do NOT memoize when:

1. **The component is cheap to render.** If a component returns simple JSX with no expensive computation, wrapping it in `memo` adds overhead for zero gain.
2. **Props change on every render anyway.** If you pass a new object/array literal as props, `memo` will always see changed props and re-render regardless.
3. **The value is a primitive.** Strings, numbers, and booleans are compared by value. No need for `useMemo` on `const total = a + b`.
4. **You are prematurely optimizing.** Profile first with React DevTools Profiler. Only memoize components that actually cause measured performance problems.

### DO memoize when:

1. **Expensive computations** -- `useMemo` for filtering/sorting large lists, complex calculations.
2. **Stable callback references** -- `useCallback` when passing callbacks to memoized child components or as dependencies to effects.
3. **Large subtrees** -- `memo` for component trees that are expensive to re-render and receive stable props.
4. **Context consumers** -- memoize components that consume context to prevent cascading re-renders.

```tsx
// BAD: memoizing a trivial component
const Label = memo(({ text }: { text: string }) => <span>{text}</span>);

// GOOD: memoizing an expensive list
const ExpensiveList = memo(({ items }: { items: Item[] }) => (
  <ul>{items.map((item) => <ComplexRow key={item.id} item={item} />)}</ul>
));

// GOOD: useMemo for expensive filtering
const filtered = useMemo(
  () => items.filter((item) => matchesSearch(item, query)),
  [items, query]
);
```

## React Compiler (React 19)

React 19 includes an experimental compiler that automatically memoizes components and hooks. When enabled:

- The compiler analyzes your code at build time and inserts memoization where beneficial.
- You can **remove** most manual `useMemo`, `useCallback`, and `memo` calls.
- The compiler respects the Rules of React (pure components, no side effects during render).

**Setup (Next.js 15):**

```js
// next.config.js
module.exports = {
  experimental: {
    reactCompiler: true,
  },
};
```

**Important:** The compiler cannot optimize code that violates React rules. Ensure components are pure and side-effect-free during render.

## Bundle Analysis

### Setup

```bash
npm install @next/bundle-analyzer
```

```js
// next.config.js
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});
module.exports = withBundleAnalyzer(nextConfig);
```

```bash
ANALYZE=true npm run build
```

### What to Look For

1. **Large dependencies** -- replace heavy libraries with lighter alternatives (e.g., `date-fns` instead of `moment`, `clsx` instead of `classnames`).
2. **Duplicate packages** -- multiple versions of the same library in the bundle.
3. **Unnecessary imports** -- importing entire libraries when only one function is needed.
4. **Client-side code that should be server-only** -- database clients, API keys.

## Code Splitting and Lazy Loading

### Dynamic Imports

```tsx
import dynamic from "next/dynamic";

// Lazy load heavy components
const MarkdownEditor = dynamic(() => import("@/components/markdown-editor"), {
  loading: () => <EditorSkeleton />,
  ssr: false, // disable SSR for client-only components
});

// Lazy load below-the-fold content
const Comments = dynamic(() => import("@/components/comments"));
```

### Route-Level Code Splitting

Next.js App Router automatically code-splits by route. Each `page.tsx` is a separate chunk. To optimize further:

- Move heavy client components into separate files and use `dynamic()`.
- Use `React.lazy` for client-side-only component trees.
- Keep `"use client"` boundaries as low in the tree as possible.

### Lazy Loading Strategies

```tsx
// Intersection Observer pattern for below-fold content
function LazySection({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setIsVisible(true); },
      { rootMargin: "200px" } // load 200px before viewport
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return <div ref={ref}>{isVisible ? children : <Skeleton />}</div>;
}
```

## Image Optimization with next/image

```tsx
import Image from "next/image";

// Always use next/image for automatic optimization
<Image
  src="/hero.jpg"
  alt="Hero banner"
  width={1200}
  height={600}
  priority              // preload above-the-fold images
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
  className="object-cover rounded-lg"
/>

// For dynamic/user-uploaded images
<Image
  src={user.avatarUrl}
  alt={user.name}
  width={48}
  height={48}
  className="rounded-full"
/>
```

**Rules:**
- Always set `priority` on above-the-fold hero images and LCP images.
- Always provide `sizes` for responsive images to avoid loading oversized images.
- Use `placeholder="blur"` with `blurDataURL` for perceived performance.
- Configure `remotePatterns` in `next.config.js` for external image domains.

## State Management Patterns

### When to Use What

| Pattern              | Use Case                                         |
|----------------------|--------------------------------------------------|
| `useState`           | Local UI state (open/closed, input values)       |
| `useReducer`         | Complex local state with multiple sub-values     |
| React Context        | Theme, locale, auth -- rarely changing data       |
| Zustand              | Global client state, frequent updates, multiple consumers |
| Server state (RSC)   | Data from database/API, rendered on server        |
| URL state (searchParams) | Filters, pagination, shareable state          |

### Zustand vs Context

**Use Zustand when:**
- State changes frequently (typing, drag-and-drop, real-time data).
- Many components consume the same state (avoids Context re-render cascade).
- You need derived state (selectors) without extra memoization.
- You need state persistence (localStorage, sessionStorage).

**Use Context when:**
- State changes rarely (theme toggle, user session).
- Only a few components consume it.
- You want zero external dependencies.

```tsx
// Zustand store pattern
import { create } from "zustand";

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  total: () => number;
}

const useCartStore = create<CartStore>((set, get) => ({
  items: [],
  addItem: (item) => set((state) => ({ items: [...state.items, item] })),
  removeItem: (id) => set((state) => ({ items: state.items.filter((i) => i.id !== id) })),
  total: () => get().items.reduce((sum, item) => sum + item.price * item.quantity, 0),
}));

// Use selectors to prevent unnecessary re-renders
const itemCount = useCartStore((state) => state.items.length);
```

## Render Optimization Checklist

1. **Move state down.** Keep state in the lowest component that needs it.
2. **Lift content up.** Pass children as props to avoid re-rendering static content.
3. **Split components.** Separate frequently-changing state from expensive render trees.
4. **Use selectors.** With Zustand or Redux, select only the data each component needs.
5. **Avoid inline objects/arrays as props.** Create them outside render or memoize them.
6. **Key lists properly.** Use stable, unique IDs -- never array indices for dynamic lists.
7. **Debounce expensive updates.** For search inputs, resize handlers, scroll listeners.
8. **Profile before optimizing.** Use React DevTools Profiler to identify actual bottlenecks.
