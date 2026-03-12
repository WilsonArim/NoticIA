---
name: Test-Driven Development
description: Write failing tests first, then make them pass, then refactor
phase: 5
---

# Test-Driven Development (TDD)

## The TDD Cycle: Red, Green, Refactor

TDD follows a strict three-step cycle that must be respected in order:

1. **RED** -- Write a failing test that describes the desired behavior. The test must fail for the right reason. Do not write implementation code before the test exists.
2. **GREEN** -- Write the minimum amount of production code necessary to make the failing test pass. Do not optimize. Do not handle edge cases not yet covered by tests. Just make it green.
3. **REFACTOR** -- Clean up both the test and the production code. Remove duplication, improve naming, extract functions. All tests must remain green after refactoring.

Each cycle should take between 1 and 10 minutes. If a cycle takes longer, the step is too large -- break it down.

## When to Use TDD

TDD is highly effective for:
- Business logic and domain rules
- Data transformations and parsing
- Utility functions and helpers
- API endpoint handlers
- State machines and workflows
- Bug fixes (write a test that reproduces the bug first)

TDD may not be the best fit for:
- Exploratory prototyping (spike and stabilize instead)
- UI layout and styling (use visual regression tests)
- Third-party integration wrappers (use integration tests post-hoc)
- One-off scripts with no maintenance expectation

## The Testing Pyramid

Structure your test suite following the pyramid model, from most to fewest tests:

```
        /  E2E  \          ~5%   -- Slow, expensive, high confidence
       /----------\
      / Integration \      ~15%  -- Medium speed, cross-boundary
     /----------------\
    /    Unit Tests     \  ~80%  -- Fast, isolated, focused
   /---------------------\
```

- **Unit tests**: Test a single function or class in isolation. Mock external dependencies. Execute in milliseconds.
- **Integration tests**: Test interactions between modules, database queries, API routes. May use real databases or test containers.
- **End-to-end tests**: Test complete user flows through the running application. Use sparingly for critical paths only.

## Test Types and Their Purpose

| Type        | Scope                  | Speed    | Dependencies     |
|-------------|------------------------|----------|------------------|
| Unit        | Single function/class  | < 10ms   | All mocked       |
| Integration | Module boundaries      | < 1s     | Some real         |
| E2E         | Full user flow         | < 30s    | All real          |
| Contract    | API boundaries         | < 100ms  | Schema-based      |
| Snapshot    | UI component output    | < 50ms   | Renderer          |

## Naming Convention for Tests

Use descriptive names that read as specifications. Follow this pattern:

```
[unit under test] [scenario] [expected behavior]
```

Examples:
```typescript
// Good -- reads as a specification
describe('calculateDiscount', () => {
  it('returns 0 when the cart total is below the minimum threshold', () => {});
  it('applies 10% discount when the user is a premium member', () => {});
  it('throws InvalidCouponError when the coupon code has expired', () => {});
});

// Bad -- vague and uninformative
describe('calculateDiscount', () => {
  it('works correctly', () => {});
  it('handles edge case', () => {});
});
```

## The AAA Pattern: Arrange, Act, Assert

Every test should follow three distinct phases, separated by blank lines:

```typescript
it('returns the total price with tax applied', () => {
  // Arrange -- set up the test data and dependencies
  const cart = createCart([
    { name: 'Widget', price: 100, quantity: 2 },
  ]);
  const taxRate = 0.08;

  // Act -- execute the behavior under test
  const result = calculateTotal(cart, taxRate);

  // Assert -- verify the outcome
  expect(result).toBe(216);
});
```

Rules:
- One Act per test. If you need multiple acts, write multiple tests.
- Arrange can be extracted into `beforeEach` only when shared across all tests in a `describe` block.
- Assert should verify one logical concept (multiple `expect` calls are acceptable if they verify the same concept).

## Mocking Strategy

Follow this hierarchy when dealing with dependencies:

1. **Prefer real implementations** when they are fast and deterministic.
2. **Use fakes** (in-memory databases, test doubles) for complex dependencies.
3. **Use stubs** to provide canned responses for external services.
4. **Use mocks** only when you need to verify that a specific interaction occurred.
5. **Use spies** to observe calls without changing behavior.

Guidelines:
- Never mock what you do not own. Wrap third-party libraries in your own interface and mock that.
- Mock at the boundary, not deep inside the module.
- If a test requires more than 3 mocks, the production code likely has too many dependencies -- refactor it.

## Coverage Targets

Coverage is a metric, not a goal. Use it as a safety net, not a badge.

| Metric            | Target  | Notes                                    |
|-------------------|---------|------------------------------------------|
| Line coverage     | > 80%   | Baseline for most projects               |
| Branch coverage   | > 75%   | Catches untested conditional paths       |
| Critical paths    | 100%    | Payment, auth, data mutation             |
| New code          | > 90%   | Enforce on pull requests via CI          |

Do not chase 100% total coverage. Focus coverage effort on:
- Code with high cyclomatic complexity
- Code that handles money, authentication, or user data
- Code that has historically produced bugs

## TDD Anti-Patterns to Avoid

- **The Liar**: Tests that pass but do not actually verify correct behavior.
- **The Giant**: Tests with hundreds of lines that test too many things at once.
- **The Mockery**: Tests that mock so much they only test the mocking framework.
- **The Inspector**: Tests that are tightly coupled to implementation details and break on every refactor.
- **The Slow Poke**: Tests that hit real networks or sleep for fixed durations.

## Practical TDD Workflow

```
1. Pick the next behavior to implement
2. Write the simplest failing test for that behavior
3. Run the test -- confirm it fails (RED)
4. Write the simplest code to pass the test
5. Run all tests -- confirm they pass (GREEN)
6. Refactor production and test code
7. Run all tests -- confirm they still pass (REFACTOR)
8. Commit
9. Repeat
```

Commit after every successful Red-Green-Refactor cycle to maintain a clean, revertible history.
