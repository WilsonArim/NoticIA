---
name: Docker Expert
description: Containers, multi-stage builds, and production-ready Docker configurations
phase: 6
---

# Docker Expert

## Dockerfile Best Practices

Every Dockerfile should follow a consistent structure that maximizes cache efficiency and minimizes image size.

### Layer Ordering

Order instructions from least to most frequently changing:

```dockerfile
# 1. Base image (rarely changes)
FROM node:20-alpine AS base

# 2. System dependencies (changes occasionally)
RUN apk add --no-cache dumb-init

# 3. Working directory
WORKDIR /app

# 4. Package manifests (changes when deps change)
COPY package.json package-lock.json ./

# 5. Install dependencies (cached unless manifests change)
RUN npm ci --only=production

# 6. Application code (changes most frequently)
COPY . .
```

### Multi-Stage Builds

Use multi-stage builds to separate build-time and runtime dependencies. This dramatically reduces final image size.

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser

COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

USER appuser
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "dist/main.js"]
```

## .dockerignore

Always include a `.dockerignore` to prevent unnecessary files from entering the build context:

```
node_modules
.git
.gitignore
*.md
.env
.env.*
dist
coverage
.nyc_output
.vscode
.idea
docker-compose*.yml
Dockerfile*
.dockerignore
*.log
```

## Image Size Optimization

- Use Alpine-based images (`node:20-alpine` instead of `node:20`).
- Combine RUN commands with `&&` to reduce layers.
- Remove caches in the same layer they are created: `RUN npm ci && npm cache clean --force`.
- Use `--no-cache` for apk: `RUN apk add --no-cache curl`.
- Copy only what is needed in the final stage; avoid `COPY . .` in production stages.

## Security

### Non-Root User

Never run containers as root in production:

```dockerfile
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser
USER appuser
```

### Minimal Base Images

Prefer images in this order of security: `distroless` > `alpine` > `slim` > full.

### Additional Hardening

- Pin exact image digests for reproducibility in CI: `FROM node:20-alpine@sha256:abc123...`.
- Do not store secrets in images; use runtime environment variables or secret managers.
- Scan images with `docker scout` or `trivy` before pushing to a registry.

## Health Checks

Define health checks so orchestrators can detect unhealthy containers:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
```

Ensure the application exposes a `/health` endpoint that returns 200 when the service is ready.

## Environment Variables

- Use `ENV` for build-time defaults that are safe to bake into the image.
- Use runtime environment injection (`docker run -e` or Docker Compose `environment:`) for secrets and per-environment config.
- Never hardcode secrets in a Dockerfile.

```dockerfile
ENV NODE_ENV=production
ENV PORT=3000
```

## Docker Compose for Development

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: deps
    volumes:
      - .:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

## Common Patterns for Node.js Apps

- Use `dumb-init` or `tini` as PID 1 to handle signals correctly: `RUN apk add --no-cache dumb-init` then `ENTRYPOINT ["dumb-init", "--"]`.
- Set `NODE_ENV=production` before `npm ci` so dev dependencies are excluded.
- Use `npm ci` instead of `npm install` for deterministic installs.
- For Next.js, use the standalone output mode and copy only `.next/standalone` and `.next/static` to the final stage.
- For NestJS, build with `nest build` and run with `node dist/main.js`.

## Quick Reference

| Concern              | Recommendation                                |
|----------------------|-----------------------------------------------|
| Base image           | `node:20-alpine`                              |
| Process manager      | `dumb-init` or `tini`                         |
| User                 | Non-root (UID 1001)                           |
| Dependencies         | `npm ci --only=production`                    |
| Health check         | `HEALTHCHECK` instruction in Dockerfile       |
| Secrets              | Runtime injection, never baked into image     |
| Image scanning       | `docker scout` or `trivy` in CI               |
| Compose              | Use `depends_on` with `condition: service_healthy` |
