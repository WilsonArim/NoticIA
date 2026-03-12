---
name: E2E Testing Patterns
description: Reliable end-to-end test suites using Playwright with page object model, test isolation, and CI integration
phase: 5
---

# E2E Testing Patterns

## Playwright Setup and Best Practices

### Installation and Configuration

```bash
npm init playwright@latest
```

Configure `playwright.config.ts` with sensible defaults:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'html',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Best Practices

- Run tests in parallel by default. Design tests to be independent.
- Use `test.describe` to group related tests logically.
- Enable traces on first retry to debug failures without guessing.
- Keep timeouts reasonable. If a test needs more than 30 seconds, the feature is too slow.
- Never use `page.waitForTimeout()` (hard waits). Use assertions or locator auto-waiting instead.

## Test Structure: Page Object Model

Encapsulate page interactions in page objects to keep tests clean and maintainable.

```typescript
// e2e/pages/login.page.ts
import { type Page, type Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByTestId('login-email');
    this.passwordInput = page.getByTestId('login-password');
    this.submitButton = page.getByTestId('login-submit');
    this.errorMessage = page.getByTestId('login-error');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}
```

```typescript
// e2e/tests/login.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

test.describe('Login', () => {
  test('redirects to dashboard after successful login', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('user@example.com', 'password123');
    await expect(page).toHaveURL('/dashboard');
  });

  test('shows error for invalid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('user@example.com', 'wrongpassword');
    await expect(loginPage.errorMessage).toBeVisible();
    await expect(loginPage.errorMessage).toContainText('Invalid credentials');
  });
});
```

Rules for page objects:
- One page object per page or significant component.
- Page objects encapsulate locators and actions but never assertions.
- Assertions belong in the test files, not in page objects.
- Page objects return data or other page objects for chaining.

## Selectors Strategy

Use `data-testid` attributes as the primary selector strategy. This decouples tests from CSS structure and visible text.

### Priority order for selectors

1. **`data-testid`** -- Most stable. Not affected by styling or text changes.
2. **`getByRole`** -- Accessible selectors like `getByRole('button', { name: 'Submit' })`.
3. **`getByText`** -- For verifying visible content, not for primary interaction selectors.
4. **`getByLabel`** -- For form inputs associated with labels.
5. **Never use**: CSS selectors, XPath, class names, or element IDs (fragile, change often).

```tsx
// In your component
<button data-testid="checkout-submit">Complete Purchase</button>

// In your test
await page.getByTestId('checkout-submit').click();
```

Add a linting rule or convention to ensure `data-testid` attributes are present on all interactive elements.

## Test Isolation

Every test must be independent. No test should depend on another test's state.

### Strategies for isolation

- **Database seeding**: Reset or seed the database before each test or test suite. Use API calls or direct database access in `beforeEach`.
- **Authentication**: Use Playwright's `storageState` to save and reuse authentication state without logging in through the UI in every test.
- **Unique data**: Generate unique test data per test run to avoid collisions (e.g., `user+${Date.now()}@test.com`).
- **Cleanup**: Clean up created resources in `afterEach` if they could affect other tests.

```typescript
// Save auth state once, reuse across tests
// e2e/auth.setup.ts
import { test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByTestId('login-email').fill('admin@test.com');
  await page.getByTestId('login-password').fill('password');
  await page.getByTestId('login-submit').click();
  await page.waitForURL('/dashboard');
  await page.context().storageState({ path: '.auth/admin.json' });
});

// Use in tests
test.use({ storageState: '.auth/admin.json' });
```

## Handling Async Operations

Playwright has built-in auto-waiting, but some scenarios need explicit handling.

```typescript
// Wait for navigation after an action
await Promise.all([
  page.waitForURL('/dashboard'),
  page.getByTestId('login-submit').click(),
]);

// Wait for a network request to complete
const responsePromise = page.waitForResponse(
  (resp) => resp.url().includes('/api/users') && resp.status() === 200
);
await page.getByTestId('save-button').click();
await responsePromise;

// Wait for an element to appear after async loading
await expect(page.getByTestId('results-list')).toBeVisible({ timeout: 10_000 });

// Avoid this -- never use hard waits
// await page.waitForTimeout(3000);  // BAD
```

## CI Integration

### GitHub Actions example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

CI guidelines:
- Run with `workers: 1` in CI to avoid resource contention on shared runners.
- Set `retries: 2` in CI to tolerate transient infrastructure issues.
- Upload test reports and traces as artifacts on failure.
- Run E2E tests after unit and integration tests pass (fail fast).
- Consider running E2E only on PRs to main, not on every push.

## Visual Regression Testing

Use Playwright's built-in screenshot comparison to catch unintended visual changes.

```typescript
test('homepage matches snapshot', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png', {
    maxDiffPixelRatio: 0.01,
    fullPage: true,
  });
});

test('button states match snapshots', async ({ page }) => {
  await page.goto('/components');
  const button = page.getByTestId('primary-button');
  await expect(button).toHaveScreenshot('button-default.png');
  await button.hover();
  await expect(button).toHaveScreenshot('button-hover.png');
});
```

Guidelines:
- Generate baseline screenshots on a consistent environment (CI, not local machines).
- Use `maxDiffPixelRatio` instead of `maxDiffPixels` for responsive tolerance.
- Store screenshots in version control so changes are visible in PRs.
- Update snapshots deliberately: `npx playwright test --update-snapshots`.

## Flaky Test Prevention

Flaky tests destroy confidence in the test suite. Prevent them systematically.

### Common causes and fixes

| Cause                        | Fix                                                  |
|------------------------------|------------------------------------------------------|
| Hard-coded waits             | Use Playwright auto-waiting and `expect` assertions  |
| Shared test state            | Isolate each test with fresh data and auth state     |
| Timing-dependent assertions  | Use `toBeVisible()`, `toHaveText()` with retries     |
| Animations interfering       | Disable animations in test mode via CSS or config    |
| External service dependency  | Mock external APIs with `page.route()`               |
| Non-deterministic data       | Use seeded, predictable test data                    |
| Race conditions in UI        | Wait for specific network responses before asserting |

### Disabling animations in tests

```typescript
// In playwright.config.ts or test setup
test.use({
  // Reduce motion for all tests
  contextOptions: {
    reducedMotion: 'reduce',
  },
});
```

### Mocking external APIs

```typescript
test('displays user profile from API', async ({ page }) => {
  await page.route('**/api/user/profile', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ name: 'Test User', email: 'test@example.com' }),
    })
  );

  await page.goto('/profile');
  await expect(page.getByTestId('user-name')).toHaveText('Test User');
});
```

### Monitoring flakiness

- Track flaky test frequency in CI dashboards.
- Quarantine consistently flaky tests: move them to a separate suite and fix within one sprint.
- Never ignore or skip flaky tests permanently. Fix the root cause or delete the test.
- Run `npx playwright test --repeat-each=5` locally to detect flakiness before merging.
