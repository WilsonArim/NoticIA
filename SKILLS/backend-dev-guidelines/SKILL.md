---
name: Backend Dev Guidelines
description: Node.js/Express/TypeScript patterns for production-grade backend services
phase: 3
---

# Backend Development Guidelines

## Project Structure Convention

Organize the codebase by domain, not by technical layer. Each module should encapsulate its own routes, controllers, services, and types.

```
src/
  modules/
    users/
      users.controller.ts
      users.service.ts
      users.routes.ts
      users.schema.ts       # Zod validation schemas
      users.types.ts
    orders/
      orders.controller.ts
      orders.service.ts
      orders.routes.ts
      orders.schema.ts
      orders.types.ts
  middleware/
    errorHandler.ts
    requestValidator.ts
    auth.ts
    rateLimiter.ts
  config/
    env.ts                   # Typed environment config
    database.ts
    logger.ts
  utils/
    AppError.ts
    asyncHandler.ts
    response.ts
  server.ts
  app.ts
```

Separate `app.ts` (Express setup, middleware, routes) from `server.ts` (HTTP listener, graceful shutdown). This makes the app testable without starting a real server.

## Environment Configuration Pattern

Never access `process.env` directly outside of a single config module. Parse and validate all env vars at startup using Zod.

```typescript
// config/env.ts
import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "staging", "production"]).default("development"),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

export const env = envSchema.parse(process.env);
export type Env = z.infer<typeof envSchema>;
```

If any required variable is missing or invalid, the process crashes immediately at startup with a clear error message. This prevents silent misconfiguration in production.

## Request Validation with Zod

Define schemas per route and validate using a reusable middleware.

```typescript
// middleware/requestValidator.ts
import { Request, Response, NextFunction } from "express";
import { AnyZodObject, ZodError } from "zod";

export const validate = (schema: AnyZodObject) =>
  async (req: Request, _res: Response, next: NextFunction) => {
    try {
      await schema.parseAsync({
        body: req.body,
        query: req.query,
        params: req.params,
      });
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        next(new AppError(400, "Validation failed", error.flatten().fieldErrors));
      }
      next(error);
    }
  };
```

Schemas should live alongside their module. Validate body, query, and params together so the controller receives only clean data.

## Error Handling Middleware

Use a custom AppError class and a centralized error handler. Never let unhandled errors leak raw stack traces.

```typescript
// utils/AppError.ts
export class AppError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public details?: unknown,
    public isOperational = true
  ) {
    super(message);
    Error.captureStackTrace(this, this.constructor);
  }
}

// middleware/errorHandler.ts
export const errorHandler = (err: Error, req: Request, res: Response, _next: NextFunction) => {
  const statusCode = err instanceof AppError ? err.statusCode : 500;
  const message = err instanceof AppError ? err.message : "Internal Server Error";

  logger.error({ err, requestId: req.id, path: req.path }, message);

  res.status(statusCode).json({
    status: "error",
    message,
    ...(env.NODE_ENV !== "production" && { stack: err.stack }),
    ...(err instanceof AppError && err.details && { details: err.details }),
  });
};
```

Distinguish operational errors (expected, like 404 or validation failure) from programmer errors (unexpected bugs). Only operational errors get user-friendly responses; programmer errors trigger alerts.

## Structured Logging

Use `pino` for structured JSON logging. Every log entry should include a request ID for traceability.

```typescript
// config/logger.ts
import pino from "pino";
import { env } from "./env";

export const logger = pino({
  level: env.LOG_LEVEL,
  transport: env.NODE_ENV === "development" ? { target: "pino-pretty" } : undefined,
  serializers: { err: pino.stdSerializers.err },
  base: { service: "my-api", env: env.NODE_ENV },
});
```

Attach a unique request ID via middleware using `crypto.randomUUID()`. Log at the right level: `debug` for development details, `info` for request/response lifecycle, `warn` for recoverable issues, `error` for failures requiring attention.

Never log sensitive data: passwords, tokens, full credit card numbers, or PII. Redact fields explicitly in the serializer config.

## Response Formatting

Standardize all API responses for consistency. Clients should always know the shape of the response.

```typescript
// utils/response.ts
export const sendSuccess = <T>(res: Response, data: T, statusCode = 200) => {
  res.status(statusCode).json({ status: "success", data });
};

export const sendPaginated = <T>(res: Response, data: T[], meta: PaginationMeta) => {
  res.status(200).json({ status: "success", data, meta });
};

type PaginationMeta = {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
};
```

## Async Handler Wrapper

Wrap all async route handlers to forward errors to the error middleware without manual try/catch in every controller.

```typescript
// utils/asyncHandler.ts
import { Request, Response, NextFunction } from "express";

export const asyncHandler = (fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) =>
  (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
```

## Graceful Shutdown

Handle SIGTERM and SIGINT to close connections cleanly before the process exits. This is critical in containerized deployments where orchestrators send signals during scaling.

```typescript
// server.ts
const server = app.listen(env.PORT, () => {
  logger.info(`Server running on port ${env.PORT}`);
});

const shutdown = async (signal: string) => {
  logger.info(`${signal} received. Starting graceful shutdown...`);
  server.close(async () => {
    await database.disconnect();
    logger.info("All connections closed. Exiting.");
    process.exit(0);
  });
  setTimeout(() => {
    logger.error("Forced shutdown after timeout");
    process.exit(1);
  }, 10_000);
};

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
```

Set a hard timeout (e.g., 10 seconds) as a safety net. If cleanup takes too long, force exit to avoid zombie processes.

## Key Principles

- Fail fast at startup: validate config, check DB connection, verify required services.
- Use dependency injection or factory functions for testability. Avoid importing singletons directly in service files.
- Keep controllers thin. They parse the request, call a service, and format the response. Business logic lives in services.
- Write integration tests against the Express app using `supertest`, not against individual controllers.
- Use TypeScript strict mode. Enable `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` for extra safety.
