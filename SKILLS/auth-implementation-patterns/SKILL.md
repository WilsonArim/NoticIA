---
name: Auth Implementation Patterns
description: JWT, OAuth2, session management, password hashing, and MFA implementation patterns
phase: 3
---

# Auth Implementation Patterns

## JWT Structure and Best Practices

A JWT consists of three parts: header (algorithm, type), payload (claims), and signature. Only the signature provides integrity; the payload is base64-encoded, not encrypted.

```typescript
// Token generation
import jwt from "jsonwebtoken";

const generateTokens = (userId: string, role: string) => {
  const accessToken = jwt.sign(
    { sub: userId, role, type: "access" },
    env.JWT_SECRET,
    { expiresIn: "15m", issuer: "myapp", audience: "myapp-api" }
  );

  const refreshToken = jwt.sign(
    { sub: userId, type: "refresh" },
    env.JWT_REFRESH_SECRET,
    { expiresIn: "7d", issuer: "myapp" }
  );

  return { accessToken, refreshToken };
};
```

**Critical rules for JWTs:**
- Set short expiry for access tokens (15 minutes or less). Use refresh tokens for long-lived sessions.
- Use separate secrets for access and refresh tokens.
- Always validate `iss`, `aud`, and `exp` claims on verification.
- Store refresh tokens in the database so they can be revoked. Access tokens are stateless and cannot be revoked individually.
- Never store sensitive data in the payload. It is readable by anyone who intercepts the token.
- Use RS256 (asymmetric) for distributed systems where multiple services need to verify tokens. Use HS256 (symmetric) for single-service setups.

## Refresh Token Rotation

Implement refresh token rotation to limit the window of a compromised token.

```typescript
const refreshAccessToken = async (oldRefreshToken: string) => {
  const payload = jwt.verify(oldRefreshToken, env.JWT_REFRESH_SECRET) as JwtPayload;
  if (payload.type !== "refresh") throw new AppError(401, "Invalid token type");

  const stored = await db.refreshToken.findUnique({ where: { token: hashToken(oldRefreshToken) } });
  if (!stored || stored.revoked) {
    // Potential token theft: revoke all tokens for this user
    await db.refreshToken.updateMany({
      where: { userId: payload.sub },
      data: { revoked: true },
    });
    throw new AppError(401, "Token reuse detected");
  }

  // Revoke old token and issue new pair
  await db.refreshToken.update({ where: { id: stored.id }, data: { revoked: true } });

  const tokens = generateTokens(payload.sub, stored.userRole);
  await db.refreshToken.create({
    data: { token: hashToken(tokens.refreshToken), userId: payload.sub, userRole: stored.userRole },
  });

  return tokens;
};
```

If a revoked refresh token is ever reused, assume theft and invalidate all tokens for that user immediately.

## OAuth2 Flows

### Authorization Code Flow (Server-Side Apps)

This is the standard flow for web applications with a backend.

1. Redirect user to the provider's authorization URL with `response_type=code`, `client_id`, `redirect_uri`, `scope`, and `state` (CSRF protection).
2. Provider redirects back to your `redirect_uri` with a `code` and your `state`.
3. Your server exchanges the `code` for tokens by calling the provider's token endpoint with `client_id`, `client_secret`, and the `code`.
4. Use the access token to fetch user profile from the provider.
5. Create or update the user in your database and issue your own session/JWT.

Always validate the `state` parameter matches what you generated. Store it in the session before redirecting.

### Authorization Code Flow with PKCE (SPAs and Mobile)

PKCE (Proof Key for Code Exchange) eliminates the need for a client secret, making it safe for public clients.

```typescript
import crypto from "crypto";

// Step 1: Generate code verifier and challenge
const codeVerifier = crypto.randomBytes(32).toString("base64url");
const codeChallenge = crypto.createHash("sha256").update(codeVerifier).digest("base64url");

// Step 2: Include in authorization URL
const authUrl = new URL("https://provider.com/authorize");
authUrl.searchParams.set("response_type", "code");
authUrl.searchParams.set("client_id", env.OAUTH_CLIENT_ID);
authUrl.searchParams.set("redirect_uri", env.OAUTH_REDIRECT_URI);
authUrl.searchParams.set("code_challenge", codeChallenge);
authUrl.searchParams.set("code_challenge_method", "S256");
authUrl.searchParams.set("state", generateState());

// Step 3: Exchange code with verifier
const tokenResponse = await fetch("https://provider.com/token", {
  method: "POST",
  body: new URLSearchParams({
    grant_type: "authorization_code",
    code: authorizationCode,
    redirect_uri: env.OAUTH_REDIRECT_URI,
    client_id: env.OAUTH_CLIENT_ID,
    code_verifier: codeVerifier,   // Proves you initiated the request
  }),
});
```

PKCE should be used even for server-side apps as an additional security layer.

## Session Management: Cookie vs Token

