---
name: Security Auditor
description: Comprehensive security audit covering OWASP Top 10, dependency analysis, and vulnerability detection
phase: 5
---

# Security Auditor

## OWASP Top 10 Checklist (2021)

Audit every application against these categories. For each, verify the controls are in place and document findings.

### A01: Broken Access Control
- [ ] Enforce deny-by-default for all protected resources.
- [ ] Verify that users cannot act outside their intended permissions.
- [ ] Ensure CORS configuration is restrictive and intentional.
- [ ] Disable directory listing on the web server.
- [ ] Verify that API endpoints enforce authorization, not just authentication.
- [ ] Check that JWT tokens are validated on every request (signature, expiration, issuer).

### A02: Cryptographic Failures
- [ ] All data in transit uses TLS 1.2 or higher.
- [ ] Passwords are hashed with bcrypt, scrypt, or Argon2 (never MD5 or SHA-1).
- [ ] Sensitive data at rest is encrypted (PII, payment data, health records).
- [ ] Encryption keys are stored in a key management service, not in code.
- [ ] Deprecated cryptographic algorithms are not in use.

### A03: Injection
- [ ] All database queries use parameterized statements or an ORM.
- [ ] User input is never interpolated into SQL, LDAP, or OS commands.
- [ ] Template engines use auto-escaping by default.
- [ ] Input validation uses allowlists, not denylists.

### A04: Insecure Design
- [ ] Threat modeling has been performed for critical features.
- [ ] Rate limiting is applied to authentication and sensitive endpoints.
- [ ] Business logic abuse scenarios have been considered and mitigated.

### A05: Security Misconfiguration
- [ ] Default credentials are changed or disabled.
- [ ] Error messages do not leak stack traces or internal details to users.
- [ ] Unnecessary features, ports, and services are disabled.
- [ ] Security headers are configured (see Security Headers section below).

### A06: Vulnerable and Outdated Components
- [ ] Run `npm audit` (or equivalent) and address critical/high findings.
- [ ] Dependencies are pinned to specific versions in lockfiles.
- [ ] A process exists for monitoring and updating vulnerable dependencies.

### A07: Identification and Authentication Failures
- [ ] Multi-factor authentication is available for sensitive accounts.
- [ ] Session tokens are invalidated on logout.
- [ ] Password policies enforce minimum length (12+ characters).
- [ ] Account lockout or progressive delays exist after failed attempts.
- [ ] Session IDs are rotated after login.

### A08: Software and Data Integrity Failures
- [ ] CI/CD pipelines are secured against unauthorized modifications.
- [ ] Dependencies are verified using integrity checks (lockfile hashes).
- [ ] Auto-update mechanisms verify signatures before applying updates.

### A09: Security Logging and Monitoring Failures
- [ ] Authentication successes and failures are logged.
- [ ] Authorization failures are logged.
- [ ] Logs do not contain sensitive data (passwords, tokens, PII).
- [ ] Alerting is configured for anomalous patterns.

### A10: Server-Side Request Forgery (SSRF)
- [ ] User-supplied URLs are validated against an allowlist of domains.
- [ ] Internal network ranges (10.x, 172.16.x, 192.168.x) are blocked for outbound requests.
- [ ] URL redirects do not follow arbitrary destinations.

## Dependency Audit

Run these checks regularly and on every PR that modifies dependencies:

```bash
# Node.js / npm
npm audit --production
npm audit fix

# Check for known vulnerabilities in detail
npx audit-ci --critical

# Check for outdated packages
npm outdated

# Python
pip-audit
safety check

# General (multi-language)
snyk test
```

Severity response times:
- **Critical**: Fix within 24 hours or remove the dependency.
- **High**: Fix within 1 week.
- **Medium**: Fix within 1 month.
- **Low**: Fix in the next scheduled maintenance window.

## Secrets Detection

Prevent secrets from entering the codebase:

```bash
# Pre-commit hook with gitleaks
gitleaks detect --source . --verbose

# Scan git history for leaked secrets
gitleaks detect --source . --log-opts="--all"

# Alternative: truffleHog
trufflehog filesystem --directory . --only-verified
```

Patterns to detect:
- AWS access keys: `AKIA[0-9A-Z]{16}`
- Generic API keys: `(api[_-]?key|apikey)\s*[:=]\s*['"][a-zA-Z0-9]{16,}`
- Private keys: `-----BEGIN (RSA |EC )?PRIVATE KEY-----`
- Database connection strings: `(postgres|mysql|mongodb)://[^\s]+`
- JWT tokens: `eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+`

## XSS Prevention

- Use framework-provided auto-escaping for all rendered output (React JSX, Vue templates).
- Never use `dangerouslySetInnerHTML`, `v-html`, or `innerHTML` with user-supplied data.
- Sanitize rich text input with a library like DOMPurify before rendering.
- Set `Content-Security-Policy` headers to restrict inline scripts and styles.
- Encode output contextually: HTML entities for HTML, JS encoding for JavaScript, URL encoding for URLs.

## CSRF Protection

- Use anti-CSRF tokens for all state-changing operations (POST, PUT, DELETE).
- Set `SameSite=Strict` or `SameSite=Lax` on session cookies.
- Verify the `Origin` or `Referer` header on sensitive endpoints.
- For API-only backends with token authentication (Bearer tokens), CSRF tokens are generally not needed since cookies are not used.

## SQL Injection Prevention

- Always use parameterized queries or prepared statements.
- Never concatenate user input into SQL strings.
- Use an ORM with parameterized query support.
- Apply the principle of least privilege to database accounts.
- Validate and type-check all query parameters before they reach the database layer.

## Authentication Review

Verify these controls:
- Passwords are hashed with a strong, salted algorithm (Argon2id preferred).
- Login endpoints are rate-limited (e.g., 5 attempts per minute per IP).
- Session tokens have a defined expiration and are rotated on privilege changes.
- "Remember me" tokens are stored hashed in the database.
- Password reset tokens are single-use, time-limited (max 1 hour), and invalidated after use.
- OAuth flows validate the `state` parameter to prevent CSRF.

## Authorization Review

Verify these controls:
- Every API endpoint has explicit authorization checks.
- Authorization is enforced server-side, never relying on client-side checks alone.
- Role-based or attribute-based access control is consistently applied.
- Users cannot access resources belonging to other users by manipulating IDs.
- Admin endpoints are separated and protected with additional verification.
- API responses exclude data the requesting user is not authorized to see.

## Security Headers Check

Verify these HTTP response headers are set:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
X-XSS-Protection: 0  (disabled in favor of CSP)
```

Use https://securityheaders.com to verify your production headers.

## Security Audit Report Template

```markdown
# Security Audit Report
**Project**: [Name]
**Date**: [YYYY-MM-DD]
**Auditor**: [Name]
**Scope**: [Description of what was audited]

## Executive Summary
[Brief overview of findings: X critical, Y high, Z medium, W low]

## Findings

### [FINDING-001] [Title]
- **Severity**: Critical / High / Medium / Low
- **Category**: OWASP A01-A10
- **Location**: [File path and line number]
- **Description**: [What the vulnerability is]
- **Impact**: [What could happen if exploited]
- **Reproduction**: [Steps to reproduce]
- **Recommendation**: [How to fix it]
- **Status**: Open / In Progress / Resolved

## Summary Table
| ID         | Title              | Severity | Status   |
|------------|--------------------|----------|----------|
| FINDING-001| [Title]            | Critical | Open     |

## Recommendations
[Prioritized list of actions]
```
