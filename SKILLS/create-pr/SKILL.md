---
name: Create Pull Request
description: Pull requests with review-ready context, templates, and best practices
phase: 6
---

# Create Pull Request

## PR Template

Every pull request should include the following sections. Save this as `.github/PULL_REQUEST_TEMPLATE.md` in your repository.

```markdown
## Summary

Brief description of what this PR does and why.

## Changes

- Bullet list of specific changes made.
- Focus on what a reviewer needs to understand.

## Test Plan

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed (describe steps)
- [ ] Edge cases considered

## Screenshots

If this PR includes UI changes, attach before/after screenshots or screen recordings.

## Related Issues

Closes #ISSUE_NUMBER
```

## PR Size Guidelines

Keep pull requests small and focused. The ideal PR is under 400 lines of meaningful changes.

| Size         | Lines Changed | Review Time | Risk    |
|--------------|---------------|-------------|---------|
| Small        | < 100         | 15 min      | Low     |
| Medium       | 100-400       | 30-60 min   | Medium  |
| Large        | 400-800       | 1-2 hours   | High    |
| Too Large    | > 800         | Unreliable  | Very High |

### Why Small PRs Matter

- Faster review turnaround (reviewers are more willing to start).
- Higher quality feedback (reviewers catch more issues in smaller diffs).
- Easier to revert if something breaks.
- Reduces merge conflict likelihood.

### Strategies for Keeping PRs Small

1. **Split by layer:** One PR for the database migration, another for the API, another for the UI.
2. **Split by behavior:** One PR for the happy path, another for error handling.
3. **Extract refactors:** If a feature requires refactoring existing code, submit the refactor as a separate PR first.
4. **Use feature flags:** Merge incomplete features behind a flag so partial work can land safely.

## Draft PRs

Use draft PRs for work-in-progress that needs early feedback.

```bash
gh pr create --draft --title "feat(auth): add OAuth2 flow" --body "WIP: Looking for feedback on the token refresh approach."
```

When to use drafts:
- You want to share an approach for discussion before it is complete.
- CI needs to run to validate an architectural decision.
- You are pairing asynchronously and need the other developer to see progress.

Convert to ready-for-review only when all checks pass and the self-review checklist is complete.

## Linking Issues

Always link the PR to the issue it addresses. This enables automatic issue closure on merge.

In the PR body:
```
Closes #142
Fixes #287
Resolves #301
```

For multiple issues:
```
Closes #142, closes #143
```

When the PR is related but does not fully resolve an issue:
```
Related to #142
```

## Reviewer Assignment

- Assign 1-2 reviewers who are familiar with the affected area of the codebase.
- Use GitHub CODEOWNERS to auto-assign reviewers based on file paths.
- Rotate reviewers to spread knowledge across the team.
- Do not assign more than 3 reviewers; it dilutes responsibility.

### CODEOWNERS Example

```
# .github/CODEOWNERS
/src/auth/       @team/backend
/src/components/ @team/frontend
/infra/          @team/devops
*.sql            @team/backend @team/dba
```

## PR Title Conventions

Follow the same format as conventional commits:

```
type(scope): concise description
```

Examples:
```
feat(auth): add Google OAuth2 login
fix(cart): resolve race condition on quantity update
refactor(api): extract middleware into shared module
docs(readme): update local development setup instructions
chore(deps): bump express from 4.18.2 to 4.19.0
```

Rules:
- Use imperative mood ("add" not "added" or "adding").
- Keep under 72 characters.
- Do not end with a period.
- The title should make sense in a changelog context.

## Self-Review Checklist

Before requesting review, go through this checklist:

### Code Quality
- [ ] I have read through the entire diff myself.
- [ ] No commented-out code or debug statements remain.
- [ ] No `TODO` comments without a linked issue.
- [ ] Variable and function names are clear and descriptive.
- [ ] No duplicated logic that should be extracted.

### Testing
- [ ] New code is covered by tests.
- [ ] Existing tests still pass.
- [ ] Edge cases are tested (empty inputs, large data, error conditions).
- [ ] No flaky tests introduced.

### Security
- [ ] No secrets, tokens, or credentials in the diff.
- [ ] User input is validated and sanitized.
- [ ] Authorization checks are in place for new endpoints.

### Documentation
- [ ] Public APIs have JSDoc or equivalent documentation.
- [ ] README is updated if setup steps changed.
- [ ] Breaking changes are called out in the PR description.

### CI/CD
- [ ] All CI checks pass (lint, typecheck, test, build).
- [ ] No new warnings introduced.

## Responding to Review Feedback

- Respond to every comment, even if just with "Done" or "Acknowledged."
- If you disagree, explain your reasoning respectfully; do not just dismiss.
- Push fixes as new commits during review (do not force-push) so reviewers can see incremental changes.
- After all feedback is addressed, leave a summary comment: "All feedback addressed, ready for re-review."
- Squash commits on merge, not during review.

## Quick Reference

| Concern          | Recommendation                                     |
|------------------|----------------------------------------------------|
| PR size          | Under 400 lines of meaningful changes              |
| Template         | Summary, Changes, Test Plan, Screenshots, Issues   |
| Title format     | `type(scope): description` (conventional commits)  |
| Draft PRs        | Use for WIP and early feedback                     |
| Reviewers        | 1-2 assigned, use CODEOWNERS for auto-assignment   |
| Self-review      | Complete checklist before requesting review         |
| Issue linking    | `Closes #N` for automatic closure on merge         |
