---
name: Git Pushing
description: Safe commits, clean history, and disciplined git practices
phase: 0
always_active: true
---

# Git Pushing

Git is not just version control. It is a communication tool. Every commit tells a
story. A clean git history makes debugging, reviewing, and collaborating dramatically
easier.

## Core Principle

Every commit should be atomic, well-described, and safe. Never push code that breaks
the build, and never write a commit message that future-you will not understand.

## Conventional Commits Format

Follow the Conventional Commits specification for all commit messages.

### Structure
```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types
- `feat`: A new feature visible to the user.
- `fix`: A bug fix.
- `docs`: Documentation changes only.
- `style`: Formatting, whitespace, semicolons. No logic change.
- `refactor`: Code restructuring without changing external behavior.
- `perf`: Performance improvement.
- `test`: Adding or updating tests.
- `chore`: Build process, dependencies, tooling.
- `ci`: CI/CD configuration changes.

### Examples
```
feat(auth): add JWT token refresh endpoint
fix(api): return 404 instead of 500 for missing resources
refactor(db): extract query builder into shared utility
test(payments): add integration tests for Stripe webhook
chore(deps): upgrade Next.js to 14.1.0
```

### Rules for Subjects
- Use imperative mood: "add feature" not "added feature" or "adds feature".
- Do not capitalize the first letter.
- Do not end with a period.
- Keep under 72 characters.
- Describe WHAT changed, not HOW.

### When to Use the Body
- The change is not self-explanatory from the subject line alone.
- You need to explain WHY you made this choice over alternatives.
- There are breaking changes that consumers need to know about.

```
fix(auth): handle expired refresh tokens gracefully

Previously, an expired refresh token caused an unhandled exception that
returned a 500 error. Now the auth middleware explicitly checks token
expiry and returns a 401 with a clear error message, prompting the
client to re-authenticate.

BREAKING CHANGE: /api/refresh now returns 401 instead of 500 for
expired tokens. Clients should handle this status code.
```

## Atomic Commits

Each commit should represent exactly one logical change. This is non-negotiable.

### What Atomic Means
- A commit compiles and passes tests on its own.
- A commit can be reverted without breaking unrelated functionality.
- A commit does not mix feature work with formatting or refactoring.

### How to Achieve Atomic Commits
- Use `git add -p` to stage specific hunks, not entire files.
- Separate refactoring into its own commit BEFORE the feature commit.
- If a fix requires a migration and code change, consider two commits:
  one for the migration, one for the code.

### Anti-Patterns
- A single commit with the message "WIP" or "misc changes" or "stuff".
- A commit that adds a feature AND fixes a bug AND reformats three files.
- A commit that breaks the build, with a follow-up "fix build" commit.

## Branch Naming

Use a consistent naming convention for branches.

### Format
```
<type>/<ticket-id>-<short-description>
```

### Examples
```
feat/AUTH-123-token-refresh
fix/API-456-null-pointer-users
chore/INFRA-789-upgrade-node
```

### Rules
- Use lowercase and hyphens only. No spaces, underscores, or camelCase.
- Include the ticket/issue ID when one exists.
- Keep the description to 3-5 words maximum.
- Delete branches after merging. Stale branches are noise.

## When to Commit

### Commit Frequently
- After completing each logical step in your plan.
- After making a test pass.
- After a successful refactoring step.
- Before switching context to a different task.
- When you reach a stable state you might want to return to.

### Do NOT Commit
- Code that does not compile or pass type checking.
- Halfway through a refactoring that leaves the code in a broken state.
- Debug logging or temporary test code.
- Secrets, credentials, or environment-specific configuration.
- Generated files that should be in .gitignore.

## Pre-Push Checklist

Before running `git push`, verify all of the following:

### Automated
- [ ] `tsc --noEmit` passes (no type errors).
- [ ] `eslint .` passes (no lint errors).
- [ ] All tests pass locally.
- [ ] No merge conflicts with the target branch.

### Manual
- [ ] Review your own diff: `git diff --staged` or `git log --oneline -5`.
- [ ] No files included that should not be (check `git status`).
- [ ] No secrets or credentials in the diff.
- [ ] Commit messages follow conventional format.
- [ ] Branch is up to date with the base branch.

## Git Safety Rules

These rules exist to prevent data loss and repository corruption.

1. NEVER force push to main, master, or any shared branch.
2. NEVER rewrite history on branches that others are working on.
3. ALWAYS pull before pushing to shared branches.
4. NEVER commit directly to main/master. Use feature branches.
5. ALWAYS use `git push --force-with-lease` instead of `git push --force` when
   force pushing is truly necessary on your own branch.
6. NEVER store secrets in git. Not even for "just a second". The git history is
   permanent. Use environment variables or secret managers.
7. KEEP `.gitignore` up to date. Review it when adding new tools or frameworks.
8. ALWAYS verify what you are pushing with `git log origin/main..HEAD` before pushing.
9. USE signed commits when working on security-sensitive projects.
10. BACK UP important branches before destructive operations like rebase or reset.

## Recovery Patterns

### Undo the Last Commit (keep changes)
```
git reset --soft HEAD~1
```

### Undo Changes to a Specific File
```
git checkout -- path/to/file
```

### Find a Lost Commit
```
git reflog
```

### Emergency: Pushed Secrets
1. Immediately rotate the exposed credential.
2. Remove from code and commit the removal.
3. Use `git filter-branch` or `bfg-repo-cleaner` to remove from history.
4. Force push the cleaned history.
5. Notify the team.
