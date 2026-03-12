---
name: Senior Fullstack
description: Complete fullstack development guide covering Next.js App Router, server/client patterns, and monorepo structure
phase: 3
---

# Senior Fullstack Development Guide

## Next.js App Router Patterns

Structure the `app/` directory by feature routes. Use route groups `(groupName)` to organize layouts without affecting the URL path. Colocate page-specific components alongside their route segments.

```
app/
  (auth)/
    login/page.tsx
    register/page.tsx
    layout.tsx              # Auth-specific layout (no sidebar)
  (dashboard)/
    dashboard/page.tsx
    settings/page.tsx
    layout.tsx              # Dashboard layout with sidebar
  api/
    webhooks/stripe/route.ts
  layout.tsx                # Root layout
  error.tsx                 # Global error boundary
  loading.tsx               # Global loading state
  not-found.tsx
lib/
  actions/                  # Server actions by domain
    users.ts
    orders.ts
  db/
    schema.ts               # Drizzle/Prisma schema
    queries.ts              # Reusable query functions
  validators/               # Shared Zod schemas
    user.ts
    order.ts
components/
  ui/                       # Generic UI components
  features/                 # Feature-specific components
types/
  index.ts                  # Shared type definitions
```

## Server Actions

Server actions are the preferred mutation mechanism in App Router. They run on the server and can be called directly from client components via forms or programmatically.

```typescript
// lib/actions/users.ts
"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { db } from "@/lib/db";
import { actionClient } from "@/lib/safe-action";

const updateProfileSchema = z.object({
  name: z.string().min(1).max(100),
  bio: z.string().max(500).optional(),
});

export const updateProfile = actionClient
  .schema(updateProfileSchema)
  .action(async ({ parsedInput, ctx }) => {
    const { name, bio } = parsedInput;
    const userId = ctx.session.user.id;

    await db.user.update({ where: { id: userId }, data: { name, bio } });
    revalidatePath("/settings");
    return { success: true };
  });
```

Always validate inputs in server actions. Never trust the client. Use `next-safe-action` or a similar wrapper to centralize validation and auth checks.

## Data Fetching Strategies: RSC vs Client

**React Server Components (default):** Fetch data directly in the component. No useEffect, no loading states to manage, no waterfalls by default.

```typescript
// app/(dashboard)/dashboard/page.tsx
import { db } from "@/lib/db";
import { DashboardView } from "@/components/features/dashboard-view";

export default async function DashboardPage() {
  const [metrics, recentOrders] = await Promise.all([
    db.getMetrics(),
    db.getRecentOrders({ limit: 10 }),
  ]);

  return <DashboardView metrics={metrics} orders={recentOrders} />;
}
```

**Client Components:** Use only when you need interactivity (event handlers, hooks, browser APIs). Fetch via React Query or SWR for data that needs polling, optimistic updates, or client-side cache.

**Decision framework:**
- Static or user-specific page load data: RSC (fetch in server component)
- Real-time data, polling, infinite scroll: Client component with React Query
- Form submissions, mutations: Server actions
- Data that changes based on user interaction without navigation: Client-side fetch

## API Routes vs Server Actions

| Use Case | Mechanism |
|---|---|
| Mutations from your own UI | Server actions |
| Third-party webhooks (Stripe, GitHub) | API routes (`route.ts`) |
| Public API consumed by external clients | API routes |
| File uploads with progress | API routes |
| Simple CRUD from forms | Server actions |

Server actions reduce boilerplate: no fetch calls, no manual error parsing, automatic revalidation. Use API routes only when you need a traditional HTTP endpoint.

## Shared Types Between Client and Server

Define types in a central `types/` directory. Derive types from your database schema and Zod validators to maintain a single source of truth.

```typescript
// lib/validators/order.ts
import { z } from "zod";

export const createOrderSchema = z.object({
  items: z.array(z.object({
    productId: z.string().uuid(),
    quantity: z.number().int().positive(),
  })).min(1),
  shippingAddressId: z.string().uuid(),
});

export type CreateOrderInput = z.infer<typeof createOrderSchema>;

// types/index.ts
import type { InferSelectModel } from "drizzle-orm";
import type { orders } from "@/lib/db/schema";

export type Order = InferSelectModel<typeof orders>;
export type OrderWithItems = Order & { items: OrderItem[] };
```

Never duplicate types manually. If the database schema changes, the types update automatically.

## Monorepo Structure

For projects that grow beyond a single Next.js app, use a monorepo with Turborepo or Nx.

```
packages/
  ui/                   # Shared UI component library
    src/
    package.json
  db/                   # Database schema, migrations, client
    src/
    package.json
  validators/           # Shared Zod schemas
    src/
    package.json
  config-ts/            # Shared tsconfig bases
    base.json
    nextjs.json
    library.json
apps/
  web/                  # Next.js frontend
    package.json
  api/                  # Express/Fastify API (if separate)
    package.json
  admin/                # Admin dashboard
    package.json
turbo.json
package.json
```

Key monorepo rules:
- Shared packages use `"main"` and `"types"` fields pointing to source (not built output) during development. Use Turborepo's `transpilePackages` in Next.js config.
- Database package owns all schema definitions and exports the client. No app should define its own database connection.
- Validators package exports Zod schemas used by both frontend forms and backend endpoints.

## Environment Management

Manage environment variables with type safety across all apps.

```
.env.local              # Local overrides (gitignored)
.env.development        # Development defaults
.env.production         # Production defaults (non-secret)
```

Rules:
- Never commit secrets. Use `.env.local` for local secrets and a secrets manager (Vault, AWS SSM, Vercel env) for production.
- Prefix client-exposed variables with `NEXT_PUBLIC_`. Everything else stays server-only.
- Validate all env vars at build time using `@t3-oss/env-nextjs` or a custom Zod schema in `env.mjs`.

```typescript
// env.mjs
import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

export const env = createEnv({
  server: {
    DATABASE_URL: z.string().url(),
    STRIPE_SECRET_KEY: z.string().startsWith("sk_"),
  },
  client: {
    NEXT_PUBLIC_APP_URL: z.string().url(),
  },
  runtimeEnv: {
    DATABASE_URL: process.env.DATABASE_URL,
    STRIPE_SECRET_KEY: process.env.STRIPE_SECRET_KEY,
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  },
});
```

## Key Principles

- Default to server components. Add `"use client"` only when the component needs interactivity.
- Colocate data fetching with the component that uses it. Avoid prop-drilling fetched data through multiple layers.
- Use `Suspense` boundaries to stream parts of the page that depend on slow queries, keeping the shell interactive.
- Leverage `generateMetadata` for SEO on dynamic pages. Do not hardcode meta tags.
- Cache aggressively with `unstable_cache` or React `cache()` for expensive database queries. Set explicit revalidation times.
- For forms, use `useActionState` (React 19) to handle pending states and errors from server actions without manual state management.
- Test server components with integration tests that render the full page. Test client components with React Testing Library.
