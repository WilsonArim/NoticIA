---
name: Architecture Decision Records
description: Document important technical decisions with context, rationale, and consequences for future reference
phase: 1
---

# Architecture Decision Records (ADRs)

## Purpose

Capture the "why" behind significant technical decisions so that future team members (including your future self) can understand the reasoning without archeology through old Slack messages and pull requests. ADRs are short documents that record a single decision along with its context and consequences.

## ADR Template

```markdown
# ADR-[NUMBER]: [TITLE]

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-[NUMBER]
**Date:** [YYYY-MM-DD]
**Decision Makers:** [Names or roles]

## Context

[Describe the situation and the forces at play. What problem are you facing?
What constraints exist? What options did you consider? Be specific about the
technical and business context that makes this decision necessary.]

## Decision

[State the decision clearly and concisely. Use active voice.
"We will use PostgreSQL as the primary database" not "It was decided that
PostgreSQL would be used."]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Risks
- [Risk and mitigation plan]

## Alternatives Considered

### [Alternative 1]
- **Pros:** [List]
- **Cons:** [List]
- **Why rejected:** [Reason]

### [Alternative 2]
- **Pros:** [List]
- **Cons:** [List]
- **Why rejected:** [Reason]
```

## When to Write an ADR

Write an ADR when a decision meets any of these criteria:

1. **Irreversibility** -- The decision is expensive to reverse (e.g., choosing a database, a programming language, a cloud provider).
2. **Cross-team impact** -- The decision affects more than one team or service.
3. **Significant trade-offs** -- You are explicitly choosing to accept a downside in exchange for a benefit.
4. **Recurring debate** -- The team has discussed this topic more than twice. Write it down and stop re-litigating.
5. **Compliance or security** -- The decision has regulatory, legal, or security implications.
6. **Pattern establishment** -- The decision sets a precedent that future work will follow (e.g., "all new services use gRPC").

### When NOT to Write an ADR

- Trivial choices with no meaningful trade-offs (e.g., choosing between two equivalent linting rules)
- Temporary decisions with a planned expiration (use a comment or ticket instead)
- Decisions already captured in another canonical document (e.g., a PRD already covers the product rationale)

## ADR Lifecycle

```
Proposed --> Accepted --> [Active]
                            |
                            +--> Deprecated (no longer relevant)
                            |
                            +--> Superseded by ADR-XXX (replaced by a new decision)
```

### Status Definitions

| Status | Meaning |
|---|---|
| **Proposed** | Under discussion. Not yet approved. Open for feedback. |
| **Accepted** | Approved and in effect. This is the current decision. |
| **Deprecated** | No longer relevant due to changed circumstances. The original reasoning was not wrong; the world changed. |
| **Superseded** | Replaced by a newer ADR. Always link to the replacement. |

### Rules

- Never delete an ADR. Change its status instead. The history of decisions is valuable.
- When superseding an ADR, update the old ADR's status to "Superseded by ADR-XXX" and reference the old ADR in the new one's Context section.
- Review ADRs during quarterly architecture reviews to identify any that are outdated.

## Naming Convention

Store ADRs in a dedicated directory in the repository:

```
docs/
  adr/
    ADR-001-use-postgresql-as-primary-database.md
    ADR-002-adopt-event-driven-architecture.md
    ADR-003-choose-react-for-frontend.md
    ADR-004-implement-cqrs-for-order-service.md
```

### Rules

- Use sequential numbering with zero-padded three-digit prefix: `ADR-001`, `ADR-002`, etc.
- Use lowercase kebab-case for the rest of the filename.
- The title in the filename should match the title in the document.
- Never reuse a number, even if the ADR is deprecated.

## Examples of Good vs Bad ADRs

### Bad ADR -- Vague and Missing Context

```markdown
# ADR-005: Use Redis

## Context
We need caching.

## Decision
Use Redis.

## Consequences
It will be faster.
```

**Why this is bad:**
- No explanation of what needs caching or why.
- No alternatives considered. Was Memcached evaluated? Local in-memory cache?
- Consequences are vague. "Faster" how? What are the trade-offs?
- No mention of operational burden, cost, or failure modes.

### Good ADR -- Specific and Well-Reasoned

```markdown
# ADR-005: Use Redis as Session Store and Rate-Limit Backend

**Status:** Accepted
**Date:** 2025-03-15
**Decision Makers:** Backend team lead, Platform engineer

## Context

Our application currently stores sessions in the PostgreSQL database.
Under load testing at 500 concurrent users, session reads add 12ms p99
latency to every authenticated request. Additionally, we need a rate-limiting
backend for the public API that can handle 10,000 checks per second
without adding significant latency.

We evaluated three options: Redis, Memcached, and DynamoDB.

## Decision

We will use Redis 7.x (hosted via AWS ElastiCache) as the backend
for both session storage and API rate limiting.

## Consequences

### Positive
- Session read latency drops from 12ms to under 1ms (benchmarked in staging)
- Redis supports atomic increment operations needed for sliding-window rate limiting
- Single operational dependency for two use cases reduces infrastructure complexity

### Negative
- Adds a new infrastructure dependency with its own failure modes
- Team has limited Redis operational experience; training needed
- Sessions are lost on Redis restart unless persistence is configured (RDB snapshots enabled)

### Risks
- If ElastiCache has an outage, all authenticated requests fail.
  Mitigation: fall back to PostgreSQL sessions with degraded latency.

## Alternatives Considered

### Memcached
- **Pros:** Simpler, slightly faster for pure key-value lookups
- **Cons:** No atomic increment, no persistence, no pub/sub
- **Why rejected:** Cannot support rate limiting without custom logic

### DynamoDB
- **Pros:** Fully managed, no server maintenance
- **Cons:** Higher latency (5-10ms), more expensive at our scale
- **Why rejected:** Latency defeats the purpose of moving off PostgreSQL
```

## Best Practices

1. **Write ADRs at decision time, not after.** If you write it a month later, you will forget key context.
2. **Keep them short.** One to two pages maximum. If it is longer, you are explaining the implementation, not the decision.
3. **Include the alternatives you rejected.** This is often the most valuable part for future readers.
4. **Use concrete numbers.** "Faster" is useless. "Reduces p99 latency from 120ms to 15ms" is useful.
5. **Link to evidence.** Reference benchmarks, user research, RFCs, or tickets that informed the decision.
6. **Make ADRs discoverable.** Add a table of contents or index file. An ADR nobody can find is an ADR that does not exist.
7. **Involve the right people.** List decision makers explicitly. This creates accountability and makes it clear who to ask for context.

## ADR Index Template

Maintain an index file at `docs/adr/README.md`:

```markdown
# Architecture Decision Records

| ADR | Title | Status | Date |
|---|---|---|---|
| [ADR-001](ADR-001-use-postgresql-as-primary-database.md) | Use PostgreSQL as primary database | Accepted | 2025-01-10 |
| [ADR-002](ADR-002-adopt-event-driven-architecture.md) | Adopt event-driven architecture | Accepted | 2025-01-22 |
| [ADR-003](ADR-003-choose-react-for-frontend.md) | Choose React for frontend | Superseded by ADR-007 | 2025-02-05 |
```

## When to Use This Skill

- When making any technical decision that is costly to reverse.
- When onboarding new team members who need to understand past decisions.
- During architecture reviews to audit and update existing decisions.
- When a previous decision needs to be revisited due to changed circumstances.
