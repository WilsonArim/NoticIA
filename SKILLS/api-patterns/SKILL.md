---
name: API Patterns
description: Decision framework and best practices for REST, GraphQL, and tRPC API design including versioning, error handling, and pagination
phase: 2
---

# API Patterns

## Decision Matrix

| Factor | REST | GraphQL | tRPC |
|---|---|---|---|
| Client diversity | Multiple clients (web, mobile, third-party) | Multiple clients with varied data needs | Single TypeScript client (monorepo) |
| Data fetching | Fixed response shapes per endpoint | Client specifies exact fields needed | Full type inference, function-call style |
| Caching | HTTP caching (CDN, browser) works natively | Requires custom caching (Apollo, urql) | Limited to query-level caching (React Query) |
| Learning curve | Low -- widely understood | Medium -- schema language, resolvers, client libraries | Low for TypeScript teams -- feels like function calls |
| Real-time | Requires WebSocket or SSE separately | Subscriptions built into spec | Subscriptions via WebSocket adapter |
| File uploads | Native multipart/form-data | Requires workarounds (multipart spec extension) | Requires separate HTTP endpoint or adapter |
| Public API | Best choice -- universal adoption | Good choice if clients need flexibility | Not suitable -- TypeScript-only, no standard protocol |
| Team setup | Any language/framework | Requires schema management discipline | Requires shared TypeScript monorepo |

### Quick Decision Guide
- **Building a public API or integrating with third parties**: Use REST.
- **Complex frontend with deeply nested, varied data needs**: Use GraphQL.
- **Full-stack TypeScript app in a monorepo (e.g., Next.js)**: Use tRPC.
- **Combining approaches**: tRPC for internal app, REST for public/webhook endpoints. This is a common and effective pattern.

## REST Best Practices

### Resource Naming
- Use nouns, not verbs: `/users`, not `/getUsers`.
- Use plural form: `/orders`, not `/order`.
- Nest for clear relationships: `/users/:userId/orders`.
- Limit nesting to two levels. Beyond that, use query parameters or top-level resources with filters.
- Use kebab-case for multi-word resources: `/order-items`.

### HTTP Methods
| Method | Purpose | Idempotent | Request Body |
|---|---|---|---|
| GET | Retrieve resource(s) | Yes | No |
| POST | Create a resource | No | Yes |
| PUT | Replace a resource entirely | Yes | Yes |
| PATCH | Partially update a resource | Yes | Yes |
| DELETE | Remove a resource | Yes | No |

### Status Codes
Use the correct status code for every response:
- **200 OK**: Successful GET, PUT, PATCH, or DELETE.
- **201 Created**: Successful POST that created a resource. Include `Location` header.
- **204 No Content**: Successful DELETE with no response body.
- **400 Bad Request**: Malformed request or validation failure.
- **401 Unauthorized**: Missing or invalid authentication.
- **403 Forbidden**: Authenticated but not authorized for this action.
- **404 Not Found**: Resource does not exist.
- **409 Conflict**: Request conflicts with current state (e.g., duplicate email).
- **422 Unprocessable Entity**: Request is well-formed but semantically invalid.
- **429 Too Many Requests**: Rate limit exceeded. Include `Retry-After` header.
- **500 Internal Server Error**: Unhandled server error. Never expose internal details.

### Pagination
Two common approaches:

**Offset-based** (simple, allows jumping to pages):
```
GET /posts?page=2&limit=20
Response: { data: [...], meta: { total: 200, page: 2, limit: 20, totalPages: 10 } }
```

**Cursor-based** (performant for large datasets, no page skipping):
```
GET /posts?cursor=abc123&limit=20
Response: { data: [...], meta: { nextCursor: "def456", hasMore: true } }
```

Prefer cursor-based for infinite scroll UIs and large tables. Use offset-based when users need page numbers.

### Filtering and Sorting
```
GET /products?category=electronics&minPrice=100&sort=-createdAt,name
```
- Use query parameters for filtering.
- Prefix sort fields with `-` for descending order.
- Validate and whitelist allowed filter and sort fields server-side.

## GraphQL Schema Design

### Schema-First Approach
Define your schema before writing resolvers. The schema is the contract between frontend and backend.

