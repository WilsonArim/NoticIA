---
name: Product Manager Toolkit
description: PRD templates, RICE prioritization, user stories, and feature prioritization for structured product planning
phase: 1
---

# Product Manager Toolkit

## Purpose

Provide a repeatable, structured approach to product planning that bridges the gap between business goals and engineering execution. This toolkit ensures nothing falls through the cracks between "we should build X" and "here is the spec for X."

## PRD Template (Product Requirements Document)

```markdown
# PRD: [Feature/Product Name]

**Author:** [Name]
**Status:** Draft | In Review | Approved | Deprecated
**Last Updated:** [Date]
**Stakeholders:** [List]

## 1. Overview
[2-3 sentences summarizing what this product/feature is and why it matters]

## 2. Problem Statement
[Describe the user problem with evidence: support tickets, user interviews, analytics data]

## 3. Goals and Success Metrics
| Goal | Metric | Target | Measurement Method |
|---|---|---|---|
| [Goal 1] | [KPI] | [Number] | [How you measure] |

## 4. User Stories
[See User Story format below]

## 5. Scope
### In Scope
- [Item]

### Out of Scope
- [Item] -- [Reason]

## 6. Design and UX
[Link to mockups, wireframes, or design specs]

## 7. Technical Considerations
[Known constraints, dependencies, APIs, performance requirements]

## 8. Timeline and Milestones
| Milestone | Date | Owner |
|---|---|---|
| [Milestone] | [Date] | [Person] |

## 9. Risks and Mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| [Risk] | High/Med/Low | High/Med/Low | [Plan] |

## 10. Open Questions
- [Question] -- Owner: [Person] -- Due: [Date]
```

### PRD Quality Checklist

- [ ] Problem is backed by data, not assumptions
- [ ] Success metrics are measurable and have specific targets
- [ ] Scope section explicitly lists what is excluded
- [ ] Every user story has acceptance criteria
- [ ] Technical risks are identified with mitigations
- [ ] Timeline has buffer for unknowns (add 30% minimum)

## RICE Prioritization Framework

RICE scores help objectively compare features when everything feels urgent.

### Formula

```
RICE Score = (Reach x Impact x Confidence) / Effort
```

### Factor Definitions

| Factor | Definition | Scale |
|---|---|---|
| **Reach** | How many users will this affect per quarter? | Actual number (e.g., 500 users) |
| **Impact** | How much will this move the target metric per user? | 3 = massive, 2 = high, 1 = medium, 0.5 = low, 0.25 = minimal |
| **Confidence** | How sure are you about Reach and Impact estimates? | 100% = high (data-backed), 80% = medium (educated guess), 50% = low (gut feel) |
| **Effort** | How many person-months will this take? | Actual estimate (e.g., 2 person-months) |

### Example Calculation

| Feature | Reach | Impact | Confidence | Effort | RICE Score |
|---|---|---|---|---|---|
| Onboarding redesign | 1000 | 2 | 80% | 3 | 533 |
| Export to CSV | 200 | 1 | 100% | 0.5 | 400 |
| Dark mode | 800 | 0.5 | 50% | 2 | 100 |

Decision: Onboarding redesign ships first, then CSV export. Dark mode goes to backlog.

### RICE Pitfalls

- Do not inflate Confidence to win arguments. Be honest about what you do not know.
- Effort must include QA, documentation, and deployment -- not just coding.
- Revisit scores quarterly. Reach and Impact change as the product evolves.

## User Story Format

### Structure

```
As a [type of user],
I want [action or capability],
so that [benefit or outcome].
```

### Rules for Good User Stories (INVEST)

- **I**ndependent -- Can be developed without depending on other stories
- **N**egotiable -- Details can be discussed; the story is not a contract
- **V**aluable -- Delivers value to the user, not just to the system
- **E**stimable -- Team can estimate the effort required
- **S**mall -- Can be completed in a single sprint
- **T**estable -- Has clear criteria for "done"

### Acceptance Criteria Format

Write acceptance criteria using Given/When/Then:

```
Given [precondition],
When [action],
Then [expected result].
```

### Example

```
User Story:
As a free-tier user,
I want to upgrade to a paid plan from the settings page,
so that I can access premium features without contacting support.

Acceptance Criteria:
1. Given I am on the Settings page and logged in as a free-tier user,
   When I click "Upgrade Plan",
   Then I see a comparison of available paid plans with pricing.

2. Given I have selected a plan and entered payment details,
   When I click "Confirm Payment",
   Then my account is upgraded immediately and I receive a confirmation email.

3. Given the payment fails,
   When the payment processor returns an error,
   Then I see a clear error message and my account remains on the free tier.
```

## Feature Prioritization Matrix

When RICE alone is not sufficient, use a multi-dimensional matrix:

| Feature | RICE Score | Strategic Alignment | Technical Risk | User Demand | Final Priority |
|---|---|---|---|---|---|
| [Feature] | [Score] | High/Med/Low | High/Med/Low | High/Med/Low | P0/P1/P2/P3 |

### Priority Levels

- **P0 (Critical)** -- Must ship this cycle. Blocks other work or addresses critical user pain.
- **P1 (High)** -- Should ship this cycle if capacity allows. Clear user value.
- **P2 (Medium)** -- Plan for next cycle. Important but not urgent.
- **P3 (Low)** -- Backlog. Revisit during next planning session.

### Decision Rules

1. Any feature with Technical Risk = High must have a spike or proof-of-concept before committing to a deadline.
2. Features with User Demand = High but low RICE score likely have a reach problem -- investigate distribution.
3. Never have more than 3 P0 items. If everything is critical, nothing is.
4. Review and re-prioritize at the start of every cycle, not just once.

## When to Use This Skill

- When planning a new feature or product from scratch.
- During sprint planning to decide what to build next.
- When stakeholders disagree on priorities and you need an objective framework.
- When writing specs that will be handed to engineers for implementation.
