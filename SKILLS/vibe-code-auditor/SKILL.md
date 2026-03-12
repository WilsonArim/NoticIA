---
name: Vibe Code Auditor
description: Deterministic code quality audit with scoring across readability, maintainability, performance, security, and testing
phase: 5
---

# Vibe Code Auditor

## Purpose

The Vibe Code Auditor provides a structured, repeatable quality assessment of any codebase or module. It produces a numerical score across five dimensions, identifies improvement priorities, and tracks technical debt over time. The goal is to replace subjective "this feels messy" assessments with deterministic, actionable evaluations.

## Scoring Dimensions

Every audit evaluates five dimensions. Each dimension is scored from 1 to 10.

### 1. Readability (Weight: 20%)
How easily can a new developer understand this code?

| Score | Criteria                                                                 |
|-------|--------------------------------------------------------------------------|
| 1-3   | Cryptic names, no comments, deep nesting, inconsistent formatting        |
| 4-6   | Mostly readable, some unclear sections, minor inconsistencies            |
| 7-8   | Clean naming, consistent style, self-documenting, minimal comments needed|
| 9-10  | Exemplary clarity, reads like prose, perfect naming, zero ambiguity      |

Evaluation points:
- Variable and function naming quality
- Consistent code style and formatting
- Appropriate use of comments (why, not what)
- Nesting depth (max 3 levels)
- Function length (max 30 lines)
- File length (max 300 lines)

### 2. Maintainability (Weight: 25%)
How easy is it to modify, extend, or fix this code?

| Score | Criteria                                                                 |
|-------|--------------------------------------------------------------------------|
| 1-3   | Tightly coupled, no separation of concerns, changes break unrelated code |
| 4-6   | Some modularity, but dependencies are implicit, moderate coupling        |
| 7-8   | Well-structured modules, clear interfaces, changes are localized         |
| 9-10  | Highly modular, dependency injection, open for extension, closed for mod |

Evaluation points:
- Separation of concerns
- Coupling between modules (low is better)
- Cohesion within modules (high is better)
- Single Responsibility adherence
- DRY principle compliance
- Presence and quality of type definitions
- Error handling consistency

### 3. Performance (Weight: 20%)
Does the code avoid unnecessary computational waste?

| Score | Criteria                                                                 |
|-------|--------------------------------------------------------------------------|
| 1-3   | N+1 queries, memory leaks, O(n^2) where O(n) is possible, no caching    |
| 4-6   | Generally okay, some missed optimizations, no profiling evidence         |
| 7-8   | Efficient algorithms, appropriate caching, lazy loading where beneficial |
| 9-10  | Profiled and optimized, measured performance budgets, zero waste          |

Evaluation points:
- Algorithm complexity appropriateness
- Database query efficiency (no N+1)
- Memory management (no leaks, reasonable allocations)
- Bundle size impact (frontend)
- Caching strategy effectiveness
- Unnecessary re-renders (frontend frameworks)

### 4. Security (Weight: 20%)
Is the code protected against common attack vectors?

| Score | Criteria                                                                 |
|-------|--------------------------------------------------------------------------|
| 1-3   | SQL injection possible, no input validation, secrets in code             |
| 4-6   | Basic protections, some gaps in validation, incomplete auth checks       |
| 7-8   | OWASP Top 10 addressed, input validated, proper auth and authz           |
| 9-10  | Defense in depth, security headers, audit logging, zero trust approach   |

Evaluation points:
- Input validation and sanitization
- Authentication and authorization completeness
- Secrets management
- Dependency vulnerability status
- Security headers configuration
- XSS, CSRF, and injection prevention

### 5. Testing (Weight: 15%)
How well is the code verified by automated tests?

| Score | Criteria                                                                 |
|-------|--------------------------------------------------------------------------|
| 1-3   | No tests, or tests that do not actually verify behavior                  |
| 4-6   | Some tests exist, but coverage is patchy, edge cases missing             |
| 7-8   | Good coverage, tests verify behavior, edge cases covered                 |
| 9-10  | Comprehensive suite, TDD evident, mutation testing, no flaky tests       |

Evaluation points:
- Test coverage percentage (line and branch)
- Test quality (testing behavior vs implementation)
- Edge case coverage
- Test naming and readability
- Test isolation (no interdependent tests)
- CI integration and enforcement

## Scoring Scale

**Overall Score** = Weighted average across all five dimensions.

| Overall Score | Grade | Interpretation                                  |
|---------------|-------|-------------------------------------------------|
| 9.0 - 10.0   | A+    | Exceptional. Reference-quality code.             |
| 8.0 - 8.9    | A     | Excellent. Production-ready, minimal issues.     |
| 7.0 - 7.9    | B     | Good. Solid foundation with minor improvements.  |
| 6.0 - 6.9    | C     | Acceptable. Noticeable issues, plan to address.  |
| 5.0 - 5.9    | D     | Below standard. Significant improvements needed. |
| Below 5.0    | F     | Critical. Major rework required before shipping.  |

## Automatic Triggers

Run a vibe audit automatically when:
- A new module or feature branch is ready for review.
- A sprint or milestone is completed.
- Technical debt is suspected but not quantified.
- Onboarding a new team member to an existing codebase.
- Before a major release or deployment.
- After significant refactoring to verify improvements.

## Audit Report Template

```markdown
# Vibe Code Audit Report
**Module/Project**: [Name]
**Date**: [YYYY-MM-DD]
**Auditor**: [Name or AI Agent]
**Files Reviewed**: [Count]
**Lines of Code**: [Count]

## Score Summary

| Dimension       | Score | Weight | Weighted |
|-----------------|-------|--------|----------|
| Readability     | X/10  | 20%    | X.XX     |
| Maintainability | X/10  | 25%    | X.XX     |
| Performance     | X/10  | 20%    | X.XX     |
| Security        | X/10  | 20%    | X.XX     |
| Testing         | X/10  | 15%    | X.XX     |
| **Overall**     |       |        | **X.XX** |

**Grade**: [A+ / A / B / C / D / F]

## Top Findings
1. [Most critical issue with location and suggested fix]
2. [Second most critical issue]
3. [Third most critical issue]

## Improvement Priorities
1. [Highest impact improvement]
2. [Second highest impact improvement]
3. [Third highest impact improvement]

## Technical Debt Estimate
- **Current debt**: [Hours/days to resolve identified issues]
- **Trend**: [Increasing / Stable / Decreasing compared to last audit]
- **Risk**: [Low / Medium / High if left unaddressed]
```

## Improvement Priorities

After scoring, prioritize improvements using this matrix:

| Impact / Effort | Low Effort       | High Effort       |
|-----------------|------------------|-------------------|
| **High Impact** | Do immediately   | Plan for next sprint |
| **Low Impact**  | Do when convenient | Defer or skip     |

Focus on dimensions with the lowest scores first, weighted by their importance to the project. Security issues always take priority regardless of score differentials.

## Technical Debt Assessment

Classify identified debt into three categories:

1. **Deliberate debt**: Conscious shortcuts taken with a documented plan to resolve. Track with tagged issues.
2. **Accidental debt**: Issues discovered during audit that were not intentionally introduced. Fix in the current or next sprint.
3. **Bit rot**: Degradation over time from changing requirements, outdated dependencies, or abandoned patterns. Schedule periodic cleanup.

For each debt item, record:
- **Location**: File path and line range.
- **Description**: What the issue is.
- **Impact**: What happens if it is not addressed.
- **Effort**: Estimated time to resolve (hours or story points).
- **Priority**: Based on the impact/effort matrix above.
