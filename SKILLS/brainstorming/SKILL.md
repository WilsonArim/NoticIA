---
name: Brainstorming
description: Transform vague ideas into concrete, validated MVP plans through structured divergent and convergent thinking
phase: 1
---

# Brainstorming Skill

## Purpose

Turn ambiguous, early-stage ideas into well-defined MVP plans that a development team can act on. This skill applies a disciplined diverge-then-converge framework so that creative exploration is balanced with ruthless prioritization.

## Brainstorm Framework: Diverge then Converge

### Phase A -- Diverge (Expand the Space)

The goal is volume. Generate as many ideas, angles, and variations as possible without judgment.

1. **Problem Mining** -- List every problem the target user faces in the domain. Do not filter yet.
2. **How Might We** -- Reframe each problem as a "How might we..." question to open solution space.
3. **Crazy Eights** -- For each HMW question, sketch eight distinct solution approaches in eight minutes.
4. **Analogy Transfer** -- Look at how adjacent industries solve similar problems. Borrow patterns.
5. **Reverse Brainstorm** -- Ask "How could we make this problem worse?" then invert the answers.

### Phase B -- Converge (Collapse to Decisions)

The goal is clarity. Filter, rank, and commit.

1. **Dot Voting** -- Each stakeholder gets three votes. Identify the top-voted ideas.
2. **Impact vs Effort Matrix** -- Plot surviving ideas on a 2x2 grid (high impact / low effort = do first).
3. **One-Liner Test** -- If you cannot describe the idea in one sentence, it is not clear enough yet.
4. **Kill Criteria** -- Explicitly state what would make you abandon this idea. If nothing would, you are not being honest.

## Idea Validation Checklist

Before committing engineering time, every idea must pass these gates:

- [ ] **Problem Exists** -- Can you find 5+ real people who have this problem today?
- [ ] **Problem is Painful** -- Are people actively spending money, time, or effort to work around it?
- [ ] **Solution is Feasible** -- Can a small team build a working version in 2-4 weeks?
- [ ] **Market is Reachable** -- Do you have a clear channel to reach the first 100 users?
- [ ] **Differentiation is Real** -- Can you name the top 3 alternatives and explain why yours is better for a specific segment?
- [ ] **Business Model Exists** -- Is there a plausible path to revenue, even if indirect?
- [ ] **Team has Domain Fit** -- Does the team have (or can quickly acquire) the domain knowledge needed?

If fewer than 5 of 7 boxes are checked, the idea needs more research before proceeding.

## MVP Scoping: Must-Have vs Nice-to-Have

### Classification Rules

| Category | Definition | Example |
|---|---|---|
| **Must-Have** | Without this, the product does not solve the core problem at all | User authentication for a SaaS app |
| **Should-Have** | Significantly improves experience but core works without it | Password reset via email |
| **Nice-to-Have** | Delightful but clearly non-essential for launch | OAuth with 5 social providers |
| **Out of Scope** | Explicitly excluded from the MVP to prevent scope creep | Admin dashboard with analytics |

### Scoping Process

1. List every feature the team has discussed.
2. For each feature, ask: "If we launched without this, would the first 10 users still get value?" If yes, it is not Must-Have.
3. Cap Must-Have features at 3-5. If you have more, your scope is too large.
4. Write a one-sentence justification for every Must-Have feature.
5. Move everything else to Should-Have or lower.
6. Set a hard deadline. Features not done by the deadline ship in v2, not v1.

## Output Template

Every brainstorming session must produce a document in the following format:

```markdown
# [Project Name] -- MVP Plan

## Problem
[2-3 sentences describing the specific problem for a specific user segment]

## Solution
[2-3 sentences describing the proposed solution and why it is better than the status quo]

## Target User
[One sentence describing the primary user persona]

## MVP Features (Must-Have)
1. [Feature] -- [One sentence justification]
2. [Feature] -- [One sentence justification]
3. [Feature] -- [One sentence justification]

## Deferred Features (v2+)
- [Feature] -- [Reason for deferral]

## Tech Stack Suggestion
- Frontend: [Choice + rationale]
- Backend: [Choice + rationale]
- Database: [Choice + rationale]
- Hosting: [Choice + rationale]

## Estimated Timeline
| Phase | Duration | Deliverable |
|---|---|---|
| Setup & Architecture | X days | Project scaffold, CI/CD |
| Core Feature 1 | X days | [Deliverable] |
| Core Feature 2 | X days | [Deliverable] |
| Integration & QA | X days | Tested MVP |
| Launch | X days | Live product |

## Open Questions
- [Question that still needs an answer before or during development]

## Kill Criteria
- [Condition under which this project should be stopped]
```

## Anti-Patterns to Avoid

- **Brainstorming without a time box** -- Sessions longer than 60 minutes produce diminishing returns.
- **Skipping the convergence phase** -- A list of 50 ideas is not a plan. You must filter.
- **Building before validating** -- Talk to users before writing code. Five interviews cost less than one sprint.
- **MVP that is not Minimum** -- If your MVP takes more than 4 weeks, it is not minimum.
- **Consensus-driven prioritization** -- Prioritize by evidence and impact, not by who argues loudest.

## When to Use This Skill

- At the very start of a new product or feature initiative.
- When the team feels stuck and needs to reset direction.
- When pivoting after initial user feedback invalidates assumptions.
- During quarterly planning to evaluate new opportunities.
