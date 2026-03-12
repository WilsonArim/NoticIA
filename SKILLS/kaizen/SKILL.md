---
name: Kaizen
description: Continuous improvement mindset applied to code, process, and developer experience
phase: 0
always_active: true
---

# Kaizen

Kaizen means "change for the better." In software, it is the disciplined practice of
making small, continuous improvements to code, processes, and tools. Not as a separate
initiative, but as a natural part of daily work.

## Core Principle

Leave every file, system, and process slightly better than you found it. Improvement
is not a project -- it is a habit.

## The Boy Scout Rule

"Always leave the campground cleaner than you found it."

When you open a file to make a change, look for one small improvement you can make
while you are there. Not a rewrite. Not a refactor epic. One thing:

- Rename an unclear variable.
- Add a missing type annotation.
- Remove a dead import.
- Fix a misleading comment.
- Extract a magic number into a named constant.

### Boundaries
- The improvement must be small enough to include in your current commit.
- The improvement must not change the behavior of the system.
- The improvement must not require its own review cycle.
- If the improvement is larger than these bounds, create a ticket instead.

## When to Suggest Improvements

### During Code Review
This is the primary venue for improvement suggestions. When reviewing code:
- Focus on patterns, not just the specific lines changed.
- Distinguish between "must fix" (bugs, security) and "consider improving" (style,
  performance).
- Provide the improved version, not just criticism.

### During Implementation
When you encounter code that could be better while working on your own task:
- Small fixes: apply the Boy Scout Rule and include in your commit.
- Medium fixes: note them and create a separate commit or ticket.
- Large fixes: document the issue and propose it for a future sprint.

### During Debugging
Debugging often reveals structural problems. When you fix a bug:
- Ask: "Why was this bug possible? What structural change would prevent this class
  of bug entirely?"
- If the answer is a reasonable refactor, propose it.

### During Onboarding
New team members see the codebase with fresh eyes. Their confusion points to
documentation gaps, naming problems, and unnecessary complexity. Capture their
feedback systematically.

## Improvement Categories

### Performance
- Identify N+1 queries and batch them.
- Cache expensive computations that are called repeatedly with the same inputs.
- Replace synchronous blocking operations with async alternatives.
- Measure before and after. Performance improvements without benchmarks are guesses.

Trigger: Response times exceeding SLA, high CPU/memory usage, user complaints about
speed.

### Readability
- Replace clever code with clear code. Clever is the enemy of maintainable.
- Break long functions into smaller ones with descriptive names.
- Add type annotations where inference is not obvious.
- Use domain language in variable and function names.

Trigger: You need to read a function more than twice to understand it. A colleague
asks "what does this do?"

### Security
- Remove hardcoded credentials and replace with environment variables.
- Add input validation and sanitization at system boundaries.
- Update dependencies with known vulnerabilities.
- Add rate limiting to public endpoints.
- Review and tighten permissions (database roles, API scopes, file access).

Trigger: Dependency audit warnings, penetration test results, new OWASP guidelines,
any security incident.

### Developer Experience (DX)
- Reduce build times. Every second matters when it runs hundreds of times per day.
- Improve error messages. A good error message tells the developer what happened,
  why, and what to do about it.
- Automate repetitive tasks with scripts or tooling.
- Keep documentation close to the code it describes.
- Simplify local development setup. Ideally: clone, install, run.

Trigger: New team member takes more than 30 minutes to set up the project. A common
task requires more than 3 manual steps. Developers frequently ask the same questions.

## How to Propose Improvements Without Being Intrusive

### Frame as Suggestions, Not Demands
- BAD: "This function is terrible and needs to be rewritten."
- GOOD: "This function has grown complex. A possible improvement would be to extract
  the validation logic into a separate function, which would also make it easier to
  test independently."

### Provide Context and Rationale
Explain the WHY behind the improvement. People resist changes they do not understand.
- "Extracting this into a hook would reduce duplication across these three components
  and make the auth logic testable in isolation."

### Separate Concerns
Never mix improvement suggestions with critical bug feedback. Use clear labels:
- MUST: Security vulnerability, data loss risk, broken functionality.
- SHOULD: Performance issue, maintainability concern, missing test.
- COULD: Style improvement, minor readability enhancement, nice-to-have.

### Pick Your Battles
Not every improvement is worth the discussion cost. Consider:
- How often is this code touched? (Frequently changed code benefits more from improvements.)
- How many people work with this code? (Shared code has higher improvement ROI.)
- How risky is the change? (Low-risk improvements are easier to justify.)

## Refactoring Triggers

These are signals that code needs improvement. Not every trigger demands immediate
action, but each should be acknowledged and tracked.

1. **Duplication**: The same logic exists in three or more places.
2. **Long Functions**: A function exceeds 40-50 lines or has more than 3 levels of
   nesting.
3. **Primitive Obsession**: Using strings and numbers where a domain type would be
   clearer (e.g., `string` instead of `EmailAddress`).
4. **Feature Envy**: A function that spends more time working with another module's
   data than its own.
5. **Shotgun Surgery**: A single change requires edits to 5 or more files.
6. **Dead Code**: Functions, variables, or branches that are never executed.
7. **Comment Crutches**: Comments explaining WHAT the code does instead of the code
   being self-explanatory.
8. **Test Brittleness**: Tests that break when implementation details change but
   behavior stays the same.

## Rules

1. ALWAYS apply the Boy Scout Rule when editing a file.
2. NEVER let the pursuit of improvement block delivery of working features.
3. ALWAYS measure before optimizing performance. Intuition about bottlenecks is
   frequently wrong.
4. ALWAYS separate improvement commits from feature commits.
5. PROPOSE improvements with rationale, not just opinion.
6. TRACK larger improvements as tickets rather than letting them live only in your head.
7. PRIORITIZE improvements that reduce bug surface area over cosmetic changes.
8. CELEBRATE improvements. Acknowledge when the team makes the codebase better.
9. REVIEW improvement proposals with the same rigor as feature code.
10. ACCEPT that not every improvement will be adopted. The suggestion still has value
    even if the team decides the cost-benefit ratio does not justify it now.
