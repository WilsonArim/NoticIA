---
name: Architecture Patterns
description: Clean Architecture, Domain-Driven Design, and Hexagonal Architecture patterns with practical guidance on when and how to apply each
phase: 2
---

# Architecture Patterns

## Overview

This skill covers three complementary architecture patterns. They share the same core idea -- isolate business logic from infrastructure -- but differ in vocabulary, emphasis, and practical application.

## Clean Architecture

### When to Use
- Medium to large applications where business logic must survive framework changes.
- Projects with multiple delivery mechanisms (REST API, CLI, message queue consumer).
- Teams that need clear boundaries for parallel development.

### Layers (Inside-Out)

**Entities (Domain)**
- Pure business objects with behavior. No framework annotations, no ORM decorators.
- Example: `User`, `Order`, `Invoice` classes with validation and business rules.
- These change only when business rules change.

**Use Cases (Application)**
- One class per use case: `CreateOrderUseCase`, `CancelSubscriptionUseCase`.
- Orchestrates entities and calls repository/service interfaces.
- Defines its own input/output DTOs. Never returns entities directly.
- Contains no HTTP, database, or framework-specific code.

**Interface Adapters**
- Controllers that translate HTTP requests into use case input DTOs.
- Presenters that format use case output into HTTP responses.
- Repository implementations that map between entities and database rows.
- Gateway implementations for external APIs.

**Frameworks and Drivers**
- Express/Fastify/Next.js configuration.
- Database connection setup (Prisma client, Drizzle instance).
- Third-party SDK initialization.
- This is the outermost, most volatile layer.

### Dependency Rule
All source code dependencies point inward. A use case never imports from a controller. An entity never imports from a repository implementation. Use interfaces (TypeScript types or abstract classes) and dependency injection.

### Practical File Structure
```
src/
  domain/
    entities/
    value-objects/
    errors/
  application/
    use-cases/
    interfaces/       # Repository and service interfaces
    dtos/
  infrastructure/
    repositories/     # Concrete implementations
    services/
    config/
  presentation/
    http/
      controllers/
      middleware/
      routes/
```

## Domain-Driven Design (DDD)

### When to Use
- Complex business domains with rich rules that go beyond CRUD.
- Projects where domain experts and developers need a shared language.
- Systems with multiple subdomains that need clear boundaries.

### Core Concepts

**Ubiquitous Language**
Use the same terminology in code, documentation, and conversations with stakeholders. If the business says "policy," the code has a `Policy` class, not a `Rule` or `Config`.

**Bounded Contexts**
A bounded context is a boundary within which a particular domain model is defined and applicable. The same real-world concept (e.g., "Customer") may have different representations in different contexts (Sales vs Support). Do not force a single shared model across contexts.

**Aggregates**
A cluster of domain objects treated as a single unit for data changes. Every aggregate has a root entity that controls access. External objects reference the aggregate only through the root.

Rules:
- Each aggregate enforces its own invariants.
- Transactions should not span multiple aggregates.
- Reference other aggregates by ID, not by direct object reference.

**Entities**
Objects with a unique identity that persists over time. Two entities with the same attributes but different IDs are different objects. Example: two users with the same name are still different users.

**Value Objects**
Objects defined by their attributes, not identity. Two value objects with the same attributes are interchangeable. Example: `Money(100, "USD")` equals another `Money(100, "USD")`. Value objects are immutable.

**Domain Events**
Something that happened in the domain that other parts of the system care about. Example: `OrderPlaced`, `PaymentReceived`, `SubscriptionCancelled`. Use events to decouple bounded contexts.

**Domain Services**
Operations that do not naturally belong to any single entity or value object. Example: `PricingService.calculateDiscount(order, customer)`.

**Repositories**
Abstractions for persisting and retrieving aggregates. The domain defines the interface; the infrastructure provides the implementation. A repository should feel like an in-memory collection.

### Anti-Patterns to Avoid
- **Anemic domain model**: Entities that are just data bags with getters/setters while all logic lives in services. Push behavior into entities.
- **God aggregate**: An aggregate that encompasses too many entities. Keep aggregates small and focused.
- **Shared kernel overuse**: Sharing too much code between bounded contexts creates tight coupling.

## Hexagonal Architecture (Ports and Adapters)

### When to Use
- Applications that need to be testable without external dependencies.
- Systems that must support multiple input/output mechanisms.
- Teams that want explicit boundaries between application logic and the outside world.

### Core Concepts

**The Hexagon (Application Core)**
Contains all business logic. Knows nothing about the outside world. Defines ports (interfaces) that describe how it wants to interact with external systems.

**Ports**
Interfaces defined by the application core. Two types:
- **Driving ports (primary)**: How the outside world triggers the application. Example: `CreateUserPort` with method `execute(input): output`.
- **Driven ports (secondary)**: How the application accesses external resources. Example: `UserRepository`, `EmailSender`, `PaymentGateway`.

**Adapters**
Concrete implementations that connect to the ports:
- **Driving adapters**: HTTP controllers, CLI handlers, message queue consumers, scheduled jobs. They call driving ports.
- **Driven adapters**: PostgreSQL repository, SMTP email sender, Stripe payment adapter. They implement driven ports.

### Testing Advantage
Replace any driven adapter with a test double (in-memory repository, mock email sender) without changing the application core. Test business logic in isolation.

## Comparison Table

| Aspect | Clean Architecture | DDD | Hexagonal |
|---|---|---|---|
| Primary focus | Layer separation and dependency direction | Domain modeling and strategic design | Port/adapter isolation for testability |
| Key concept | Dependency rule (inward only) | Bounded contexts and aggregates | Ports (interfaces) and adapters (implementations) |
| Best for | Applications needing framework independence | Complex business domains | Systems needing high testability and multiple I/O channels |
| Complexity cost | Medium -- requires clear layer boundaries | High -- requires domain expertise and modeling effort | Medium -- requires discipline in port/adapter definitions |
| Team prerequisite | Understanding of SOLID principles | Access to domain experts, willingness to invest in modeling | Comfort with interfaces and dependency injection |
| Can combine with others | Yes, often combined with DDD concepts | Yes, tactical patterns fit inside Clean/Hexagonal layers | Yes, naturally complements Clean Architecture |

## Decision Guide

1. **Simple CRUD app**: None of these patterns is necessary. Use a straightforward MVC or service-layer approach.
2. **Medium complexity, single domain**: Clean Architecture or Hexagonal. Pick based on team familiarity.
3. **High complexity, multiple subdomains**: DDD for strategic design, combined with Clean or Hexagonal for tactical implementation.
4. **Need extreme testability**: Hexagonal provides the most explicit mechanism for swapping dependencies.

## Common Mistakes

- Applying DDD to a CRUD application. The overhead is not justified.
- Creating too many layers for a small project. Two layers (domain + infrastructure) are often sufficient.
- Treating these patterns as rigid frameworks rather than guidelines. Adapt to your context.
- Over-abstracting: creating interfaces for things that will never have a second implementation. Be pragmatic.