### Type Design Principles
- Keep types focused. A `User` type should not include unrelated fields from other domains.
- Use custom scalar types for domain concepts: `DateTime`, `EmailAddress`, `URL`.
- Prefer specific types over generic ones. `CreateUserInput` and `UpdateUserInput` instead of a single `UserInput`.

### Query Design
- Provide both singular and plural queries: `user(id: ID!)` and `users(filter: UserFilter)`.
- Use connection pattern for pagination (Relay spec): `users(first: 10, after: "cursor")` returning `UserConnection` with `edges` and `pageInfo`.
- Avoid deeply nested queries that could cause N+1 problems. Use DataLoader.

### Mutation Design
- Name mutations as verbs: `createUser`, `updateOrder`, `cancelSubscription`.
- Each mutation should return a union type or the modified object plus potential errors.
- Validate inputs in resolvers. Do not rely solely on schema validation.

### Common Pitfalls
- **N+1 queries**: Use DataLoader to batch and cache database calls within a single request.
- **Over-fetching in resolvers**: Only fetch data for fields actually requested. Check `info.fieldNodes`.
- **Schema bloat**: Resist adding fields "just in case." Add fields when there is a client need.

## tRPC Setup with Next.js

### Core Concept
tRPC eliminates the API layer by sharing types between server and client. You define procedures (queries, mutations) on the server and call them as type-safe functions on the client.

### Setup Steps
1. **Define your router** with procedures:
```typescript
const appRouter = router({
  user: router({
    getById: publicProcedure
      .input(z.object({ id: z.string().uuid() }))
      .query(({ input, ctx }) => {
        return ctx.db.user.findUnique({ where: { id: input.id } });
      }),
    create: protectedProcedure
      .input(createUserSchema)
      .mutation(({ input, ctx }) => {
        return ctx.userService.create(input);
      }),
  }),
});
```

2. **Export the type**: `export type AppRouter = typeof appRouter;`
3. **Create the client** using `createTRPCReact<AppRouter>()` or the Next.js adapter.
4. **Use in components** with full autocompletion and type safety.

### Best Practices
- Use Zod for input validation on every procedure.
- Organize routers by domain: `userRouter`, `orderRouter`, `paymentRouter`.
- Use middleware for cross-cutting concerns (auth, logging, rate limiting).
- Keep procedures thin -- delegate business logic to service or use case layers.

## API Versioning Strategies

### URL Path Versioning
```
/api/v1/users
/api/v2/users
```
Simple and explicit. Easy to route and document. Recommended for most public APIs.

### Header Versioning
```
Accept: application/vnd.myapp.v2+json
```
Keeps URLs clean but is less discoverable and harder to test in a browser.

### Query Parameter Versioning
```
/api/users?version=2
```
Easy to implement but pollutes the query string and complicates caching.

### Recommendation
Use URL path versioning for public REST APIs. For internal APIs (especially with tRPC), versioning is rarely needed -- evolve the contract alongside the client.

### Version Transition Rules
1. Never break an existing version. Add new fields as optional; do not remove or rename existing fields.
2. Deprecate before removing. Log usage of deprecated endpoints.
3. Support at most two versions simultaneously (current and previous).
4. Communicate deprecation timelines clearly in documentation and response headers.

## Error Response Format

Use a consistent error format across all API responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request body contains invalid fields.",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address."
      },
      {
        "field": "age",
        "message": "Must be a positive integer."
      }
    ]
  }
}
```

### Error Code Conventions
- Use UPPER_SNAKE_CASE for error codes.
- Make codes machine-readable and stable. Clients should be able to switch on `error.code`.
- Use `message` for human-readable descriptions. These can change without breaking clients.
- Include `details` array for field-level validation errors.
- For paginated or batch endpoints, support partial errors with per-item status.

### Standard Error Codes
Define a finite set of error codes and document them:
- `VALIDATION_ERROR` -- Input validation failed.
- `NOT_FOUND` -- Requested resource does not exist.
- `UNAUTHORIZED` -- Authentication required or invalid.
- `FORBIDDEN` -- Insufficient permissions.
- `CONFLICT` -- Action conflicts with current state.
- `RATE_LIMITED` -- Too many requests.
- `INTERNAL_ERROR` -- Unexpected server error.
