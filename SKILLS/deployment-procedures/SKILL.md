---
name: Deployment Procedures
description: Safe rollout strategies, CI/CD pipelines, and rollback procedures
phase: 6
---

# Deployment Procedures

## Deployment Checklist

Before every deployment, verify:

- [ ] All tests pass (unit, integration, e2e).
- [ ] Build succeeds with no warnings treated as errors.
- [ ] Database migrations are backward-compatible.
- [ ] Environment variables are configured for the target environment.
- [ ] Feature flags are set correctly for the release.
- [ ] Rollback plan is documented and tested.
- [ ] Monitoring dashboards and alerts are active.
- [ ] Changelog and release notes are prepared.
- [ ] Team has been notified of the deployment window.

## Deployment Strategies

### Blue-Green Deployment

Maintain two identical production environments (blue and green). At any time, one is live and the other is idle.

1. Deploy the new version to the idle environment.
2. Run smoke tests against the idle environment.
3. Switch the load balancer to point traffic to the newly deployed environment.
4. If issues are detected, switch back immediately (instant rollback).
5. The previously live environment becomes the next deployment target.

**Pros:** Zero-downtime, instant rollback.
**Cons:** Requires double infrastructure, database migrations must be backward-compatible.

### Canary Releases

Route a small percentage of traffic to the new version before rolling it out fully.

1. Deploy the new version alongside the current version.
2. Route 5% of traffic to the canary.
3. Monitor error rates, latency, and business metrics.
4. Gradually increase traffic (5% -> 25% -> 50% -> 100%).
5. If metrics degrade, route all traffic back to the stable version.

**Pros:** Limits blast radius, data-driven rollout decisions.
**Cons:** More complex routing infrastructure, requires good observability.

### Rolling Updates

Replace instances of the old version one at a time.

1. Take one instance out of the load balancer.
2. Deploy the new version to that instance.
3. Run health checks; if healthy, add it back to the pool.
4. Repeat for each instance.

**Pros:** Simple, no extra infrastructure.
**Cons:** Mixed versions running simultaneously, slower rollback.

## Rollback Procedures

### Automated Rollback Triggers

Define automatic rollback conditions:

- Error rate exceeds 5% for 2 consecutive minutes.
- p95 latency exceeds 2x the baseline for 3 minutes.
- Health check failures on more than 30% of instances.

### Manual Rollback Steps

1. Identify the last known good version (check deployment history).
2. Trigger redeployment of that version.
3. Verify health checks pass on the rolled-back version.
4. Investigate the root cause of the failed deployment.
5. Document the incident in the post-mortem.

### Database Rollback

- Always write forward-compatible migrations. Never drop columns in the same release that removes the code using them.
- Use a two-phase approach: Phase 1 deploys code that no longer uses the column. Phase 2 (next release) drops the column.
- Keep migration rollback scripts tested and ready.

## CI/CD Pipeline Design (GitHub Actions)

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Staging
        run: ./scripts/deploy.sh staging
      - name: Run Smoke Tests
        run: npm run test:smoke -- --env=staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://app.example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Production
        run: ./scripts/deploy.sh production
      - name: Run Smoke Tests
        run: npm run test:smoke -- --env=production
      - name: Notify Team
        if: success()
        run: ./scripts/notify-deploy.sh success
      - name: Rollback on Failure
        if: failure()
        run: ./scripts/rollback.sh production
```

## Environment Promotion

Follow a strict promotion path: **dev -> staging -> production**.

| Environment | Purpose                            | Data              |
|-------------|------------------------------------|--------------------|
| dev         | Active development, fast iteration | Seed/synthetic     |
| staging     | Pre-production validation          | Anonymized copy    |
| production  | Live user traffic                  | Real user data     |

Rules:
- Never deploy directly to production without passing through staging.
- Staging should mirror production configuration as closely as possible.
- Use the same Docker image across all environments; only environment variables change.
- Database migrations must be tested in staging before production.

## Feature Flags

Use feature flags to decouple deployment from release.

```typescript
// Simple feature flag check
if (featureFlags.isEnabled('new-checkout-flow', { userId: user.id })) {
  return renderNewCheckout();
}
return renderLegacyCheckout();
```

Best practices:
- Use a feature flag service (LaunchDarkly, Unleash, or Supabase edge config).
- Clean up flags after full rollout; do not let stale flags accumulate.
- Log flag evaluations for debugging.
- Use percentage-based rollouts for gradual releases.

## Monitoring Post-Deploy

After every deployment, monitor for at least 30 minutes:

- **Error rate:** Compare against the pre-deploy baseline.
- **Latency:** Check p50, p95, and p99 response times.
- **Resource usage:** CPU, memory, and disk on all services.
- **Business metrics:** Conversion rates, signups, or other KPIs.
- **Logs:** Watch for new error patterns or warnings.

Set up alerts that trigger within 5 minutes if any metric degrades beyond acceptable thresholds.

## Quick Reference

| Concern            | Recommendation                                   |
|--------------------|--------------------------------------------------|
| Strategy           | Blue-green for critical, canary for gradual       |
| Rollback           | Automated triggers + manual procedure documented  |
| Pipeline           | test -> deploy staging -> deploy production       |
| Feature flags      | Decouple deploy from release                      |
| Monitoring         | 30-minute active watch post-deploy                |
| Database           | Forward-compatible migrations only                |
