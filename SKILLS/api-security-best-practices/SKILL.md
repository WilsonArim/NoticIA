---
name: API Security Best Practices
description: Secure API design covering OWASP Top 10, authentication, rate limiting, and defense-in-depth patterns
phase: 3
---

# API Security Best Practices

## OWASP API Security Top 10 Overview

Every backend developer must understand these common API vulnerabilities:

1. **Broken Object Level Authorization (BOLA):** Always verify the requesting user owns or has access to the requested resource. Never rely on the client sending the correct user ID.
2. **Broken Authentication:** Use proven libraries. Never implement custom crypto. Enforce strong password policies and MFA.
3. **Broken Object Property Level Authorization:** Do not return all object fields by default. Use explicit allowlists for response serialization.
4. **Unrestricted Resource Consumption:** Apply rate limiting, pagination limits, and request size caps.
5. **Broken Function Level Authorization:** Enforce role checks on every endpoint. Admin routes must verify admin status server-side.
6. **Unrestricted Access to Sensitive Business Flows:** Protect against automated abuse (bot purchases, credential stuffing) with rate limits and CAPTCHA.
7. **Server Side Request Forgery (SSRF):** Validate and sanitize all URLs the server fetches. Block requests to internal networks.
8. **Security Misconfiguration:** Disable debug modes, remove default credentials, restrict CORS, keep dependencies updated.
9. **Improper Inventory Management:** Document all API endpoints. Remove deprecated or shadow APIs. Version your API.
10. **Unsafe Consumption of APIs:** Validate responses from third-party APIs. Do not blindly trust external data.

## Rate Limiting Implementation

Apply rate limiting at multiple levels: global, per-endpoint, and per-user.

```typescript
// middleware/rateLimiter.ts
import rateLimit from "express-rate-limit";
import RedisStore from "rate-limit-redis";
import { redisClient } from "@/config/redis";

// Global: 100 requests per 15 minutes per IP
export const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
  message: { status: "error", message: "Too many requests. Try again later." },
});

// Auth endpoints: 5 attempts per 15 minutes per IP
export const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  skipSuccessfulRequests: true,
  store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
});
```

Use Redis-backed stores in multi-instance deployments. Memory-based stores do not share state across processes.

## CORS Configuration

Never use `origin: "*"` in production. Whitelist specific origins explicitly.

```typescript
import cors from "cors";

const allowedOrigins = [
  "https://myapp.com",
  "https://admin.myapp.com",
];

if (env.NODE_ENV === "development") {
  allowedOrigins.push("http://localhost:3000");
}

app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error("Not allowed by CORS"));
    }
  },
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "PATCH"],
  allowedHeaders: ["Content-Type", "Authorization"],
}));
```

If your API is not meant to be consumed from browsers, disable CORS entirely by not including the middleware.

## Input Validation

Validate every input on the server. Client-side validation is a UX convenience, not a security measure.

- Use Zod schemas for body, query parameters, and path parameters.
- Reject unknown keys with `.strict()` to prevent mass assignment attacks.
- Sanitize string inputs to strip HTML/script tags when the field should be plain text.
- Validate file uploads: check MIME type, file size, and file extension. Do not trust the `Content-Type` header alone.

```typescript
const createUserSchema = z.object({
  body: z.object({
    email: z.string().email().max(255),
    name: z.string().min(1).max(100).trim(),
    role: z.enum(["user", "editor"]),   // Never allow "admin" from client input
  }).strict(),
});
```

## SQL Injection Prevention

Use parameterized queries exclusively. Never concatenate user input into SQL strings.

```typescript
// DANGEROUS - never do this
const result = await db.query(`SELECT * FROM users WHERE id = '${userId}'`);

// SAFE - parameterized query
const result = await db.query("SELECT * FROM users WHERE id = $1", [userId]);

// SAFE - ORM with parameterized queries
const user = await db.user.findUnique({ where: { id: userId } });
```

ORMs like Prisma and Drizzle parameterize by default, but be cautious with raw query escape hatches (`$queryRaw`, `sql.raw`). Always pass user input as parameters, never as template literals.

## Authentication vs Authorization

**Authentication** verifies identity: "Who are you?" Handled by login, JWT verification, session validation.

**Authorization** verifies permissions: "Are you allowed to do this?" Handled by role checks, resource ownership checks, policy engines.

```typescript
// middleware/auth.ts - Authentication
export const authenticate = async (req: Request, _res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.replace("Bearer ", "");
  if (!token) throw new AppError(401, "Authentication required");

  const payload = verifyJWT(token);
  req.user = await db.user.findUniqueOrThrow({ where: { id: payload.sub } });
  next();
};

// middleware/authorize.ts - Authorization
export const authorize = (...roles: string[]) =>
  (req: Request, _res: Response, next: NextFunction) => {
    if (!roles.includes(req.user.role)) {
      throw new AppError(403, "Insufficient permissions");
    }
    next();
  };

// Usage
router.delete("/users/:id", authenticate, authorize("admin"), deleteUserHandler);
```

Always check resource ownership in addition to role. An authenticated user with the "editor" role should only edit their own resources unless explicitly granted broader access.

## API Key Management

- Generate API keys using `crypto.randomBytes(32).toString("hex")`. Never use UUIDs as API keys; they are not cryptographically random in all implementations.
- Store only the hashed version of the key in the database (SHA-256 is sufficient since API keys have high entropy).
- Show the raw key to the user exactly once at creation time.
- Support key rotation: allow multiple active keys per user with expiration dates.
- Scope keys with permissions (read-only, read-write, admin).
- Log key usage for audit trails but never log the key itself.

## Security Headers

Apply security headers using `helmet` or manually.

```typescript
import helmet from "helmet";

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
    },
  },
  hsts: { maxAge: 31536000, includeSubDomains: true },
}));

// Additional headers for APIs
app.use((_req, res, next) => {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Pragma", "no-cache");
  next();
});
```

For APIs returning sensitive data, always set `Cache-Control: no-store` to prevent proxies and browsers from caching responses.

## Request Size Limits

Limit request body size to prevent denial-of-service via large payloads.

```typescript
app.use(express.json({ limit: "100kb" }));
app.use(express.urlencoded({ extended: true, limit: "100kb" }));

// For file upload endpoints, set a higher but bounded limit
app.post("/upload", express.raw({ limit: "10mb", type: "application/octet-stream" }), uploadHandler);
```

Also enforce limits at the reverse proxy level (Nginx, Cloudflare) as a first line of defense.

## Security Checklist

- All endpoints require authentication unless explicitly public.
- Every mutation checks authorization (role + resource ownership).
- Rate limiting is applied globally and on sensitive endpoints (login, registration, password reset).
- All inputs are validated and sanitized server-side.
- Secrets are never logged, returned in responses, or committed to version control.
- Dependencies are audited regularly with `npm audit` and tools like Snyk.
- HTTPS is enforced. HTTP requests redirect to HTTPS.
- Error responses do not leak internal details (stack traces, database errors, file paths).
- API versioning is in place so deprecated endpoints can be removed on a schedule.
- Sensitive actions (password change, email change, account deletion) require re-authentication.
