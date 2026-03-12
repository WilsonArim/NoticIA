---
name: Conventional Commits
description: Structured commit messages following the Conventional Commits specification
phase: 6
---

# Conventional Commits

## Format

Every commit message must follow this structure:

```
type(scope): description

[optional body]

[optional footer(s)]
```

- **type**: The category of change (required).
- **scope**: The area of the codebase affected (optional but recommended).
- **description**: A concise summary of the change in imperative mood (required).
- **body**: Additional context, motivation, or implementation details (optional).
- **footer**: References to issues, breaking change notes (optional).

## Commit Types

| Type       | When to Use                                              |
|------------|----------------------------------------------------------|
| `feat`     | A new feature visible to the user                        |
| `fix`      | A bug fix                                                |
| `chore`    | Maintenance tasks that do not affect src or tests        |
| `docs`     | Documentation-only changes                               |
| `style`    | Formatting, whitespace, semicolons (no logic change)     |
| `refactor` | Code restructuring without changing external behavior    |
| `test`     | Adding or updating tests                                 |
| `perf`     | Performance improvements                                 |
| `ci`       | CI/CD configuration changes                              |
| `build`    | Build system or dependency changes                       |

## Scope Guidelines

The scope narrows down which part of the codebase is affected. Use consistent, project-specific scopes.

Common scope patterns:
- **By module:** `auth`, `api`, `ui`, `db`, `config`
- **By feature:** `checkout`, `profile`, `search`, `notifications`
- **By layer:** `controller`, `service`, `repository`, `middleware`

Rules:
- Keep scopes lowercase.
- Use a single word or hyphenated compound: `user-auth`, not `user authentication`.
- Define an allowed list in your project and enforce it with commitlint.
- Omit the scope only when the change is truly cross-cutting.

## Breaking Changes

Indicate breaking changes in two ways:

### Exclamation Mark in Header

```
feat(api)!: change authentication endpoint response format
```

### BREAKING CHANGE Footer

```
feat(api): change authentication endpoint response format

BREAKING CHANGE: The /auth/login endpoint now returns { token, user }
instead of { accessToken, refreshToken }. All clients must update their
response parsing logic.
```

Both methods cause a major version bump under semantic versioning.

## Commit Message Examples

### Good Examples

```
feat(auth): add password reset via email

Implement the forgot-password flow with a time-limited token
sent to the user's registered email address.

Closes #142
```

```
fix(cart): prevent duplicate items when clicking add rapidly

Added a debounce guard on the add-to-cart handler to prevent
race conditions that resulted in duplicate line items.

Fixes #287
```

```
refactor(db): extract query builder into shared utility

Moved duplicated query construction logic from three service
files into a single reusable QueryBuilder class.
```

```
chore: upgrade eslint to v9 and migrate flat config
```

```
perf(search): add database index on products.name column

Reduced search query time from 800ms to 45ms for the product
listing page.
```

```
ci: add Node.js 22 to the test matrix
```

### Bad Examples

```
# Too vague
fix: fix bug

# Past tense instead of imperative
feat(auth): added login feature

# No type
update user profile page

# Scope too broad
fix(everything): resolve issues

# Multiple unrelated changes in one commit
feat(auth,cart,search): add login, fix cart, update search
```

## Atomic Commit Principle

Each commit should represent exactly one logical change. This means:

- **One purpose per commit.** Do not mix a feature addition with a formatting fix.
- **Compilable and testable.** Every commit should leave the codebase in a working state.
- **Revertable.** If this commit needs to be reverted, only one logical change is undone.
- **Reviewable.** A reviewer can understand the purpose by reading the commit message alone.

### How to Achieve Atomic Commits

1. Use `git add -p` to stage only the hunks related to one change.
2. If you realize mid-work that you have two changes, stash one and commit the other first.
3. Plan your work in small increments: write one test, make it pass, commit.
4. If a refactor is needed to implement a feature, commit the refactor first, then the feature.

### Splitting a Large Change

Instead of one monolithic commit:

```
feat(checkout): complete checkout redesign with new payment flow
```

Break it into a sequence:

```
refactor(checkout): extract payment form into dedicated component
feat(checkout): add credit card validation with Luhn algorithm
feat(checkout): integrate Stripe payment intent API
test(checkout): add e2e tests for complete checkout flow
style(checkout): align spacing and typography to design spec
```

## Enforcing Conventional Commits

### commitlint Configuration

```javascript
// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'scope-enum': [2, 'always', ['auth', 'api', 'ui', 'db', 'config', 'ci']],
    'subject-case': [2, 'always', 'lower-case'],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [2, 'always', 100],
  },
};
```

### Husky Git Hook

```json
// package.json
{
  "husky": {
    "hooks": {
      "commit-msg": "commitlint --edit $1"
    }
  }
}
```

## Quick Reference

| Element         | Rule                                            |
|-----------------|-------------------------------------------------|
| Type            | Required, from the defined list                 |
| Scope           | Recommended, lowercase, single-word or hyphenated |
| Description     | Imperative mood, lowercase start, no period     |
| Body            | Optional, explain why not what                  |
| Footer          | Reference issues, note breaking changes         |
| Atomic          | One logical change per commit                   |
| Enforcement     | commitlint + husky in CI and locally            |
