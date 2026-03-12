---
name: Code Review Checklist
description: Systematic approach to catching bugs, security issues, and quality problems in pull requests
phase: 5
---

# Code Review Checklist

## Review Checklist

Every pull request should be evaluated across these dimensions, in order of priority:

### 1. Correctness and Logic
- Does the code do what the PR description claims?
- Are edge cases handled (null, empty, boundary values, negative numbers)?
- Are error paths handled gracefully with appropriate error messages?
- Is the logic free from off-by-one errors?
- Are race conditions possible in concurrent scenarios?
- Does the code handle failure modes (network errors, timeouts, disk full)?

### 2. Security
- Is user input validated and sanitized before use?
- Are SQL queries parameterized (no string concatenation)?
- Are secrets, API keys, or tokens absent from the code?
- Is authentication checked on all protected routes?
- Is authorization enforced (not just authentication)?
- Are sensitive data fields excluded from logs and error messages?
- Are CORS headers configured correctly?

### 3. Performance
- Are there N+1 query patterns in database access?
- Are large datasets paginated rather than loaded entirely into memory?
- Are expensive computations memoized or cached where appropriate?
- Are database queries using indexes effectively?
- Are unnecessary re-renders avoided in frontend components?
- Is the bundle size impact acceptable?

### 4. Readability and Maintainability
- Are variable and function names descriptive and consistent?
- Is the code self-documenting, or are complex sections commented?
- Does the code follow the project's established patterns and conventions?
- Is there unnecessary duplication that should be extracted?
- Are abstractions at the right level (not too abstract, not too concrete)?
- Are magic numbers replaced with named constants?

### 5. Tests
- Are new behaviors covered by tests?
- Do tests follow the AAA pattern (Arrange, Act, Assert)?
- Are tests testing behavior, not implementation details?
- Are edge cases tested?
- Are test names descriptive enough to serve as documentation?
- Is test coverage maintained or improved?

## Common Code Smells

Watch for these patterns during review:

| Smell                    | Symptom                                             | Suggested Fix                          |
|--------------------------|-----------------------------------------------------|----------------------------------------|
| Long method              | Function exceeds 30 lines                           | Extract into smaller functions         |
| Deep nesting             | More than 3 levels of indentation                   | Use early returns, extract functions   |
| Feature envy             | Method accesses another object's data excessively    | Move method to the data owner          |
| Primitive obsession      | Using strings/numbers where a type would be clearer  | Create domain types or enums           |
| Boolean blindness        | Functions with boolean parameters                    | Use named options or separate methods  |
| God object               | Class doing too many things                          | Split by responsibility                |
| Shotgun surgery          | One change requires edits in many unrelated files    | Improve cohesion, reduce coupling      |
| Dead code                | Unreachable or commented-out code                    | Remove it; version control has history |

## PR Size Guidelines

Small PRs lead to better reviews. Follow these guidelines:

| PR Size (lines changed) | Classification | Review Quality |
|--------------------------|---------------|----------------|
| 1 -- 50                  | Excellent     | Thorough       |
| 51 -- 200                | Good          | Solid          |
| 201 -- 400               | Acceptable    | Declining      |
| 401 -- 800               | Too Large     | Superficial    |
| 800+                     | Unacceptable  | Rubber stamp   |

If a PR exceeds 400 lines:
- Ask the author to split it into smaller, independently reviewable PRs.
- If splitting is not possible, request a walkthrough before reviewing.
- Review in multiple passes, one concern at a time.

## Review Etiquette

### For Reviewers
- Review within 24 hours of being assigned. Delays compound.
- Start with the PR description and linked issue to understand intent before reading code.
- Comment on the code, not the person. Say "this function could be simplified" not "you wrote this wrong."
- Ask questions instead of making demands. "What happens if this is null?" is better than "Handle the null case."
- Acknowledge good work. A "nice approach" comment costs nothing and builds trust.
- Provide concrete suggestions. Include code snippets when proposing alternatives.
- Limit nitpicks. Prefix optional suggestions with "nit:" so the author can prioritize.

### For Authors
- Keep PRs small and focused on a single concern.
- Write a thorough PR description explaining what and why.
- Self-review before requesting review. Read every diff line.
- Respond to every comment, even if just "Done" or "Acknowledged."
- Do not take feedback personally. The goal is better code.

## Blocking vs Non-Blocking Feedback

Clearly distinguish feedback that must be addressed from suggestions:

**Blocking (must fix before merge):**
- Security vulnerabilities
- Data loss risks
- Broken functionality
- Missing tests for critical paths
- Violations of regulatory requirements

**Non-blocking (author's discretion):**
- Style preferences beyond the linter's scope
- Alternative approaches that are equally valid
- Naming suggestions
- Minor performance improvements with negligible impact
- Documentation improvements

Mark your comments explicitly:
- `[blocking]` -- Must be addressed before approval.
- `[suggestion]` -- Consider this, but it is not required.
- `[question]` -- I need clarification to continue the review.
- `[nit]` -- Trivial improvement, entirely optional.

## Auto-Review Triggers

Configure CI to automatically flag these patterns before human review:

```yaml
# Example auto-review checks
auto_review:
  - name: "Large PR warning"
    trigger: lines_changed > 400
    action: comment "This PR exceeds 400 lines. Consider splitting it."

  - name: "Missing tests"
    trigger: source_files_changed AND NOT test_files_changed
    action: comment "Source files changed without corresponding test changes."

  - name: "Dependency changes"
    trigger: lockfile_changed
    action: request_review from security_team

  - name: "Migration present"
    trigger: migration_files_added
    action: request_review from database_team

  - name: "Secrets detection"
    trigger: pattern_match "(API_KEY|SECRET|PASSWORD|TOKEN)\\s*=\\s*['\"]\\w+"
    action: block_merge "Possible hardcoded secret detected."

  - name: "Console statements"
    trigger: pattern_match "console\\.(log|debug|info)"
    action: comment "Remove console statements before merging."
```

## Review Workflow

```
1. Read the PR description and linked issue
2. Check CI status (tests, lint, build)
3. Review file-by-file, starting with tests to understand intent
4. Check the diff for each dimension in the checklist
5. Leave comments with clear blocking/non-blocking labels
6. Approve, request changes, or comment
7. Re-review after changes are made
8. Approve and merge
```
