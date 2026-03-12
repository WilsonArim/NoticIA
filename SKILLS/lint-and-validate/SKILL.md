---
name: Lint and Validate
description: Automatic code validation to catch errors before they reach review or production
phase: 0
always_active: true
---

# Lint and Validate

Code that has not been linted and validated is not ready to deliver. Automated checks
catch entire categories of bugs before a human ever needs to look at the code.

## Core Principle

Never rely on manual review to catch what a machine can catch automatically. Linting
and validation are the first line of defense, not an afterthought.

## Linting Rules

### What Linting Catches
- Syntax errors and typos in variable names.
- Unused variables and imports (dead code).
- Inconsistent formatting that hinders readability.
- Common anti-patterns and known bug sources.
- Accessibility violations in UI code.
- Security issues like eval() usage or prototype pollution.

### When to Lint
- After every file save (IDE integration).
- Before every commit (pre-commit hook).
- In CI on every pull request (enforcement gate).
- Linting is not optional. It is infrastructure.

## TypeScript Strict Mode

Always enable strict mode in TypeScript projects. The following compiler options should
be active in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### Why Strict Mode Matters
- `strict: true` enables all strict type checking options at once.
- `noUncheckedIndexedAccess` prevents assuming array/object access always returns a
  value. This alone catches a large class of runtime errors.
- `noImplicitReturns` ensures every code path in a function returns a value.
- These are not pedantic rules. Each one prevents a real category of production bugs.

### Dealing with Strict Mode in Legacy Code
- Enable strict mode incrementally using per-file `// @ts-strict` comments or by
  configuring `include` paths.
- Never weaken the tsconfig to accommodate new code. Fix the code instead.
- Use `// @ts-expect-error` with a comment explaining why, never `// @ts-ignore`.

## ESLint Configuration Recommendations

### Recommended Base Configs
- `@typescript-eslint/recommended` as the minimum for TypeScript projects.
- `eslint:recommended` as the baseline for JavaScript projects.
- `eslint-plugin-import` for import order and unused import detection.
- `eslint-config-prettier` to avoid conflicts between ESLint and Prettier.

### Key Rules to Enable
```javascript
{
  "rules": {
    "no-console": "warn",
    "no-debugger": "error",
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": ["error", {
      "argsIgnorePattern": "^_",
      "varsIgnorePattern": "^_"
    }],
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-non-null-assertion": "warn",
    "import/no-cycle": "error",
    "import/order": ["error", {
      "groups": ["builtin", "external", "internal", "parent", "sibling", "index"],
      "newlines-between": "always"
    }],
    "eqeqeq": ["error", "always"],
    "no-var": "error",
    "prefer-const": "error"
  }
}
```

### Rules to Avoid
- Do not enable stylistic rules that conflict with Prettier. Let Prettier handle
  formatting and ESLint handle logic.
- Do not disable rules project-wide to fix one file. Use inline overrides sparingly.

## Pre-Commit Hooks

Use `husky` and `lint-staged` to enforce validation before code enters the repository.

### Recommended Setup
```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix --max-warnings=0",
      "prettier --write"
    ],
    "*.{json,md,yml,yaml}": [
      "prettier --write"
    ]
  }
}
```

### What Pre-Commit Hooks Should Run
1. Linting with auto-fix on staged files.
2. Formatting with Prettier on staged files.
3. Type checking (`tsc --noEmit`) on the full project.
4. Unit tests related to changed files (optional but recommended).

### What Pre-Commit Hooks Should NOT Run
- Full test suite (too slow -- save for CI).
- Build steps (too slow -- save for CI).
- Anything that takes more than 10 seconds.

## Validation Checklist Before Delivering Code

Run through this checklist before marking any task as complete:

### Automated Checks
- [ ] `tsc --noEmit` passes with zero errors.
- [ ] `eslint .` passes with zero errors and zero warnings.
- [ ] `prettier --check .` reports no formatting issues.
- [ ] All existing tests pass.
- [ ] New code has corresponding test coverage.

### Manual Checks
- [ ] No `console.log` statements left in production code.
- [ ] No `any` types introduced without justification.
- [ ] No `// @ts-ignore` or `// @ts-expect-error` without explanatory comments.
- [ ] No hardcoded secrets, URLs, or environment-specific values.
- [ ] No TODO comments without a linked issue or ticket number.
- [ ] Error handling is present for all async operations.
- [ ] Function and variable names are descriptive and consistent.

## Rules

1. NEVER deliver code that does not pass linting and type checking.
2. ALWAYS run `tsc --noEmit` before considering TypeScript code complete.
3. NEVER disable a lint rule project-wide to fix a local issue.
4. ALWAYS use `--max-warnings=0` in CI to prevent warning accumulation.
5. TREAT warnings as errors in CI. Warnings in CI are just errors you have not fixed yet.
6. FIX lint errors by improving code, not by adding disable comments.
7. CONFIGURE pre-commit hooks in every project from day one.
8. KEEP lint configuration in version control. It is project infrastructure, not
   personal preference.
9. UPDATE lint rules when the team agrees on new standards. Do not let the config
   become stale.
10. RUN the full validation checklist before every pull request.
