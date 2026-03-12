---
name: Performance Engineer
description: Application performance optimization covering Core Web Vitals, profiling, caching, and rendering strategies
phase: 5
---

# Performance Engineer

## Core Web Vitals

These are Google's key metrics for user experience. All production web applications must meet the "Good" thresholds.

### Largest Contentful Paint (LCP)
Measures how long it takes for the largest visible content element to render.

| Rating | Threshold   |
|--------|-------------|
| Good   | < 2.5s      |
| Needs Improvement | 2.5s - 4.0s |
| Poor   | > 4.0s      |

Optimization strategies:
- Optimize the critical rendering path. Inline critical CSS.
- Preload the LCP resource (`<link rel="preload">`).
- Use a CDN for static assets to reduce TTFB.
- Optimize server response time (target < 200ms TTFB).
- Avoid render-blocking JavaScript and CSS.
- Use responsive images with `srcset` and `sizes` attributes.

### First Input Delay (FID) / Interaction to Next Paint (INP)
Measures responsiveness -- how quickly the page responds to user interaction.

| Rating | Threshold   |
|--------|-------------|
| Good   | < 100ms (FID) / < 200ms (INP) |
| Needs Improvement | 100-300ms / 200-500ms |
| Poor   | > 300ms / > 500ms |

Optimization strategies:
- Break long tasks (> 50ms) into smaller chunks using `requestIdleCallback` or `scheduler.yield()`.
- Defer non-critical JavaScript with `async` or `defer` attributes.
- Minimize main thread work during page load.
- Use web workers for CPU-intensive computations.
- Avoid synchronous layout thrashing (read then write DOM properties in batches).

### Cumulative Layout Shift (CLS)
Measures visual stability -- how much the page layout shifts unexpectedly.

| Rating | Threshold   |
|--------|-------------|
| Good   | < 0.1       |
| Needs Improvement | 0.1 - 0.25 |
| Poor   | > 0.25      |

Optimization strategies:
- Always include `width` and `height` attributes on images and videos.
- Use CSS `aspect-ratio` for dynamic media containers.
- Reserve space for ads, embeds, and dynamically injected content.
- Avoid inserting content above existing content after initial render.
- Use `font-display: swap` with font preloading to minimize FOIT/FOUT shifts.

## Profiling Tools

| Tool                         | Purpose                              | When to Use                     |
|------------------------------|--------------------------------------|---------------------------------|
| Chrome DevTools Performance  | CPU profiling, flame charts          | Diagnosing slow interactions    |
| Lighthouse                   | Overall performance audit            | Pre-deployment checks           |
| WebPageTest                  | Real-world loading performance       | Production baseline measurement |
| React DevTools Profiler      | Component render analysis            | React-specific optimization     |
| Node.js --inspect            | Server-side CPU profiling            | API response time issues        |
| pg_stat_statements           | PostgreSQL query analysis            | Database bottleneck detection   |
| bundle-analyzer              | JavaScript bundle composition        | Bundle size optimization        |

## Bundle Size Optimization

Target: Keep the initial JavaScript bundle under 200KB gzipped.

Strategies:
- **Code splitting**: Split by route using dynamic `import()`. Each page should load only the code it needs.
- **Tree shaking**: Ensure all imports are ES modules. Avoid `import *` and side-effect-heavy modules.
- **Dependency audit**: Regularly review `node_modules` for large, underutilized dependencies. Use `bundlephobia.com` to check package sizes before adding them.
- **Replace heavy libraries**: Consider lighter alternatives (e.g., `date-fns` instead of `moment`, `clsx` instead of `classnames`).
- **Compression**: Enable Brotli compression on your CDN/server (20-25% smaller than gzip).
- **Dead code elimination**: Remove unused exports and unreachable code paths.

```bash
# Analyze bundle composition
npx webpack-bundle-analyzer stats.json
# or for Next.js
ANALYZE=true next build
```

## Database Query Optimization

### Common problems and fixes

| Problem           | Symptom                          | Fix                                          |
|-------------------|----------------------------------|----------------------------------------------|
| N+1 queries       | 100+ queries for one page load   | Use JOINs or eager loading                   |
| Missing indexes   | Full table scans on WHERE clauses| Add indexes on filtered/sorted columns       |
| SELECT *          | Transferring unused columns      | Select only needed columns                   |
| No pagination     | Loading entire tables            | Use LIMIT/OFFSET or cursor-based pagination  |
| Unoptimized JOINs | Slow multi-table queries         | Analyze with EXPLAIN ANALYZE, add indexes    |