**HttpOnly Cookie Sessions (Recommended for web apps):**
- The server sets a session cookie with `HttpOnly`, `Secure`, `SameSite=Lax`, and a reasonable `Max-Age`.
- The browser automatically sends the cookie on every request. No JavaScript can access it, preventing XSS-based token theft.
- The server looks up session data in a store (Redis, database).

```typescript
import session from "express-session";
import RedisStore from "connect-redis";

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 24 * 60 * 60 * 1000, // 24 hours
  },
}));
```

**Bearer Token (Required for mobile apps and third-party API consumers):**
- The client stores the token (securely in keychain/keystore, never in localStorage).
- The client sends the token in the `Authorization` header.
- Stateless verification on the server, but no built-in revocation without a blocklist.

**Decision:** Use cookies for first-party web apps. Use bearer tokens for mobile apps and external API clients.

## Password Hashing

Never store passwords in plain text. Never use MD5, SHA-1, or SHA-256 for password hashing. These are fast hash functions not designed for passwords.

**Argon2id** is the recommended algorithm. Bcrypt is acceptable if Argon2 is not available.

```typescript
import argon2 from "argon2";

// Hashing
const hash = await argon2.hash(password, {
  type: argon2.argon2id,
  memoryCost: 65536,    // 64 MB
  timeCost: 3,
  parallelism: 4,
});

// Verification
const isValid = await argon2.verify(storedHash, candidatePassword);
```

If using bcrypt, use a cost factor of at least 12. Re-hash passwords when the user logs in if the cost factor has been increased since the hash was created.

## MFA Implementation

Implement Time-based One-Time Password (TOTP) as the standard second factor.

```typescript
import { authenticator } from "otplib";
import qrcode from "qrcode";

// Setup: generate secret and QR code
const setupMFA = async (userId: string) => {
  const secret = authenticator.generateSecret();
  await db.user.update({ where: { id: userId }, data: { mfaSecret: encrypt(secret), mfaEnabled: false } });

  const otpauth = authenticator.keyuri(user.email, "MyApp", secret);
  const qrCodeUrl = await qrcode.toDataURL(otpauth);
  return { qrCodeUrl, secret };  // Show secret as fallback for manual entry
};

// Verification: validate code and enable MFA
const verifyAndEnableMFA = async (userId: string, token: string) => {
  const user = await db.user.findUniqueOrThrow({ where: { id: userId } });
  const secret = decrypt(user.mfaSecret);
  const isValid = authenticator.verify({ token, secret });

  if (!isValid) throw new AppError(400, "Invalid verification code");

  // Generate recovery codes
  const recoveryCodes = Array.from({ length: 10 }, () => crypto.randomBytes(4).toString("hex"));
  await db.user.update({
    where: { id: userId },
    data: { mfaEnabled: true, recoveryCodes: recoveryCodes.map(hashCode) },
  });

  return { recoveryCodes };  // Show once, user must save them
};
```

Always provide recovery codes (one-time use, 8-10 codes). Store them hashed. Encrypt the TOTP secret at rest. Rate-limit MFA verification attempts to prevent brute-force (6-digit codes have only 1 million combinations).

## Auth Middleware Pattern

Compose authentication and authorization as layered middleware.

```typescript
// Authenticate: verify identity
export const authenticate = asyncHandler(async (req, _res, next) => {
  const token = extractToken(req);
  if (!token) throw new AppError(401, "Authentication required");

  const payload = jwt.verify(token, env.JWT_SECRET, { issuer: "myapp", audience: "myapp-api" });
  const user = await db.user.findUnique({ where: { id: payload.sub } });
  if (!user || user.disabled) throw new AppError(401, "User not found or disabled");

  req.user = user;
  next();
});

// Require MFA: check second factor was verified in this session
export const requireMFA = asyncHandler(async (req, _res, next) => {
  if (req.user.mfaEnabled && !req.session?.mfaVerified) {
    throw new AppError(403, "MFA verification required");
  }
  next();
});

// Authorize: check permissions
export const authorize = (...allowedRoles: string[]) =>
  asyncHandler(async (req, _res, next) => {
    if (!allowedRoles.includes(req.user.role)) {
      throw new AppError(403, "Insufficient permissions");
    }
    next();
  });

// Usage: stack middleware in order
router.post("/admin/users",
  authenticate,
  requireMFA,
  authorize("admin"),
  createUserHandler
);
```

## Key Principles

- Never roll your own cryptography. Use established libraries for JWT, hashing, and encryption.
- Store secrets (JWT secret, OAuth client secret, encryption keys) in a secrets manager, not in environment files.
- Implement account lockout after repeated failed login attempts (e.g., 5 failures in 15 minutes triggers a 30-minute lockout).
- Log all authentication events (login, logout, failed attempts, password changes, MFA changes) for audit trails.
- Use constant-time comparison for token and code verification to prevent timing attacks.
- Always hash tokens and codes before storing them. A database breach should not expose usable credentials.
- Set token expiry as short as the UX allows. Shorter windows reduce the impact of token theft.
