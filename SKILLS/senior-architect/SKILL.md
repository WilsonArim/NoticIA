---
name: Senior Architect
description: Comprehensive software architecture guidance covering principles, system design, scalability, and strategic decision-making
phase: 2
---

# Senior Architect

## Core Architecture Principles

### Separation of Concerns (SoC)
Every module, class, or function should address a single part of the overall functionality. Never mix data access logic with business rules or presentation logic. When a component does more than one thing, split it.

### Single Responsibility Principle (SRP)
A class or module should have exactly one reason to change. If you find yourself describing what a module does using the word "and," it likely violates SRP. Refactor until each unit owns a single, well-defined behavior.

### Dependency Inversion Principle (DIP)
High-level modules must not depend on low-level modules. Both should depend on abstractions (interfaces or types). This decouples your business logic from infrastructure concerns like databases, HTTP frameworks, and third-party services.

### Open/Closed Principle
Modules should be open for extension but closed for modification. Favor composition, strategy patterns, and plugin architectures over modifying existing, tested code.

### Least Astonishment
Design APIs and interfaces so that their behavior matches what a developer would reasonably expect. Surprising behavior introduces bugs.

## System Design Checklist

Before writing any code for a new system or feature, answer these questions:

1. **Requirements clarity** -- Are functional and non-functional requirements documented?
2. **Data model** -- What are the core entities, their relationships, and access patterns?
3. **API contract** -- Are the endpoints, request/response shapes, and error formats defined?
4. **Authentication and authorization** -- Who can access what? What is the auth mechanism?
5. **Error handling** -- How are errors surfaced to the user and logged internally?
6. **Observability** -- What metrics, logs, and traces will you capture?
7. **Deployment** -- How will the system be deployed, scaled, and rolled back?
8. **Data migration** -- Are there existing data or schema changes needed?
9. **Third-party dependencies** -- What external services does this depend on? What are their SLAs?
10. **Failure modes** -- What happens when a dependency is unavailable?

## Scalability Considerations

### Vertical vs Horizontal Scaling
- **Vertical**: Increase resources on a single machine. Simpler but has hard limits.
- **Horizontal**: Add more instances behind a load balancer. Requires stateless design.

### Statelessness
Design services so that any instance can handle any request. Store session data in external stores (Redis, database) rather than in-memory. This is a prerequisite for horizontal scaling.

### Caching Strategy
- **Application-level**: In-memory caches (LRU) for hot data within a single process.
- **Distributed cache**: Redis or Memcached for shared state across instances.
- **CDN**: For static assets and cacheable API responses.
- **Cache invalidation**: Define TTLs and invalidation triggers. Stale data is a common source of bugs.

### Database Scaling
- Read replicas for read-heavy workloads.
- Connection pooling (PgBouncer, Supabase built-in pooler).
- Partitioning and sharding for very large datasets.
- Consider eventual consistency where strong consistency is not required.

## Monolith vs Microservices Decision Framework

| Factor | Choose Monolith | Choose Microservices |
|---|---|---|
| Team size | Small (1-8 developers) | Large (multiple autonomous teams) |
| Domain complexity | Single, well-understood domain | Multiple distinct bounded contexts |
| Deployment frequency | Uniform release cadence | Independent deployment per service |
| Operational maturity | Limited DevOps capability | Strong CI/CD, observability, orchestration |
| Performance requirements | Low-latency internal calls needed | Network latency between services is acceptable |
| Data consistency | Strong consistency across features | Eventual consistency is tolerable |

**Default recommendation**: Start with a well-structured monolith. Extract services only when there is a clear organizational or scaling reason to do so. Premature decomposition into microservices adds operational complexity without proportional benefit.

## Layer Architecture

Organize code into layers with strict dependency direction (outer layers depend on inner layers, never the reverse):

### Layer 1 -- Domain / Entities
Pure business objects and rules. No dependencies on frameworks, databases, or I/O. This layer changes only when business rules change.

### Layer 2 -- Application / Use Cases
Orchestrates domain objects to fulfill a specific user action. Defines input/output boundaries (DTOs). Depends only on domain layer abstractions.

### Layer 3 -- Infrastructure / Adapters
Implements interfaces defined by inner layers. Contains database repositories, HTTP clients, message queue consumers, file system access. All framework-specific code lives here.

### Layer 4 -- Presentation / Delivery
HTTP controllers, CLI handlers, GraphQL resolvers. Translates external input into use case calls and formats responses.

### Dependency Rule
Dependencies always point inward. The domain layer never imports from infrastructure. Use dependency injection to provide concrete implementations at runtime.

## Error Handling Strategy

### Classification
- **Operational errors**: Expected failures (network timeout, invalid input, not found). Handle gracefully with appropriate HTTP status codes and user-facing messages.
- **Programmer errors**: Bugs (null reference, type mismatch). These should crash the process in development and be caught by global error handlers in production.

### Implementation Guidelines
1. Define a base `AppError` class with `statusCode`, `code`, `message`, and optional `details`.
2. Create specific error subclasses: `ValidationError`, `NotFoundError`, `AuthorizationError`, `ConflictError`.
3. Use a global error handler middleware that catches all errors, logs them, and returns a consistent JSON response.
4. Never expose internal stack traces or implementation details to the client.
5. Always log the full error context (stack trace, request ID, user ID) server-side.
6. Use structured logging (JSON format) so errors are searchable and parseable.

### Error Response Format
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested user was not found.",
    "details": {}
  }
}
```

### Retry and Circuit Breaker
For external service calls, implement retry with exponential backoff. After repeated failures, use a circuit breaker pattern to fail fast and avoid cascading failures. Libraries like `cockatiel` (Node.js) provide these primitives.

## Architecture Review Checklist

Before approving any architectural decision, verify:

- [ ] The design handles the expected load with headroom.
- [ ] There is a clear data model with defined access patterns.
- [ ] Error scenarios are explicitly handled, not just the happy path.
- [ ] The system can be tested at each layer independently.
- [ ] There is an observability plan (logging, metrics, alerting).
- [ ] Security concerns are addressed (input validation, auth, rate limiting).
- [ ] The design is documented with an ADR (Architecture Decision Record).
- [ ] The team understands and agrees with the tradeoffs made.