### Query analysis workflow
```sql
-- Identify slow queries
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Find missing indexes
SELECT relname, seq_scan, idx_scan,
       seq_scan - idx_scan AS too_many_seqs
FROM pg_stat_user_tables
WHERE seq_scan - idx_scan > 0
ORDER BY too_many_seqs DESC;
```

## Caching Strategies

### CDN Caching
- Cache static assets (JS, CSS, images, fonts) with long TTLs (1 year) using content hashing in filenames.
- Use `Cache-Control: public, max-age=31536000, immutable` for hashed assets.
- Use `Cache-Control: no-cache` (which means "revalidate") for HTML documents.
- Configure cache purging for emergency updates.

### Application Caching
- Cache expensive computations with in-memory stores (Redis, Memcached).
- Use cache-aside pattern: check cache first, compute on miss, store result.
- Set appropriate TTLs based on data freshness requirements.
- Implement cache invalidation on data mutations.
- Use stale-while-revalidate for non-critical data.

```typescript
// Cache-aside pattern example
async function getUser(id: string): Promise<User> {
  const cached = await cache.get(`user:${id}`);
  if (cached) return JSON.parse(cached);

  const user = await db.users.findById(id);
  await cache.set(`user:${id}`, JSON.stringify(user), { ttl: 300 });
  return user;
}
```

### Database Caching
- Use materialized views for expensive aggregations that tolerate staleness.
- Enable query result caching where supported.
- Use connection pooling to avoid connection overhead (PgBouncer, Supabase built-in pooler).
- Denormalize read-heavy data when the write cost is acceptable.

## Lazy Loading

- **Images**: Use `loading="lazy"` for below-the-fold images. Do NOT lazy load the LCP image.
- **Components**: Use `React.lazy()` with `Suspense` for non-critical UI components.
- **Routes**: Split routes with dynamic imports so each page is a separate chunk.
- **Third-party scripts**: Load analytics, chat widgets, and non-essential scripts with `defer` or after page load.
- **Data**: Fetch non-critical data after the initial render using intersection observers or idle callbacks.

```tsx
// Route-level code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));

// Component-level lazy loading
const HeavyChart = lazy(() => import('./components/HeavyChart'));
```

## Image Optimization

- Use modern formats: WebP (90% browser support) or AVIF (70% support) with JPEG/PNG fallbacks.
- Serve responsive images using `srcset` and `sizes` attributes.
- Compress images to appropriate quality (80-85% for photos, lossless for graphics).
- Use a CDN with automatic image optimization (Cloudflare Images, Vercel Image Optimization, imgix).
- Implement blur-up or LQIP (Low Quality Image Placeholder) for perceived performance.
- Set explicit dimensions to prevent layout shifts.

```html
<img
  src="/images/hero.webp"
  srcset="/images/hero-400.webp 400w,
         /images/hero-800.webp 800w,
         /images/hero-1200.webp 1200w"
  sizes="(max-width: 600px) 400px,
         (max-width: 1000px) 800px,
         1200px"
  width="1200"
  height="600"
  alt="Hero image"
  loading="eager"
  fetchpriority="high"
/>
```

## Server-Side Rendering vs Static Generation

| Strategy              | Best For                              | Trade-offs                          |
|-----------------------|---------------------------------------|-------------------------------------|
| Static Generation (SSG) | Marketing pages, blogs, docs        | Fastest TTFB, but data is stale until rebuild |
| Incremental Static Regeneration (ISR) | E-commerce, content sites | Near-static speed with periodic updates |
| Server-Side Rendering (SSR) | Personalized content, dashboards  | Fresh data, but higher server load and TTFB |
| Client-Side Rendering (CSR) | Internal tools, authenticated apps | Simplest, but poor SEO and initial load |

Decision framework:
1. Is the content the same for all users? Use **SSG** or **ISR**.
2. Does the content change per-user or per-request? Use **SSR**.
3. Is SEO irrelevant and the app behind authentication? **CSR** is acceptable.
4. Do you need real-time data on a public page? Use **SSR** with streaming or **CSR** with a loading skeleton.

## Performance Budget

Define and enforce budgets in CI:

| Metric                  | Budget          |
|-------------------------|-----------------|
| Total JS (gzipped)      | < 200 KB        |
| Total CSS (gzipped)     | < 50 KB         |
| LCP                     | < 2.5s          |
| INP                     | < 200ms         |
| CLS                     | < 0.1           |
| Time to Interactive     | < 3.5s          |
| Lighthouse Performance  | > 90            |

```bash
# Enforce with bundlesize
npx bundlesize --config bundlesize.config.json

# Or with Lighthouse CI
lhci assert --preset=lighthouse:recommended
```
