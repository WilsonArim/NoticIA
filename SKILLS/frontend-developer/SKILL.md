---
name: Frontend Developer
description: React 19+ and Next.js 15+ modern development patterns and best practices
phase: 4
---

# Frontend Developer -- React 19+ and Next.js 15+

## React 19 Core Features

### The `use` Hook

React 19 introduces `use` as a first-class way to read resources (promises, context) during render.

```tsx
// Reading a promise during render (replaces useEffect + useState for data fetching)
function UserProfile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise);
  return <h1>{user.name}</h1>;
}

// Reading context conditionally (impossible with useContext)
function ThemeButton({ showTheme }: { showTheme: boolean }) {
  if (showTheme) {
    const theme = use(ThemeContext);
    return <button className={theme.buttonClass}>Themed</button>;
  }
  return <button>Default</button>;
}
```

### Actions and Form Handling

Actions replace manual `onSubmit` handlers with integrated pending states and error handling.

```tsx
// Server Action (defined in a server module)
"use server";
export async function createPost(formData: FormData) {
  const title = formData.get("title") as string;
  await db.posts.create({ title });
  revalidatePath("/posts");
}

// Client component consuming the action
function PostForm() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? "Saving..." : "Save"}</button>;
}
```

### Optimistic Updates with `useOptimistic`

```tsx
function TodoList({ todos }: { todos: Todo[] }) {
  const [optimisticTodos, addOptimisticTodo] = useOptimistic(
    todos,
    (state, newTodo: Todo) => [...state, { ...newTodo, pending: true }]
  );

  async function addTodo(formData: FormData) {
    const title = formData.get("title") as string;
    addOptimisticTodo({ id: crypto.randomUUID(), title, pending: true });
    await createTodo(title); // server action
  }

  return (
    <form action={addTodo}>
      <input name="title" />
      <ul>
        {optimisticTodos.map((todo) => (
          <li key={todo.id} style={{ opacity: todo.pending ? 0.6 : 1 }}>
            {todo.title}
          </li>
        ))}
      </ul>
    </form>
  );
}
```

## Next.js 15 App Router Patterns

### Server vs Client Components Decision Tree

Use this decision tree when choosing component boundaries:

1. Does the component need browser APIs (window, localStorage, event listeners)? --> Client Component
2. Does it need React state or lifecycle effects (useState, useEffect)? --> Client Component
3. Does it use interactivity (onClick, onChange, onSubmit handlers)? --> Client Component
4. Does it only display data fetched from a database or API? --> Server Component
5. Does it access backend resources directly (database, filesystem)? --> Server Component
6. Does it keep sensitive data server-side (API keys, tokens)? --> Server Component

**Default to Server Components.** Only add `"use client"` when you need interactivity.

### Data Fetching in React Server Components

```tsx
// app/posts/page.tsx -- Server Component (no "use client")
// Direct database/API access without useEffect or client-side fetching
async function PostsPage() {
  const posts = await db.posts.findMany({ orderBy: { createdAt: "desc" } });

  return (
    <div>
      <h1>Posts</h1>
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  );
}
```

**Caching and revalidation strategies:**

- `fetch(url, { cache: "force-cache" })` -- cache indefinitely (static)
- `fetch(url, { next: { revalidate: 3600 } })` -- revalidate every hour (ISR)
- `fetch(url, { cache: "no-store" })` -- always fresh (dynamic)
- `revalidatePath("/posts")` -- on-demand revalidation from server actions
- `revalidateTag("posts")` -- tag-based revalidation

### Metadata API

```tsx
// Static metadata
export const metadata: Metadata = {
  title: "My App",
  description: "App description for SEO",
  openGraph: { title: "My App", description: "Shared on social media" },
};

// Dynamic metadata based on params
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPost(params.slug);
  return {
    title: post.title,
    description: post.excerpt,
    openGraph: { images: [post.coverImage] },
  };
}
```

### Error Boundaries and Loading States

```
app/
  layout.tsx          -- Root layout (wraps everything)
  error.tsx           -- Root error boundary
  loading.tsx         -- Root loading state (shows during Suspense)
  posts/
    page.tsx          -- Posts list page
    error.tsx         -- Posts-specific error boundary
    loading.tsx       -- Posts-specific loading skeleton
    [slug]/
      page.tsx        -- Individual post
      not-found.tsx   -- Custom 404 for missing posts
```

**Error boundary pattern:**

```tsx
// app/posts/error.tsx
"use client"; // Error boundaries must be client components
export default function PostsError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div role="alert">
      <h2>Something went wrong loading posts</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

**Loading state pattern:**

```tsx
// app/posts/loading.tsx
export default function PostsLoading() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  );
}
```

### Parallel Routes

Parallel routes allow rendering multiple pages simultaneously in the same layout.

```
app/
  @analytics/
    page.tsx          -- Analytics panel
  @feed/
    page.tsx          -- Feed panel
  layout.tsx          -- Receives both as props
  page.tsx            -- Main content
```

```tsx
// app/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  feed,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  feed: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <main className="col-span-2">{children}</main>
      <aside>
        {analytics}
        {feed}
      </aside>
    </div>
  );
}
```

## Key Conventions

- **File conventions:** `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`, `route.tsx`
- **Colocation:** keep components, utils, and tests near their route segments
- **Server-first:** start with Server Components, push `"use client"` to leaf components
- **Streaming:** use `<Suspense>` boundaries to progressively render content
- **Type safety:** use `generateStaticParams` return type for dynamic routes
