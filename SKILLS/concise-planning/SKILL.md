---
name: Concise Planning
description: Structured planning before execution to reduce rework and align on goals
phase: 0
always_active: true
---

# Concise Planning

Always start with a plan. Never jump straight into code. A few minutes of structured
thinking prevents hours of rework, miscommunication, and wasted effort.

## Core Principle

Think first, then act. Every task above trivial complexity deserves a brief plan.
The plan is not a document for its own sake -- it is a forcing function for clarity.

## When to Plan

- Before implementing any feature or fix that touches more than one file.
- Before refactoring existing code.
- Before investigating a bug that is not immediately obvious.
- When a task has ambiguous requirements or multiple valid approaches.
- When coordinating work across multiple people or systems.

You do NOT need a formal plan for:
- Single-line fixes with obvious solutions.
- Renaming a variable or fixing a typo.
- Tasks where the entire scope fits in your head with zero uncertainty.

## Plan Template

Every plan should contain these four sections. Keep each section to 1-5 bullet points.

### 1. Goal
State the desired outcome in one sentence. Be specific.
- BAD: "Fix the auth bug"
- GOOD: "Ensure that expired JWT tokens return 401 instead of 500 on all protected endpoints"

### 2. Steps
List the concrete actions in order. Number them. Each step should be independently
verifiable.
1. Reproduce the issue with an expired token on /api/users
2. Trace the middleware chain to find where the error is swallowed
3. Add proper token validation with explicit expiry check
4. Update error handler to return 401 with structured error body
5. Add test case for expired token scenario

### 3. Risks
Identify what could go wrong or what you are uncertain about.
- "The auth middleware is shared across 12 routes -- changes may have side effects"
- "Not sure if the refresh token flow is affected"
- "No existing test coverage for this path"

### 4. Success Criteria
Define how you will know the task is done. These should be objectively verifiable.
- Expired tokens return 401 with `{ error: "token_expired" }` body
- All existing auth tests still pass
- New test covers the expired token case
- Manual verification against staging environment

## Iterative Planning

Plans are not set in stone. They are living documents that evolve as you learn more.

### Plan-Execute-Revise Cycle
1. Write the initial plan (5 minutes max).
2. Execute the first 1-2 steps.
3. Revise the plan based on what you learned.
4. Repeat until done.

### When to Revise
- You discover the problem is different from what you assumed.
- A step turns out to be more complex than expected.
- You find a simpler approach mid-execution.
- New requirements or constraints emerge.

### When to Escalate
- The revised plan is fundamentally different from the original.
- The scope has grown beyond the original estimate by more than 2x.
- You have been stuck on a single step for more than 30 minutes.

## Anti-Patterns

### Over-Planning
Writing a 50-line plan for a 10-line change. The plan should be proportional to the
complexity and risk of the task. If your plan is longer than your implementation,
something is wrong.

### Planning Without Context
Writing a plan before reading the relevant code. Always read first, then plan. Your
plan should reference specific files, functions, and data structures.

### Plan-and-Forget
Writing a plan and then ignoring it. The plan is a checklist -- refer back to it as
you work. Cross off steps as you complete them.

### Premature Architecture
Designing an entire system architecture when you only need to fix one endpoint. Plan
at the appropriate level of abstraction for the task at hand.

### Analysis Paralysis
Spending 45 minutes planning a 15-minute task. Set a time box: if the plan is not
done in 5 minutes for a small task or 15 minutes for a large task, start executing
and refine as you go.

## Rules

1. ALWAYS state the goal before writing any code.
2. ALWAYS list steps when the task has more than two actions.
3. NEVER skip the risks section -- even "no known risks" is a valid entry.
4. KEEP plans concise. Brevity is a feature, not a bug.
5. REVISE the plan when reality diverges from expectations.
6. SHARE the plan with collaborators before executing when working in a team.
7. TIME-BOX planning to prevent analysis paralysis.

## Quick Reference

For small tasks (under 30 min):
```
Goal: [one sentence]
Steps: [numbered list, 2-4 items]
```

For medium tasks (30 min to half day):
```
Goal: [one sentence]
Steps: [numbered list, 4-8 items]
Risks: [1-3 bullets]
Success: [2-4 criteria]
```

For large tasks (more than half day):
```
Full template with all four sections.
Consider breaking into multiple smaller plans.
```
